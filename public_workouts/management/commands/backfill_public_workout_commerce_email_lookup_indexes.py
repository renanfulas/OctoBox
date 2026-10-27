"""Dry-run, backfill, or verify checkout-lead and waitlist email HMACs."""

from __future__ import annotations

import json

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.db.models import Count
from django_tenants.utils import get_public_schema_name, schema_context

from public_workouts.models import PublicWorkoutCheckoutLead, PublicWorkoutWaitlistEntry
from shared_support.crypto_fields import (
    generate_public_workout_checkout_lead_email_blind_index,
    generate_public_workout_waitlist_email_blind_index,
)


TARGETS = (
    ("checkout_leads", PublicWorkoutCheckoutLead, generate_public_workout_checkout_lead_email_blind_index),
    ("waitlist_entries", PublicWorkoutWaitlistEntry, generate_public_workout_waitlist_email_blind_index),
)


class Command(BaseCommand):
    help = "Faz dry-run, backfill ou verificação agregada dos índices HMAC comerciais de email."

    def add_arguments(self, parser):
        action = parser.add_mutually_exclusive_group()
        action.add_argument("--apply", action="store_true", help="Grava índices ausentes usando compare-and-swap.")
        action.add_argument("--verify", action="store_true", help="Recalcula e compara sem gravar.")
        parser.add_argument("--batch-size", type=int, default=250)
        parser.add_argument("--limit", type=int, default=0, help="Limita a leitura; 0 percorre os dois conjuntos completos.")

    def handle(self, *args, **options):
        if connection.vendor != "postgresql":
            raise CommandError("O backfill shared exige PostgreSQL.")
        batch_size, limit = options["batch_size"], options["limit"]
        if not 1 <= batch_size <= 5000:
            raise CommandError("batch-size deve estar entre 1 e 5000.")
        if limit < 0:
            raise CommandError("limit não pode ser negativo.")
        if not getattr(settings, "EMAIL_BLIND_INDEX_KEY", ""):
            raise CommandError("EMAIL_BLIND_INDEX_KEY ausente; nenhum dado foi alterado.")

        totals = {
            name: {
                "rows_scanned": 0, "nonempty_email": 0, "missing_index": 0,
                "written": 0, "drift": 0, "write_conflicts": 0,
            }
            for name, _model, _generator in TARGETS
        }
        try:
            with schema_context(get_public_schema_name()):
                for name, model, generator in TARGETS:
                    self._process_target(
                        model, generator, totals[name], batch_size=batch_size,
                        limit=limit, apply=options["apply"], verify=options["verify"],
                    )
                duplicates = self._duplicate_groups()
        except CommandError:
            raise
        except Exception as exc:
            raise CommandError("Operação interrompida; nenhum email ou digest foi exibido.") from exc

        complete_scan = not bool(limit)
        verification_clean = all(
            not counts["missing_index"] and not counts["drift"] for counts in totals.values()
        )
        report = {
            "scope": "shared",
            "schema": get_public_schema_name(),
            "mode": "apply" if options["apply"] else "verify" if options["verify"] else "dry-run",
            "complete_target_scan": complete_scan,
            "checkout_leads": totals["checkout_leads"],
            "waitlist_entries": totals["waitlist_entries"],
            "active_uniqueness_duplicate_groups": duplicates,
            "duplicate_scan_complete": bool(options["verify"] and complete_scan),
            "verification_clean": bool(options["verify"] and complete_scan and verification_clean),
        }
        self.stdout.write(json.dumps(report, ensure_ascii=False, sort_keys=True))
        if options["verify"] and not verification_clean:
            raise CommandError("Verificação encontrou índice ausente ou divergente.")

    @staticmethod
    def _process_target(model, generator, counts, *, batch_size, limit, apply, verify):
        cursor_id = 0
        while True:
            remaining = limit - counts["rows_scanned"] if limit else batch_size
            if limit and remaining <= 0:
                break
            size = min(batch_size, remaining) if limit else batch_size
            queryset = model.objects.filter(pk__gt=cursor_id).order_by("pk")
            if not verify:
                queryset = queryset.filter(email_lookup_index="")
            queryset = queryset.only("pk", "email", "email_lookup_index")
            if apply:
                with transaction.atomic():
                    rows = list(queryset.select_for_update()[:size])
                    PublicWorkoutCommerceEmailLookupCommandProcessor.process(
                        model, rows, counts, generator, apply=True, verify=False,
                    )
            else:
                rows = list(queryset[:size])
                PublicWorkoutCommerceEmailLookupCommandProcessor.process(
                    model, rows, counts, generator, apply=False, verify=verify,
                )
            if not rows:
                break
            cursor_id = rows[-1].pk

    @staticmethod
    def _duplicate_groups():
        lead_groups = (
            PublicWorkoutCheckoutLead.objects.filter(paid_at__isnull=True)
            .exclude(email_lookup_index="").values("email_lookup_index")
            .annotate(row_count=Count("pk")).filter(row_count__gt=1).count()
        )
        waitlist_groups = (
            PublicWorkoutWaitlistEntry.objects.filter(status="waiting")
            .exclude(email_lookup_index="").values("email_lookup_index", "tier")
            .annotate(row_count=Count("pk")).filter(row_count__gt=1).count()
        )
        return {"unpaid_checkout_lead_email": lead_groups, "waiting_waitlist_email_tier": waitlist_groups}


class PublicWorkoutCommerceEmailLookupCommandProcessor:
    @staticmethod
    def process(model, rows, counts, generator, *, apply, verify):
        for row in rows:
            counts["rows_scanned"] += 1
            expected = generator(row.email)
            if expected:
                counts["nonempty_email"] += 1
            if not row.email_lookup_index and expected:
                counts["missing_index"] += 1
                if apply:
                    updated = model.objects.filter(
                        pk=row.pk, email=row.email, email_lookup_index="",
                    ).update(email_lookup_index=expected)
                    if updated:
                        counts["written"] += 1
                    else:
                        counts["write_conflicts"] += 1
            elif verify and row.email_lookup_index != expected:
                counts["drift"] += 1


__all__ = ["Command"]
