from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from student_identity.domain.cohort_contracts import (
    COHORT_DEFINITIONS,
    calculate_student_cohort_report,
)


def _start(*, key='11', day=1, tz='America/Sao_Paulo'):
    return SimpleNamespace(
        occurred_at=datetime(2026, 1, day, 15, tzinfo=timezone.utc),
        timezone_name=tz,
        contract_version=1,
        cohort_kind='invitation',
        cohort_key=key,
    )


def _milestone(*, journey, event, key='11', identity=501, day=1, hour=15):
    return SimpleNamespace(
        journey=journey,
        milestone=event,
        cohort_kind='invitation',
        cohort_key=key,
        identity_id=identity,
        occurred_at=datetime(2026, 1, day, hour, tzinfo=timezone.utc),
        contract_version=1,
    )


def test_cohort_uses_local_calendar_boundaries_for_activation_and_retention():
    definition = COHORT_DEFINITIONS[1]
    journey = definition.journey
    report = calculate_student_cohort_report(
        definition=definition,
        starts=[_start()],
        activations=[_milestone(journey=journey, event='app_entry_completed', day=7, hour=2)],
        returns=[(501, datetime(2026, 1, 9, 3, tzinfo=timezone.utc))],
        now=datetime(2026, 1, 20, tzinfo=timezone.utc),
        coverage_start=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    assert report['eligible_count'] == 1
    assert report['activated_count'] == 1
    assert report['retained_count'] == 1
    assert report['activation_rate'] == 100.0
    assert report['retention_rate'] == 100.0
    assert report['maturity'] == 'ready'


def test_retention_excludes_d6_and_d14_and_ignores_delayed_events_after_cutoff():
    definition = COHORT_DEFINITIONS[1]
    journey = definition.journey
    report = calculate_student_cohort_report(
        definition=definition,
        starts=[_start()],
        activations=[_milestone(journey=journey, event='app_entry_completed', day=2)],
        returns=[
            (501, datetime(2026, 1, 7, 15, tzinfo=timezone.utc)),  # D6
            (501, datetime(2026, 1, 15, 15, tzinfo=timezone.utc)),  # D14
        ],
        now=datetime(2026, 1, 20, tzinfo=timezone.utc),
        coverage_start=None,
    )

    assert report['eligible_count'] == 1
    assert report['activated_count'] == 1
    assert report['retained_count'] == 0
    assert report['retention_rate'] == 0.0


def test_activation_window_excludes_events_before_start_and_at_local_d7_boundary():
    definition = COHORT_DEFINITIONS[1]
    journey = definition.journey
    report = calculate_student_cohort_report(
        definition=definition,
        starts=[_start()],
        activations=[
            _milestone(
                journey=journey,
                event='app_entry_completed',
                day=1,
                hour=14,
            ),  # antes do início às 15:00 UTC, ainda que no mesmo dia local
            _milestone(
                journey=journey,
                event='app_entry_completed',
                day=8,
                hour=3,
            ),  # início de D7 em America/Sao_Paulo
        ],
        returns=[],
        now=datetime(2026, 1, 20, tzinfo=timezone.utc),
        coverage_start=None,
    )

    assert report['eligible_count'] == 1
    assert report['activated_count'] == 0
    assert report['activation_rate'] == 0.0


def test_activation_window_includes_start_and_the_last_instant_of_local_d6():
    definition = COHORT_DEFINITIONS[1]
    journey = definition.journey
    report = calculate_student_cohort_report(
        definition=definition,
        starts=[_start()],
        activations=[
            _milestone(journey=journey, event='app_entry_completed', day=1, hour=15),
            _milestone(journey=journey, event='app_entry_completed', day=8, hour=2),
        ],
        returns=[],
        now=datetime(2026, 1, 20, tzinfo=timezone.utc),
        coverage_start=None,
    )

    assert report['eligible_count'] == 1
    assert report['activated_count'] == 1
    assert report['activation_rate'] == 100.0


def test_maturity_keeps_denominator_absent_until_cutoff_reaches_d14():
    definition = COHORT_DEFINITIONS[1]
    report = calculate_student_cohort_report(
        definition=definition,
        starts=[_start(day=10)],
        activations=[],
        returns=[],
        now=datetime(2026, 1, 20, tzinfo=timezone.utc),
        coverage_start=None,
    )

    assert report['eligible_count'] == 0
    assert report['immature_count'] == 1
    assert report['activation_rate'] is None
    assert report['retention_rate'] is None
    assert report['maturity'] == 'warming_up'


def test_cohorts_do_not_share_identity_or_activation_between_invites():
    definition = COHORT_DEFINITIONS[1]
    report = calculate_student_cohort_report(
        definition=definition,
        starts=[_start(key='11'), _start(key='12', day=1)],
        activations=[_milestone(journey=definition.journey, event='app_entry_completed', key='11', identity=501)],
        returns=[(502, datetime(2026, 1, 9, 15, tzinfo=timezone.utc))],
        now=datetime(2026, 1, 20, tzinfo=timezone.utc),
        coverage_start=None,
    )

    assert report['eligible_count'] == 2
    assert report['activated_count'] == 1
    assert report['retained_count'] == 0
    assert report['activation_rate'] == 50.0
    assert report['retention_rate'] == 0.0


def test_group_link_is_one_cohort_even_when_multiple_identities_activate():
    definition = COHORT_DEFINITIONS[0]
    start = SimpleNamespace(
        occurred_at=datetime(2026, 1, 1, 15, tzinfo=timezone.utc),
        timezone_name='America/Sao_Paulo',
        contract_version=1,
        cohort_kind='invite_link',
        cohort_key='group-link-1',
    )
    activations = [
        SimpleNamespace(
            journey=definition.journey,
            milestone='app_entry_completed',
            cohort_kind='invite_link',
            cohort_key='group-link-1',
            identity_id=identity_id,
            occurred_at=datetime(2026, 1, day, 15, tzinfo=timezone.utc),
            contract_version=1,
        )
        for identity_id, day in ((701, 2), (702, 3))
    ]
    report = calculate_student_cohort_report(
        definition=definition,
        starts=[start],
        activations=activations,
        returns=[(702, datetime(2026, 1, 9, 15, tzinfo=timezone.utc))],
        now=datetime(2026, 1, 20, tzinfo=timezone.utc),
        coverage_start=None,
    )

    assert report['cohort_unit'] == 'invite_link'
    assert report['eligible_count'] == 1
    assert report['activated_count'] == 1
    assert report['retained_count'] == 1
    assert report['activation_rate'] == 100.0
    assert report['retention_rate'] == 100.0
