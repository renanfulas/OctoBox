from datetime import datetime, timedelta, timezone as dt_timezone
from io import StringIO
import json

import pytest
from django.core.management import call_command
from django.utils import timezone
from django_tenants.utils import schema_context

from integrations.whatsapp.models import WebhookDeliveryStatus, WebhookEvent

from integrations.management.commands.report_legacy_whatsapp_queue import (
    _safe_attempt_counts,
    _safe_group_counts,
    summarize_legacy_queue,
)


def test_queue_census_collapses_unrecognized_dimensions_without_echoing_them():
    provider_secret = "tenant-phone-5511999999999"
    status_secret = "raw-error-private-value"
    provider_counts = _safe_group_counts(
        [("evolution", 2), (provider_secret, 1)],
        allowed_labels={"evolution"},
    )
    status_counts = _safe_group_counts(
        [("pending", 3), (status_secret, 1)],
        allowed_labels={"pending", "processed", "failed"},
    )

    assert provider_counts == {"evolution": 2, "other": 1}
    assert status_counts == {"pending": 3, "other": 1}
    assert provider_secret not in repr(provider_counts)
    assert status_secret not in repr(status_counts)


def test_queue_census_report_contains_only_aggregates_and_safe_attempt_buckets():
    payload_marker = "sensitive-payload-5511999999999"
    now = datetime(2026, 10, 23, tzinfo=dt_timezone.utc)
    report = summarize_legacy_queue(
        now=now,
        aggregate={
            "rows": 4,
            "first_created_at": now,
            "last_created_at": now,
            "missing_event_id": 1,
            "missing_fingerprint": 2,
            "pending_due": 1,
            "pending_future": 1,
            "pending_unscheduled": 1,
            "future_created_at": 0,
            "under_7_days": 4,
            "7_to_30_days": 0,
            "30_to_90_days": 0,
            "over_90_days": 0,
        },
        status_rows=[("pending", 3), (payload_marker, 1)],
        provider_rows=[("evolution", 4)],
        attempt_rows=[(0, 1), (3, 1), (5, 1), (100, 1)],
    )

    assert report["rows"] == 4
    assert report["status_counts"] == {"pending": 3, "other": 1}
    assert report["attempt_buckets"] == {"0": 1, "3": 1, "5_plus": 2}
    assert payload_marker not in repr(report)


def test_queue_census_attempt_counts_flag_invalid_negative_values():
    assert _safe_attempt_counts([(-1, 2), ("bad", 1), (4, 1)]) == {
        "4": 1,
        "invalid": 3,
    }


@pytest.mark.django_db(transaction=True)
def test_queue_census_reads_only_aggregates_from_public_without_leaking_payload():
    secret_marker = "private-phone-5511999999999"
    with schema_context("public"):
        event = WebhookEvent.objects.create(
            provider=secret_marker,
            payload={"phone": secret_marker},
            status=WebhookDeliveryStatus.PENDING,
            attempts=7,
            next_retry_at=timezone.now() - timedelta(minutes=1),
            last_error_message=secret_marker,
        )

    output = StringIO()
    call_command(
        "report_legacy_whatsapp_queue",
        schema="public",
        stdout=output,
        no_color=True,
    )
    report = json.loads(output.getvalue())

    assert report["schema"] == "public"
    # The shared public schema can contain legacy rows from other tests. This
    # command is a census, so assert the canary contributes to its aggregates
    # without assuming the rest of the public inbox is empty.
    assert report["rows"] >= 1
    assert report["provider_counts"]["other"] >= 1
    assert report["pending_retry_counts"]["due"] >= 1
    assert report["attempt_buckets"]["5_plus"] >= 1
    assert secret_marker not in output.getvalue()
    with schema_context("public"):
        event.refresh_from_db()
        assert event.payload == {"phone": secret_marker}
        assert event.last_error_message == secret_marker
