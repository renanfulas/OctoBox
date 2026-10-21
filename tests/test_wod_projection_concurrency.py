"""PostgreSQL tenant regression for concurrent weekly WOD distribution."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, time, timedelta
from threading import Barrier
from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import close_old_connections
from django.utils import timezone
from django_tenants.utils import schema_context

from operations.models import ClassSession, ClassType
from operations.services.wod_projection import project_plan_to_sessions
from student_app.models import ReplicationBatch, SessionWorkout, WeeklyWodPlan


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize('share_request_key', [False, True], ids=['independent-retries', 'same-request-replay'])
def test_two_coaches_distributing_same_week_create_only_one_workout(test_tenant, share_request_key):
    """Concurrent requests either skip the collision or replay one committed result."""
    User = get_user_model()
    actor = User.objects.create_user(
        username=f'projection-race-{uuid4().hex}',
        password='test-password',
    )
    today = timezone.localdate()
    week_start = today + timedelta(days=(7 - today.weekday()) % 7)
    session = ClassSession.objects.create(
        title='Aula concorrida',
        class_type=ClassType.CROSS,
        coach=actor,
        scheduled_at=timezone.make_aware(datetime.combine(week_start, time(hour=12))),
        duration_minutes=60,
        capacity=16,
    )
    plan = WeeklyWodPlan.objects.create(
        week_start=week_start,
        label='Plano concorrente',
        status='confirmed',
        created_by=actor,
        parsed_payload={
            'days': [{
                'weekday': 0,
                'weekday_label': 'Segunda',
                'blocks': [{
                    'kind': 'metcon',
                    'title': 'WOD',
                    'movements': [],
                }],
            }],
        },
    )
    barrier = Barrier(2)
    request_key = uuid4() if share_request_key else None

    def attempt_distribution():
        close_old_connections()
        try:
            with schema_context(test_tenant.schema_name):
                thread_actor = User.objects.get(pk=actor.pk)
                thread_plan = WeeklyWodPlan.objects.get(pk=plan.pk)
                barrier.wait(timeout=10)
                try:
                    batch, replay_preview = project_plan_to_sessions(
                        weekly_plan=thread_plan,
                        target_week_start=week_start,
                        class_types=[ClassType.CROSS],
                        actor=thread_actor,
                        idempotency_key=request_key,
                    )
                except ValidationError as exc:
                    return ('skipped', str(exc))
                return ('replayed' if replay_preview.get('idempotent_replay') else 'created', batch.pk)
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda _: attempt_distribution(), range(2)))

    expected_outcomes = ['created', 'replayed'] if share_request_key else ['created', 'skipped']
    assert sorted(result[0] for result in outcomes) == expected_outcomes
    if share_request_key:
        assert outcomes[0][1] == outcomes[1][1]
    assert SessionWorkout.objects.filter(session=session).count() == 1
    assert ReplicationBatch.objects.filter(weekly_plan=plan).count() == 1
    assert SessionWorkout.objects.get(session=session).replication_batch_id == ReplicationBatch.objects.get(
        weekly_plan=plan
    ).pk
