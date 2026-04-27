"""
Testes da camada de dominio puro de cancelamento de sessao.
Sem Django, sem ORM, sem pywebpush — executa em ms.
"""

import pytest

from operations.domain.session_cancellation_rules import (
    LAST_MINUTE_THRESHOLD_MINUTES,
    CancellationDecision,
    build_cancellation_decision,
    resolve_copy_variant,
    should_notify_cancellation,
)


# ---------------------------------------------------------------------------
# should_notify_cancellation — 6 casos de tabela
# ---------------------------------------------------------------------------

class TestShouldNotifyCancellation:
    def test_scheduled_to_canceled_with_active_atts_notifies(self):
        assert should_notify_cancellation(
            prev_status='scheduled',
            new_status='canceled',
            attendance_count_active=3,
        ) is True

    def test_open_to_canceled_with_active_atts_notifies(self):
        assert should_notify_cancellation(
            prev_status='open',
            new_status='canceled',
            attendance_count_active=1,
        ) is True

    def test_scheduled_to_canceled_no_atts_does_not_notify(self):
        assert should_notify_cancellation(
            prev_status='scheduled',
            new_status='canceled',
            attendance_count_active=0,
        ) is False

    def test_already_canceled_to_canceled_is_idempotent(self):
        assert should_notify_cancellation(
            prev_status='canceled',
            new_status='canceled',
            attendance_count_active=10,
        ) is False

    def test_canceled_to_scheduled_does_not_notify(self):
        assert should_notify_cancellation(
            prev_status='canceled',
            new_status='scheduled',
            attendance_count_active=5,
        ) is False

    def test_completed_to_canceled_with_atts_notifies(self):
        assert should_notify_cancellation(
            prev_status='completed',
            new_status='canceled',
            attendance_count_active=2,
        ) is True


# ---------------------------------------------------------------------------
# resolve_copy_variant — 5 casos
# ---------------------------------------------------------------------------

class TestResolveCopyVariant:
    def test_checked_in_wins_over_last_minute(self):
        variant = resolve_copy_variant(
            cancel_lead_minutes=30,
            had_checked_in_attendance=True,
        )
        assert variant == 'already_checked_in'

    def test_checked_in_wins_even_with_ahead_lead(self):
        variant = resolve_copy_variant(
            cancel_lead_minutes=300,
            had_checked_in_attendance=True,
        )
        assert variant == 'already_checked_in'

    def test_last_minute_below_threshold(self):
        variant = resolve_copy_variant(
            cancel_lead_minutes=LAST_MINUTE_THRESHOLD_MINUTES - 1,
            had_checked_in_attendance=False,
        )
        assert variant == 'last_minute'

    def test_last_minute_at_zero(self):
        variant = resolve_copy_variant(
            cancel_lead_minutes=0,
            had_checked_in_attendance=False,
        )
        assert variant == 'last_minute'

    def test_ahead_at_threshold_or_above(self):
        variant = resolve_copy_variant(
            cancel_lead_minutes=LAST_MINUTE_THRESHOLD_MINUTES,
            had_checked_in_attendance=False,
        )
        assert variant == 'ahead'

    def test_ahead_well_in_advance(self):
        variant = resolve_copy_variant(
            cancel_lead_minutes=1440,
            had_checked_in_attendance=False,
        )
        assert variant == 'ahead'


# ---------------------------------------------------------------------------
# build_cancellation_decision — integra as duas funcoes
# ---------------------------------------------------------------------------

class TestBuildCancellationDecision:
    def test_no_notification_when_no_atts(self):
        decision = build_cancellation_decision(
            prev_status='scheduled',
            new_status='canceled',
            attendance_count_active=0,
            cancel_lead_minutes=60,
            had_checked_in_attendance=False,
        )
        assert decision == CancellationDecision(should_notify=False, copy_variant=None)

    def test_ahead_variant_populated(self):
        decision = build_cancellation_decision(
            prev_status='scheduled',
            new_status='canceled',
            attendance_count_active=5,
            cancel_lead_minutes=360,
            had_checked_in_attendance=False,
        )
        assert decision.should_notify is True
        assert decision.copy_variant == 'ahead'

    def test_last_minute_variant_populated(self):
        decision = build_cancellation_decision(
            prev_status='scheduled',
            new_status='canceled',
            attendance_count_active=2,
            cancel_lead_minutes=45,
            had_checked_in_attendance=False,
        )
        assert decision.should_notify is True
        assert decision.copy_variant == 'last_minute'

    def test_already_checked_in_variant_populated(self):
        decision = build_cancellation_decision(
            prev_status='open',
            new_status='canceled',
            attendance_count_active=8,
            cancel_lead_minutes=10,
            had_checked_in_attendance=True,
        )
        assert decision.should_notify is True
        assert decision.copy_variant == 'already_checked_in'

    def test_idempotent_canceled_to_canceled(self):
        decision = build_cancellation_decision(
            prev_status='canceled',
            new_status='canceled',
            attendance_count_active=12,
            cancel_lead_minutes=0,
            had_checked_in_attendance=True,
        )
        assert decision.should_notify is False
        assert decision.copy_variant is None
