"""Read-only, aggregate-only inventory of the legacy public WhatsApp inbox."""

from __future__ import annotations

import json
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.db.models import Count, Max, Min, Q
from django.utils import timezone
from django_tenants.utils import schema_context

from integrations.whatsapp.models import WebhookDeliveryStatus, WebhookEvent


KNOWN_PROVIDERS = {"evolution"}
KNOWN_STATUSES = {choice for choice, _label in WebhookDeliveryStatus.choices}


def _safe_group_counts(rows, *, allowed_labels):
    """Collapse unexpected stored labels without echoing arbitrary DB content."""

    counts = {label: 0 for label in sorted(allowed_labels)}
    counts["other"] = 0
    for label, count in rows:
        safe_label = label if label in allowed_labels else "other"
        counts[safe_label] += int(count)
    return {label: count for label, count in counts.items() if count}


def _attempt_bucket(value):
    try:
        attempts = int(value)
    except (TypeError, ValueError):
        return "invalid"
    if attempts < 0:
        return "invalid"
    return "5_plus" if attempts >= 5 else str(attempts)


def _safe_attempt_counts(rows):
    counts = {str(value): 0 for value in range(5)}
    counts.update({"5_plus": 0, "invalid": 0})
    for attempts, count in rows:
        counts[_attempt_bucket(attempts)] += int(count)
    return {label: count for label, count in counts.items() if count}


def summarize_legacy_queue(*, now, aggregate, status_rows, provider_rows, attempt_rows):
    """Build a payload-free report from aggregate values only."""

    return {
        "schema": "public",
        "snapshot_at": now.isoformat(),
        "rows": int(aggregate["rows"] or 0),
        "created_at_range": {
            "first": aggregate["first_created_at"].isoformat()
            if aggregate["first_created_at"]
            else None,
            "last": aggregate["last_created_at"].isoformat()
            if aggregate["last_created_at"]
            else None,
        },
        "missing_event_id": int(aggregate["missing_event_id"] or 0),
        "missing_fingerprint": int(aggregate["missing_fingerprint"] or 0),
        "status_counts": _safe_group_counts(status_rows, allowed_labels=KNOWN_STATUSES),
        "provider_counts": _safe_group_counts(provider_rows, allowed_labels=KNOWN_PROVIDERS),
        "pending_retry_counts": {
            "due": int(aggregate["pending_due"] or 0),
            "future": int(aggregate["pending_future"] or 0),
            "unscheduled": int(aggregate["pending_unscheduled"] or 0),
        },
        "age_buckets": {
            "future_created_at": int(aggregate["future_created_at"] or 0),
            "under_7_days": int(aggregate["under_7_days"] or 0),
            "7_to_30_days": int(aggregate["7_to_30_days"] or 0),
            "30_to_90_days": int(aggregate["30_to_90_days"] or 0),
            "over_90_days": int(aggregate["over_90_days"] or 0),
        },
        "attempt_buckets": _safe_attempt_counts(attempt_rows),
    }


class Command(BaseCommand):
    help = "Gera censo read-only agregado da fila antiga de WhatsApp no schema public."

    def add_arguments(self, parser):
        parser.add_argument(
            "--schema",
            required=True,
            choices=("public",),
            help="Schema compartilhado da fila antiga; somente public é aceito.",
        )

    def handle(self, *args, **options):
        if options["schema"] != "public":
            raise CommandError("O censo legado aceita somente --schema public.")
        if connection.vendor != "postgresql":
            raise CommandError("O censo da fila legada exige PostgreSQL.")

        now = timezone.now()
        try:
            with schema_context("public"):
                with transaction.atomic():
                    with connection.cursor() as cursor:
                        cursor.execute("SET TRANSACTION READ ONLY")

                    events = WebhookEvent.objects
                    aggregate = events.aggregate(
                        rows=Count("pk"),
                        first_created_at=Min("created_at"),
                        last_created_at=Max("created_at"),
                        missing_event_id=Count("pk", filter=Q(event_id__isnull=True) | Q(event_id="")),
                        missing_fingerprint=Count(
                            "pk", filter=Q(webhook_fingerprint__isnull=True) | Q(webhook_fingerprint="")
                        ),
                        pending_due=Count(
                            "pk",
                            filter=Q(
                                status=WebhookDeliveryStatus.PENDING,
                                next_retry_at__isnull=False,
                                next_retry_at__lte=now,
                            ),
                        ),
                        pending_future=Count(
                            "pk",
                            filter=Q(
                                status=WebhookDeliveryStatus.PENDING,
                                next_retry_at__gt=now,
                            ),
                        ),
                        pending_unscheduled=Count(
                            "pk",
                            filter=Q(
                                status=WebhookDeliveryStatus.PENDING,
                                next_retry_at__isnull=True,
                            ),
                        ),
                        future_created_at=Count("pk", filter=Q(created_at__gt=now)),
                        under_7_days=Count(
                            "pk",
                            filter=Q(
                                created_at__gte=now - timedelta(days=7),
                                created_at__lte=now,
                            ),
                        ),
                        **{
                            "7_to_30_days": Count(
                                "pk",
                                filter=Q(
                                    created_at__lt=now - timedelta(days=7),
                                    created_at__gte=now - timedelta(days=30),
                                ),
                            ),
                            "30_to_90_days": Count(
                                "pk",
                                filter=Q(
                                    created_at__lt=now - timedelta(days=30),
                                    created_at__gte=now - timedelta(days=90),
                                ),
                            ),
                            "over_90_days": Count(
                                "pk", filter=Q(created_at__lt=now - timedelta(days=90))
                            ),
                        },
                    )
                    status_rows = list(
                        events.values_list("status").annotate(row_count=Count("pk"))
                    )
                    provider_rows = list(
                        events.values_list("provider").annotate(row_count=Count("pk"))
                    )
                    attempt_rows = list(
                        events.values_list("attempts").annotate(row_count=Count("pk"))
                    )

            report = summarize_legacy_queue(
                now=now,
                aggregate=aggregate,
                status_rows=status_rows,
                provider_rows=provider_rows,
                attempt_rows=attempt_rows,
            )
        except CommandError:
            raise
        except Exception as exc:
            raise CommandError("Censo interrompido; nenhuma linha da fila foi alterada.") from exc

        self.stdout.write(json.dumps(report, ensure_ascii=False, sort_keys=True))
