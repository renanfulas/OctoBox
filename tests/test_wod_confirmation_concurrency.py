"""A3/A4: corridas reais com conexões PostgreSQL independentes no tenant de ensaio."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, time, timedelta
import json
from threading import Barrier, Event
from uuid import UUID, uuid4
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.db import close_old_connections, connection, connections
from django.test import Client, override_settings
from django.urls import reverse
from django.utils import timezone
from django_tenants.utils import get_public_schema_name, schema_context

from access.roles import ROLE_COACH, ROLE_MANAGER, ROLE_OWNER, ROLE_RECEPTION
from operations.models import ClassSession, ClassType, SessionStatus, WorkoutApprovalPolicySetting, WorkoutPlannerTemplatePickerEvent, WorkoutProgram, WorkoutTemplate, WorkoutTemplateBlock, WorkoutTemplateMovement
from operations.services.wod_drafts import DraftConflict, resolve_draft_scope, save_draft
from operations.services.wod_apply_intents import WodApplyConflict, confirm_program_apply, prepare_program_apply
from operations.services.wod_preview_contracts import daily_program_snapshot
from operations.workout_approval_policy import update_workout_approval_policy_setting
from student_app.models import SessionWorkout, SessionWorkoutStatus, WodApplyIntent, WodInputDraft


@pytest.mark.django_db(transaction=True)
@pytest.mark.requires_postgres
def test_two_tabs_updating_one_draft_have_one_winner(test_tenant):
    call_command('bootstrap_roles')
    actor = get_user_model().objects.create_user(username=f'wod-draft-race-{uuid4().hex}', password='test-password')
    actor.groups.add(Group.objects.get(name=ROLE_COACH))
    program = WorkoutProgram.objects.create(slug=f'draft-race-{uuid4().hex[:12]}', name='Corrida A3')
    today = timezone.localdate()
    week_start = today + timedelta(days=(7 - today.weekday()) % 7)
    scope = resolve_draft_scope(
        actor=actor, scope_kind='weekly', week_start=week_start.isoformat(),
        workout_program_id=program.pk,
    )
    draft = save_draft(actor=actor, scope=scope, source_text='Original', request_id=uuid4())
    barrier = Barrier(2)

    def write_variant(label):
        close_old_connections()
        try:
            with schema_context(test_tenant.schema_name):
                thread_actor = get_user_model().objects.get(pk=actor.pk)
                thread_scope = resolve_draft_scope(
                    actor=thread_actor, scope_kind='weekly', week_start=week_start.isoformat(),
                    workout_program_id=program.pk,
                )
                barrier.wait(timeout=10)
                try:
                    saved = save_draft(
                        actor=thread_actor, scope=thread_scope, source_text=label,
                        request_id=uuid4(), expected_version=1, draft_id=draft.pk,
                    )
                    return ('saved', saved.version)
                except DraftConflict as error:
                    return (error.code, error.version)
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(write_variant, ['Aba A', 'Aba B']))

    assert sorted(result[0] for result in outcomes) == ['saved', 'stale_version']
    draft.refresh_from_db()
    assert draft.version == 2
    assert draft.source_text in {'Aba A', 'Aba B'}
    assert WodInputDraft.objects.filter(author=actor, scope_key=scope.key, state='active').count() == 1


@pytest.mark.django_db(transaction=True)
@pytest.mark.requires_postgres
def test_same_daily_intent_confirms_once_across_two_connections(test_tenant):
    call_command('bootstrap_roles')
    actor = get_user_model().objects.create_user(username=f'wod-intent-race-{uuid4().hex}', password='test-password')
    actor.groups.add(Group.objects.get(name=ROLE_COACH))
    program = WorkoutProgram.objects.create(slug=f'intent-race-{uuid4().hex[:12]}', name='Corrida A4')
    target_date = timezone.localdate()
    session = ClassSession.objects.create(
        title='Aula A4', class_type=ClassType.CROSS, workout_program=program,
        coach=actor, scheduled_at=timezone.make_aware(datetime.combine(target_date, time(hour=12))),
        duration_minutes=60, capacity=12,
    )
    template = WorkoutTemplate.objects.create(name='Template A4', created_by=actor)
    WorkoutTemplateBlock.objects.create(template=template, kind='strength', title='Força', sort_order=1)
    preview = prepare_program_apply(
        actor=actor, target_date=target_date, template_id=template.pk,
        workout_program_id=program.pk, mode='replace_empty',
    )
    barrier = Barrier(2)

    def confirm():
        close_old_connections()
        try:
            with schema_context(test_tenant.schema_name):
                thread_actor = get_user_model().objects.get(pk=actor.pk)
                http_client = Client()
                http_client.force_login(thread_actor)
                barrier.wait(timeout=10)
                response = http_client.post(
                    reverse('wod-day-program-confirm'),
                    data={
                        'intent_id': preview['intent_id'],
                        'fingerprint': preview['fingerprint'],
                    },
                )
                return response.status_code, response.json()
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: confirm(), range(2)))

    assert [status_code for status_code, _payload in results] == [200, 200]
    assert sorted(payload['idempotent_replay'] for _status_code, payload in results) == [False, True]
    assert SessionWorkout.objects.filter(session=session).count() == 1
    template.refresh_from_db()
    assert template.usage_count == 1


@pytest.mark.django_db(transaction=True)
@pytest.mark.requires_postgres
def test_daily_apply_commits_without_claiming_undo_when_cache_write_fails(test_tenant):
    call_command('bootstrap_roles')
    actor = get_user_model().objects.create_user(username=f'wod-undo-cache-{uuid4().hex}', password='test-password')
    actor.groups.add(Group.objects.get(name=ROLE_COACH))
    program = WorkoutProgram.objects.create(slug=f'undo-cache-{uuid4().hex[:12]}', name='Undo cache')
    target_date = timezone.localdate()
    session = ClassSession.objects.create(
        title='Aula com cache indisponível', class_type=ClassType.CROSS,
        workout_program=program, coach=actor,
        scheduled_at=timezone.make_aware(datetime.combine(target_date, time(hour=12))),
        duration_minutes=60, capacity=12,
    )
    template = WorkoutTemplate.objects.create(name='Template undo cache', created_by=actor)
    WorkoutTemplateBlock.objects.create(template=template, kind='strength', title='Força', sort_order=1)
    preview = prepare_program_apply(
        actor=actor, target_date=target_date, template_id=template.pk,
        workout_program_id=program.pk, mode='replace_empty',
    )

    with patch('operations.services.wod_day_apply_executor.cache.set', side_effect=RuntimeError('cache indisponível')):
        result = confirm_program_apply(
            actor=actor, intent_id=preview['intent_id'],
            request_fingerprint=preview['fingerprint'],
        )

    assert result['applied_count'] == 1
    assert result['undo_token'] == ''
    assert result['undo_expires_at'] is None
    assert result['undo_unavailable'] is True
    assert SessionWorkout.objects.filter(session=session).exists()
    intent = WodApplyIntent.objects.get(pk=preview['intent_id'])
    assert intent.state == WodApplyIntent.State.CONFIRMED
    assert intent.response_payload['undo_token'] == ''
    replay = confirm_program_apply(
        actor=actor, intent_id=preview['intent_id'],
        request_fingerprint=preview['fingerprint'],
    )
    assert replay['idempotent_replay'] is True
    assert replay['undo_unavailable'] is True


@pytest.mark.django_db(transaction=True)
@pytest.mark.requires_postgres
@override_settings(WOD_APPROVAL_POLICY='strict')
@pytest.mark.parametrize('policy_row_exists', (False, True))
def test_policy_update_waits_for_daily_confirmation_snapshot(test_tenant, policy_row_exists):
    """Create/update de política não atravessa o lock da confirmação, com ou sem linha."""
    call_command('bootstrap_roles')
    actor = get_user_model().objects.create_user(username=f'wod-policy-race-{uuid4().hex}', password='test-password')
    actor.groups.add(Group.objects.get(name=ROLE_COACH))
    box_id = 1_800_000_000
    actor.box_id = box_id
    actor.is_trusted_author = True
    program = WorkoutProgram.objects.create(slug=f'policy-race-{uuid4().hex[:12]}', name='Policy race')
    target_date = timezone.localdate()
    session = ClassSession.objects.create(
        title='Aula com política concorrente', class_type=ClassType.CROSS,
        workout_program=program, coach=actor,
        scheduled_at=timezone.make_aware(datetime.combine(target_date, time(hour=12))),
        duration_minutes=60, capacity=12,
    )
    template = WorkoutTemplate.objects.create(name='Template policy race', created_by=actor)
    WorkoutTemplateBlock.objects.create(template=template, kind='strength', title='Força', sort_order=1)
    preview = prepare_program_apply(
        actor=actor, target_date=target_date, template_id=template.pk,
        workout_program_id=program.pk, mode='replace_empty',
    )
    if policy_row_exists:
        WorkoutApprovalPolicySetting.objects.create(box_id=box_id, approval_policy='strict')
    else:
        assert not WorkoutApprovalPolicySetting.objects.filter(box_id=box_id).exists()

    snapshot_ready = Event()
    release_confirmation = Event()
    def pause_after_locked_snapshot(**kwargs):
        result = daily_program_snapshot(**kwargs)
        if kwargs.get('lock'):
            snapshot_ready.set()
            if not release_confirmation.wait(timeout=10):
                raise TimeoutError('A confirmação não foi liberada pelo teste.')
        return result

    def confirm_in_worker():
        close_old_connections()
        try:
            with schema_context(test_tenant.schema_name):
                worker_actor = get_user_model().objects.get(pk=actor.pk)
                worker_actor.box_id = box_id
                worker_actor.is_trusted_author = True
                return confirm_program_apply(
                    actor=worker_actor, intent_id=preview['intent_id'],
                    request_fingerprint=preview['fingerprint'],
                )
        finally:
            connections.close_all()

    def create_policy_in_worker():
        close_old_connections()
        try:
            with schema_context(test_tenant.schema_name):
                worker_actor = get_user_model().objects.get(pk=actor.pk)
                worker_actor.box_id = box_id
                return update_workout_approval_policy_setting(
                    actor=worker_actor, approval_policy='coach_autonomy',
                )
        finally:
            connections.close_all()

    with patch('operations.services.wod_apply_intents.daily_program_snapshot', side_effect=pause_after_locked_snapshot):
        with ThreadPoolExecutor(max_workers=2) as pool:
            confirmation = pool.submit(confirm_in_worker)
            assert snapshot_ready.wait(timeout=10)
            policy_update = pool.submit(create_policy_in_worker)
            try:
                assert not policy_update.done(), 'a política precisa aguardar o snapshot/commit da confirmação'
            finally:
                release_confirmation.set()
            result = confirmation.result(timeout=10)
            setting = policy_update.result(timeout=10)

    assert result['applied_count'] == 1
    assert setting.approval_policy == 'coach_autonomy'
    workout = SessionWorkout.objects.get(session=session)
    assert workout.status == SessionWorkoutStatus.DRAFT


@pytest.mark.django_db(transaction=True)
@pytest.mark.requires_postgres
@override_settings(WOD_APPROVAL_POLICY='strict')
def test_new_daily_destination_waits_for_locked_program_snapshot(test_tenant):
    """FK para o WorkoutProgram bloqueia aula nova até a confirmação linearizar."""
    call_command('bootstrap_roles')
    actor = get_user_model().objects.create_user(username=f'wod-session-race-{uuid4().hex}', password='test-password')
    actor.groups.add(Group.objects.get(name=ROLE_COACH))
    program = WorkoutProgram.objects.create(slug=f'session-race-{uuid4().hex[:12]}', name='Session race')
    target_date = timezone.localdate()
    session = ClassSession.objects.create(
        title='Aula originalmente pré-visualizada', class_type=ClassType.CROSS,
        workout_program=program, coach=actor,
        scheduled_at=timezone.make_aware(datetime.combine(target_date, time(hour=12))),
        duration_minutes=60, capacity=12,
    )
    template = WorkoutTemplate.objects.create(name='Template session race', created_by=actor)
    WorkoutTemplateBlock.objects.create(template=template, kind='strength', title='Força', sort_order=1)
    preview = prepare_program_apply(
        actor=actor, target_date=target_date, template_id=template.pk,
        workout_program_id=program.pk, mode='replace_empty',
    )

    snapshot_ready = Event()
    release_confirmation = Event()

    def pause_after_locked_snapshot(**kwargs):
        result = daily_program_snapshot(**kwargs)
        if kwargs.get('lock'):
            snapshot_ready.set()
            if not release_confirmation.wait(timeout=10):
                raise TimeoutError('A confirmação não foi liberada pelo teste.')
        return result

    def confirm_in_worker():
        close_old_connections()
        try:
            with schema_context(test_tenant.schema_name):
                worker_actor = get_user_model().objects.get(pk=actor.pk)
                return confirm_program_apply(
                    actor=worker_actor, intent_id=preview['intent_id'],
                    request_fingerprint=preview['fingerprint'],
                )
        finally:
            connections.close_all()

    def create_new_destination():
        close_old_connections()
        try:
            with schema_context(test_tenant.schema_name):
                return ClassSession.objects.create(
                    title='Aula criada durante confirmação', class_type=ClassType.CROSS,
                    workout_program=WorkoutProgram.objects.get(pk=program.pk), coach_id=actor.pk,
                    scheduled_at=timezone.make_aware(datetime.combine(target_date, time(hour=15))),
                    duration_minutes=60, capacity=12,
                )
        finally:
            connections.close_all()

    with patch('operations.services.wod_apply_intents.daily_program_snapshot', side_effect=pause_after_locked_snapshot):
        with ThreadPoolExecutor(max_workers=2) as pool:
            confirmation = pool.submit(confirm_in_worker)
            assert snapshot_ready.wait(timeout=10)
            creation = pool.submit(create_new_destination)
            try:
                assert not creation.done(), 'a nova aula deve esperar o lock do programa e a confirmação'
            finally:
                release_confirmation.set()
            result = confirmation.result(timeout=10)
            created_session = creation.result(timeout=10)

    assert result['applied_count'] == 1
    assert SessionWorkout.objects.filter(session=session).exists()
    assert not SessionWorkout.objects.filter(session=created_session).exists()


@pytest.mark.django_db(transaction=True)
@pytest.mark.requires_postgres
@override_settings(WOD_APPROVAL_POLICY='strict')
@pytest.mark.parametrize('change_kind', ('block_create', 'block_edit', 'movement_create', 'movement_edit', 'movement_edit_http'))
def test_template_content_change_waits_for_locked_daily_snapshot(test_tenant, change_kind):
    """Criação/edição paralela de bloco ou movimento não pode cruzar o snapshot."""
    call_command('bootstrap_roles')
    actor = get_user_model().objects.create_user(username=f'wod-template-race-{uuid4().hex}', password='test-password')
    actor.groups.add(Group.objects.get(name=ROLE_COACH))
    program = WorkoutProgram.objects.create(slug=f'template-race-{uuid4().hex[:12]}', name='Template race')
    target_date = timezone.localdate()
    session = ClassSession.objects.create(
        title='Aula com template concorrente', class_type=ClassType.CROSS,
        workout_program=program, coach=actor,
        scheduled_at=timezone.make_aware(datetime.combine(target_date, time(hour=12))),
        duration_minutes=60, capacity=12,
    )
    template = WorkoutTemplate.objects.create(name='Template pré-visualizado', created_by=actor)
    original_block = WorkoutTemplateBlock.objects.create(
        template=template, kind='strength', title='Bloco original', sort_order=1,
    )
    original_movement = WorkoutTemplateMovement.objects.create(
        block=original_block, movement_slug='deadlift',
        movement_label='Levantamento original', sort_order=1,
    )
    preview = prepare_program_apply(
        actor=actor, target_date=target_date, template_id=template.pk,
        workout_program_id=program.pk, mode='replace_empty',
    )

    snapshot_ready = Event()
    release_confirmation = Event()

    def pause_after_locked_snapshot(**kwargs):
        result = daily_program_snapshot(**kwargs)
        if kwargs.get('lock'):
            snapshot_ready.set()
            if not release_confirmation.wait(timeout=10):
                raise TimeoutError('A confirmação não foi liberada pelo teste.')
        return result

    def confirm_in_worker():
        close_old_connections()
        try:
            with schema_context(test_tenant.schema_name):
                worker_actor = get_user_model().objects.get(pk=actor.pk)
                return confirm_program_apply(
                    actor=worker_actor, intent_id=preview['intent_id'],
                    request_fingerprint=preview['fingerprint'],
                )
        finally:
            connections.close_all()

    def change_template():
        close_old_connections()
        try:
            with schema_context(test_tenant.schema_name):
                if change_kind == 'block_create':
                    return WorkoutTemplateBlock.objects.create(
                        template=WorkoutTemplate.objects.get(pk=template.pk),
                        kind='metcon', title='Bloco criado em paralelo', sort_order=2,
                    )
                if change_kind == 'block_edit':
                    block = WorkoutTemplateBlock.objects.get(pk=original_block.pk)
                    block.title = 'Bloco editado em paralelo'
                    block.save(update_fields=['title', 'updated_at'])
                    return block
                if change_kind == 'movement_create':
                    return WorkoutTemplateMovement.objects.create(
                        block=WorkoutTemplateBlock.objects.get(pk=original_block.pk),
                        movement_slug='box_jump', movement_label='Box jump criado em paralelo',
                        sort_order=2,
                    )
                if change_kind == 'movement_edit_http':
                    thread_actor = get_user_model().objects.get(pk=actor.pk)
                    http_client = Client()
                    http_client.force_login(thread_actor)
                    response = http_client.post(
                        reverse('workout-template-update-movement', args=[original_movement.pk]),
                        data={
                            'movement_id': original_movement.pk,
                            'movement_slug': 'deadlift',
                            'movement_label': 'Editado pela rota HTTP',
                            'sets': 5,
                            'reps': 3,
                            'load_type': 'free',
                            'sort_order': 1,
                        },
                    )
                    assert response.status_code == 302
                    return WorkoutTemplateMovement.objects.get(pk=original_movement.pk)
                movement = WorkoutTemplateMovement.objects.get(pk=original_movement.pk)
                movement.movement_label = 'Levantamento editado em paralelo'
                movement.save(update_fields=['movement_label', 'updated_at'])
                return movement
        finally:
            connections.close_all()

    with patch('operations.services.wod_apply_intents.daily_program_snapshot', side_effect=pause_after_locked_snapshot):
        with ThreadPoolExecutor(max_workers=2) as pool:
            confirmation = pool.submit(confirm_in_worker)
            assert snapshot_ready.wait(timeout=10)
            concurrent_change = pool.submit(change_template)
            try:
                assert not concurrent_change.done(), 'conteúdo do template deve esperar o lock da confirmação'
            finally:
                release_confirmation.set()
            result = confirmation.result(timeout=10)
            changed_item = concurrent_change.result(timeout=10)

    assert result['applied_count'] == 1
    workout = SessionWorkout.objects.get(session=session)
    assert list(workout.blocks.order_by('sort_order').values_list('title', flat=True)) == ['Bloco original']
    assert list(workout.blocks.get().movements.order_by('sort_order').values_list('movement_label', flat=True)) == ['Levantamento original']
    if change_kind == 'block_create':
        assert changed_item.template_id == template.pk
        assert WorkoutTemplateBlock.objects.filter(template=template).count() == 2
    elif change_kind == 'block_edit':
        changed_item.refresh_from_db()
        assert changed_item.title == 'Bloco editado em paralelo'
    elif change_kind == 'movement_create':
        assert changed_item.block_id == original_block.pk
        assert WorkoutTemplateMovement.objects.filter(block=original_block).count() == 2
    elif change_kind == 'movement_edit_http':
        changed_item.refresh_from_db()
        assert changed_item.movement_label == 'Editado pela rota HTTP'
    else:
        changed_item.refresh_from_db()
        assert changed_item.movement_label == 'Levantamento editado em paralelo'


@pytest.mark.django_db(transaction=True)
@pytest.mark.requires_postgres
@override_settings(WOD_APPROVAL_POLICY='strict')
def test_existing_session_status_change_waits_for_daily_confirmation(test_tenant):
    """Cancelar uma aula-alvo aguarda o apply e não atravessa sua validação bloqueada."""
    call_command('bootstrap_roles')
    actor = get_user_model().objects.create_user(username=f'wod-session-edit-{uuid4().hex}', password='test-password')
    actor.groups.add(Group.objects.get(name=ROLE_COACH))
    program = WorkoutProgram.objects.create(slug=f'session-edit-{uuid4().hex[:12]}', name='Session edit')
    target_date = timezone.localdate()
    session = ClassSession.objects.create(
        title='Aula que será cancelada em paralelo', class_type=ClassType.CROSS,
        workout_program=program, coach=actor,
        scheduled_at=timezone.make_aware(datetime.combine(target_date, time(hour=12))),
        duration_minutes=60, capacity=12,
    )
    template = WorkoutTemplate.objects.create(name='Template session edit', created_by=actor)
    WorkoutTemplateBlock.objects.create(template=template, kind='strength', title='Bloco conferido', sort_order=1)
    preview = prepare_program_apply(
        actor=actor, target_date=target_date, template_id=template.pk,
        workout_program_id=program.pk, mode='replace_empty',
    )

    snapshot_ready = Event()
    release_confirmation = Event()

    def pause_after_locked_snapshot(**kwargs):
        result = daily_program_snapshot(**kwargs)
        if kwargs.get('lock'):
            snapshot_ready.set()
            if not release_confirmation.wait(timeout=10):
                raise TimeoutError('A confirmação não foi liberada pelo teste.')
        return result

    def confirm_in_worker():
        close_old_connections()
        try:
            with schema_context(test_tenant.schema_name):
                worker_actor = get_user_model().objects.get(pk=actor.pk)
                return confirm_program_apply(
                    actor=worker_actor, intent_id=preview['intent_id'],
                    request_fingerprint=preview['fingerprint'],
                )
        finally:
            connections.close_all()

    def cancel_session():
        close_old_connections()
        try:
            with schema_context(test_tenant.schema_name):
                return ClassSession.objects.filter(pk=session.pk).update(status=SessionStatus.CANCELED)
        finally:
            connections.close_all()

    with patch('operations.services.wod_apply_intents.daily_program_snapshot', side_effect=pause_after_locked_snapshot):
        with ThreadPoolExecutor(max_workers=2) as pool:
            confirmation = pool.submit(confirm_in_worker)
            assert snapshot_ready.wait(timeout=10)
            cancellation = pool.submit(cancel_session)
            try:
                assert not cancellation.done(), 'edição do destino deve esperar o lock da confirmação'
            finally:
                release_confirmation.set()
            result = confirmation.result(timeout=10)
            assert cancellation.result(timeout=10) == 1

    session.refresh_from_db()
    assert result['applied_count'] == 1
    assert session.status == SessionStatus.CANCELED
    assert SessionWorkout.objects.filter(session=session).exists()


@pytest.mark.django_db(transaction=True)
@pytest.mark.requires_postgres
def test_same_author_and_scope_have_independent_drafts_in_two_tenant_schemas(test_tenant):
    """Mesmo autor/escopo lógico não atravessa o search_path de outro box."""
    call_command('bootstrap_roles')
    actor = get_user_model().objects.create_user(username=f'wod-tenant-isolation-{uuid4().hex}', password='test-password')
    actor.groups.add(Group.objects.get(name=ROLE_COACH))
    other_schema = f'box_wod_{uuid4().hex[:12]}'
    with connection.cursor() as cursor:
        cursor.execute(f'CREATE SCHEMA "{other_schema}"')
    call_command('migrate_schemas', schema=other_schema, verbosity=0, interactive=False)

    week_start = timezone.localdate() - timedelta(days=timezone.localdate().weekday())
    with schema_context(test_tenant.schema_name):
        program_a = WorkoutProgram.objects.create(slug=f'wod-isolation-a-{uuid4().hex[:8]}', name='Box A')
        scope_a = resolve_draft_scope(
            actor=actor, scope_kind='weekly', week_start=week_start.isoformat(),
            workout_program_id=program_a.pk,
        )
        draft_a = save_draft(actor=actor, scope=scope_a, source_text='Texto do box A', request_id=uuid4())

    with schema_context(other_schema):
        program_b = WorkoutProgram.objects.create(slug=f'wod-isolation-b-{uuid4().hex[:8]}', name='Box B')
        scope_b = resolve_draft_scope(
            actor=actor, scope_kind='weekly', week_start=week_start.isoformat(),
            workout_program_id=program_b.pk,
        )
        draft_b = save_draft(actor=actor, scope=scope_b, source_text='Texto do box B', request_id=uuid4())
        assert WodInputDraft.objects.filter(author=actor, scope_key=scope_b.key).count() == 1
        assert WodInputDraft.objects.get(pk=draft_b.pk).source_text == 'Texto do box B'

    with schema_context(test_tenant.schema_name):
        assert WodInputDraft.objects.filter(author=actor, scope_key=scope_a.key).count() == 1
        assert WodInputDraft.objects.get(pk=draft_a.pk).source_text == 'Texto do box A'
        assert not WodInputDraft.objects.filter(source_text='Texto do box B').exists()


@pytest.mark.django_db(transaction=True)
@pytest.mark.requires_postgres
def test_daily_intent_from_another_tenant_schema_is_not_replayed(test_tenant):
    """UUID igual em outro schema não pode revelar nem reproduzir a intenção."""
    call_command('bootstrap_roles')
    actor = get_user_model().objects.create_user(
        username=f'wod-intent-schema-{uuid4().hex}', password='test-password',
    )
    actor.groups.add(Group.objects.get(name=ROLE_COACH))
    intent_id = uuid4()
    fingerprint = 'a' * 64
    other_schema = f'box_wod_intent_{uuid4().hex[:12]}'
    with connection.cursor() as cursor:
        cursor.execute(f'CREATE SCHEMA "{other_schema}"')

    try:
        call_command('migrate_schemas', schema=other_schema, verbosity=0, interactive=False)
        with schema_context(other_schema):
            other_actor = get_user_model().objects.create_user(
                pk=actor.pk, username=f'wod-intent-other-schema-{uuid4().hex}',
                password='test-password',
            )
            program = WorkoutProgram.objects.create(
                slug=f'wod-intent-other-{uuid4().hex[:10]}', name='Intent Box B',
            )
            template = WorkoutTemplate.objects.create(
                name='Template Box B', created_by=other_actor,
            )
            foreign_intent = WodApplyIntent.objects.create(
                id=intent_id, author=other_actor,
                target_date=timezone.localdate(), workout_program=program,
                template=template, mode='replace_empty', fingerprint=fingerprint,
                preview_snapshot={'tenant': 'B'},
                expires_at=timezone.now() + timedelta(minutes=30),
            )

        with schema_context(test_tenant.schema_name):
            with pytest.raises(WodApplyConflict) as conflict:
                confirm_program_apply(
                    actor=actor, intent_id=intent_id,
                    request_fingerprint=fingerprint,
                )
            assert conflict.value.code == 'not_found'

        with schema_context(other_schema):
            foreign_intent.refresh_from_db()
            assert foreign_intent.state == WodApplyIntent.State.PREPARED
            assert foreign_intent.response_payload == {}
    finally:
        with connection.cursor() as cursor:
            cursor.execute(f'DROP SCHEMA IF EXISTS "{other_schema}" CASCADE')


@pytest.mark.django_db(transaction=True)
@pytest.mark.requires_postgres
def test_daily_and_weekly_apply_fingerprints_are_tenant_local_with_colliding_ids(test_tenant):
    """Confirmações A4 usam programas, alvos, intents e batches do schema ativo."""
    from django.core.exceptions import ValidationError

    from operations.models import WorkoutTemplateBlock
    from operations.services.wod_apply_intents import (
        WodApplyConflict, confirm_program_apply, prepare_program_apply,
    )
    from operations.services.wod_preview_contracts import read_projection_token, issue_projection_token
    from operations.services.wod_projection import build_projection_preview, project_plan_to_sessions
    from student_app.models import (
        ReplicationBatch, SessionWorkoutBlock, WeeklyWodPlan, WodApplyIntent,
    )

    call_command('bootstrap_roles')
    actor = get_user_model().objects.create_user(
        username=f'wod-apply-two-boxes-{uuid4().hex}', password='test-password',
    )
    actor.groups.add(Group.objects.get(name=ROLE_OWNER))
    other_schema = f'box_wod_apply_{uuid4().hex[:12]}'
    with connection.cursor() as cursor:
        cursor.execute(f'CREATE SCHEMA "{other_schema}"')

    program_id = 3_000_000_001
    template_id = 3_000_000_002
    daily_session_id = 3_000_000_003
    daily_workout_id = 3_000_000_004
    weekly_session_id = 3_000_000_005
    weekly_plan_id = 3_000_000_006
    today = timezone.localdate()
    target_date = today + timedelta(days=1)
    target_week_start = today + timedelta(days=7 - today.weekday())
    daily_at = timezone.make_aware(datetime.combine(target_date, time(hour=12)))
    weekly_at = timezone.make_aware(datetime.combine(target_week_start, time(hour=12)))
    weekly_key = uuid4()
    try:
        call_command('migrate_schemas', schema=other_schema, verbosity=0, interactive=False)
        with schema_context(test_tenant.schema_name):
            program_a = WorkoutProgram.objects.create(
                pk=program_id, slug=f'apply-a-{uuid4().hex[:10]}', name='Programa do Box A',
            )
            template_a = WorkoutTemplate.objects.create(
                pk=template_id, name='Template do Box A', created_by=actor,
            )
            WorkoutTemplateBlock.objects.create(
                template=template_a, title='Bloco do template A', kind='strength', sort_order=1,
            )
            daily_session_a = ClassSession.objects.create(
                pk=daily_session_id, title='Aula diária A', class_type=ClassType.CROSS,
                workout_program=program_a, coach=actor, scheduled_at=daily_at,
                duration_minutes=60, capacity=12,
            )
            daily_workout_a = SessionWorkout.objects.create(
                pk=daily_workout_id, session=daily_session_a, title='Draft diário A original',
                status=SessionWorkoutStatus.DRAFT, created_by=actor,
            )
            weekly_session_a = ClassSession.objects.create(
                pk=weekly_session_id, title='Aula semanal A', class_type=ClassType.CROSS,
                workout_program=program_a, coach=actor, scheduled_at=weekly_at,
                duration_minutes=60, capacity=12,
            )
            plan_a = WeeklyWodPlan.objects.create(
                pk=weekly_plan_id, week_start=target_week_start, workout_program=program_a,
                label='Plano do Box A', source_text='Conteúdo A',
                parsed_payload={'days': [{'weekday': 0, 'blocks': [{
                    'kind': 'strength', 'title': 'Bloco semanal A', 'movements': [],
                }]}]},
                status='confirmed', created_by=actor,
            )
            daily_preview_a = prepare_program_apply(
                actor=actor, target_date=target_date, template_id=template_id,
                workout_program_id=program_id, mode='overwrite',
            )
            daily_result_a = confirm_program_apply(
                actor=actor, intent_id=UUID(daily_preview_a['intent_id']),
                request_fingerprint=daily_preview_a['fingerprint'],
            )
            weekly_preview_a = build_projection_preview(
                weekly_plan=plan_a, target_week_start=target_week_start,
                class_types=[ClassType.CROSS], exclude_completed=True,
            )
            weekly_digest_a = read_projection_token(issue_projection_token(
                weekly_plan=plan_a, target_week_start=target_week_start,
                class_types=[ClassType.CROSS], actor=actor, preview=weekly_preview_a,
                intent_id=weekly_key,
            ))['fingerprint']
            batch_a, projected_a = project_plan_to_sessions(
                weekly_plan=plan_a, target_week_start=target_week_start,
                class_types=[ClassType.CROSS], actor=actor, idempotency_key=weekly_key,
                expected_preview_fingerprint=weekly_digest_a, exclude_completed=True,
            )
            daily_workout_a.refresh_from_db()
            assert daily_result_a['applied_count'] == 1
            assert daily_workout_a.title == 'Template do Box A'
            assert projected_a['totals']['sessions_creatable'] == 1
            weekly_workout_a = SessionWorkout.objects.get(session=weekly_session_a)
            assert SessionWorkoutBlock.objects.get(workout=weekly_workout_a).title == 'Bloco semanal A'

        with schema_context(other_schema):
            program_b = WorkoutProgram.objects.create(
                pk=program_id, slug=f'apply-b-{uuid4().hex[:10]}', name='Programa do Box B',
            )
            template_b = WorkoutTemplate.objects.create(
                pk=template_id, name='Template do Box B', created_by=actor,
            )
            WorkoutTemplateBlock.objects.create(
                template=template_b, title='Bloco do template B', kind='strength', sort_order=1,
            )
            daily_session_b = ClassSession.objects.create(
                pk=daily_session_id, title='Aula diária B', class_type=ClassType.CROSS,
                workout_program=program_b, coach=actor, scheduled_at=daily_at,
                duration_minutes=60, capacity=12,
            )
            daily_workout_b = SessionWorkout.objects.create(
                pk=daily_workout_id, session=daily_session_b, title='Publicado protegido B',
                status=SessionWorkoutStatus.PUBLISHED, created_by=actor,
            )
            weekly_session_b = ClassSession.objects.create(
                pk=weekly_session_id, title='Aula semanal B', class_type=ClassType.CROSS,
                workout_program=program_b, coach=actor, scheduled_at=weekly_at,
                duration_minutes=60, capacity=12,
            )
            plan_b = WeeklyWodPlan.objects.create(
                pk=weekly_plan_id, week_start=target_week_start, workout_program=program_b,
                label='Plano do Box B', source_text='Conteúdo B',
                parsed_payload={'days': [{'weekday': 0, 'blocks': [{
                    'kind': 'strength', 'title': 'Bloco semanal B', 'movements': [],
                }]}]},
                status='confirmed', created_by=actor,
            )
            daily_preview_b = prepare_program_apply(
                actor=actor, target_date=target_date, template_id=template_id,
                workout_program_id=program_id, mode='overwrite',
            )
            intent_b = WodApplyIntent.objects.get(pk=daily_preview_b['intent_id'])
            intent_snapshot_b = intent_b.preview_snapshot
            intent_b.delete()
            WodApplyIntent.objects.create(
                id=UUID(daily_preview_a['intent_id']), author=actor,
                target_date=target_date, workout_program=program_b, template=template_b,
                mode='overwrite', fingerprint=daily_preview_a['fingerprint'],
                preview_snapshot=intent_snapshot_b, expires_at=timezone.now() + timedelta(minutes=30),
            )
            with pytest.raises(WodApplyConflict) as daily_conflict:
                confirm_program_apply(
                    actor=actor, intent_id=UUID(daily_preview_a['intent_id']),
                    request_fingerprint=daily_preview_a['fingerprint'],
                )
            assert daily_conflict.value.code == 'stale_preview'
            daily_workout_b.refresh_from_db()
            assert daily_workout_b.title == 'Publicado protegido B'
            assert daily_workout_b.status == SessionWorkoutStatus.PUBLISHED
            assert WodApplyIntent.objects.get(pk=daily_preview_a['intent_id']).state == WodApplyIntent.State.PREPARED

            weekly_preview_b = build_projection_preview(
                weekly_plan=plan_b, target_week_start=target_week_start,
                class_types=[ClassType.CROSS], exclude_completed=True,
            )
            with pytest.raises(ValidationError, match='mudaram depois da prévia'):
                project_plan_to_sessions(
                    weekly_plan=plan_b, target_week_start=target_week_start,
                    class_types=[ClassType.CROSS], actor=actor, idempotency_key=weekly_key,
                    expected_preview_fingerprint=weekly_digest_a, exclude_completed=True,
                )
            assert not ReplicationBatch.objects.filter(idempotency_key=weekly_key).exists()
            assert not SessionWorkout.objects.filter(session=weekly_session_b).exists()
            weekly_digest_b = read_projection_token(issue_projection_token(
                weekly_plan=plan_b, target_week_start=target_week_start,
                class_types=[ClassType.CROSS], actor=actor, preview=weekly_preview_b,
                intent_id=weekly_key,
            ))['fingerprint']
            batch_b, projected_b = project_plan_to_sessions(
                weekly_plan=plan_b, target_week_start=target_week_start,
                class_types=[ClassType.CROSS], actor=actor, idempotency_key=weekly_key,
                expected_preview_fingerprint=weekly_digest_b, exclude_completed=True,
            )
            assert projected_b['totals']['sessions_creatable'] == 1
            weekly_workout_b = SessionWorkout.objects.get(session=weekly_session_b)
            assert SessionWorkoutBlock.objects.get(workout=weekly_workout_b).title == 'Bloco semanal B'
            assert ReplicationBatch.objects.filter(idempotency_key=weekly_key).count() == 1

        with schema_context(test_tenant.schema_name):
            daily_workout_a.refresh_from_db()
            assert daily_workout_a.title == 'Template do Box A'
            assert ReplicationBatch.objects.get(pk=batch_a.pk).weekly_plan_id == weekly_plan_id
            assert ReplicationBatch.objects.filter(idempotency_key=weekly_key).count() == 1
        with schema_context(other_schema):
            assert ReplicationBatch.objects.get(pk=batch_b.pk).weekly_plan_id == weekly_plan_id
    finally:
        with connection.cursor() as cursor:
            cursor.execute(f'DROP SCHEMA IF EXISTS "{other_schema}" CASCADE')


@pytest.mark.django_db(transaction=True)
@pytest.mark.requires_postgres
def test_weekly_draft_routes_do_not_read_or_mutate_another_tenant_schema(test_tenant):
    """Rotas resolvem plano e draft pelo tenant ativo mesmo com PKs colidentes."""
    from control.models import Box, Membership
    from student_app.models import WeeklyWodPlan

    call_command('bootstrap_roles')
    actor = get_user_model().objects.create_user(
        username=f'wod-draft-schema-http-{uuid4().hex}', password='test-password',
    )
    actor.groups.add(Group.objects.get(name=ROLE_COACH))
    Membership.objects.update_or_create(
        user=actor, box=test_tenant,
        defaults={'role': Membership.Role.COACH, 'is_primary_box': True},
    )
    suffix = uuid4().hex[:12]
    other_schema = f'box_wod_draft_{suffix}'
    with schema_context(get_public_schema_name()):
        box_b = Box.objects.create(
            slug=f'wod-draft-{suffix}',
            schema_name=other_schema,
            display_name='WOD Draft Box B',
            status=Box.Status.ACTIVE,
            owner_user=actor,
        )
        Membership.objects.create(
            user=actor, box=box_b, role=Membership.Role.COACH, is_primary_box=False,
        )
    with connection.cursor() as cursor:
        cursor.execute(f'CREATE SCHEMA "{other_schema}"')

    try:
        call_command('migrate_schemas', schema=other_schema, verbosity=0, interactive=False)
        week_start = timezone.localdate() - timedelta(days=timezone.localdate().weekday())
        with schema_context(test_tenant.schema_name):
            program_a = WorkoutProgram.objects.create(
                slug=f'wod-draft-a-{suffix}', name='Draft Isolation A',
            )
        with schema_context(other_schema):
            program_b = WorkoutProgram.objects.create(
                pk=program_a.pk, slug=f'wod-draft-b-{suffix}', name='Draft Isolation B',
            )
            plan_b = WeeklyWodPlan.objects.create(
                week_start=week_start,
                workout_program=program_b,
                created_by=actor,
                source_text='Plano semanal privado B',
            )
            scope_b = resolve_draft_scope(
                actor=actor, scope_kind='weekly', week_start=week_start.isoformat(),
                workout_program_id=program_b.pk, plan_id=plan_b.pk,
            )
            draft_b = save_draft(
                actor=actor, scope=scope_b, source_text='Texto confidencial do Box B',
                request_id=uuid4(),
            )

        client = Client()
        client.force_login(actor)

        def select_box(box):
            session = client.session
            session['active_box_id'] = box.pk
            session.save()

        select_box(test_tenant)
        scope_params = {
            'scope_kind': 'weekly', 'week_start': week_start.isoformat(),
            'workout_program_id': program_a.pk,
        }
        read_without_plan = client.get(reverse('wod-input-draft'), scope_params)
        assert read_without_plan.status_code == 200
        assert read_without_plan.json()['draft'] is None
        assert 'Texto confidencial do Box B' not in read_without_plan.content.decode()

        foreign_plan = client.get(reverse('wod-input-draft'), {
            **scope_params, 'plan_id': plan_b.pk,
        })
        assert foreign_plan.status_code == 404
        assert foreign_plan.json()['code'] == 'scope_not_found'

        foreign_update = client.post(
            reverse('wod-input-draft'),
            data=json.dumps({
                **scope_params, 'action': 'save', 'source_text': 'Tentativa no Box A',
                'request_id': str(uuid4()), 'draft_id': str(draft_b.pk),
                'expected_version': draft_b.version,
            }),
            content_type='application/json',
        )
        assert foreign_update.status_code == 409
        assert foreign_update.json()['code'] == 'draft_missing'

        with schema_context(other_schema):
            draft_b.refresh_from_db()
            assert draft_b.source_text == 'Texto confidencial do Box B'
            assert draft_b.version == 1

        select_box(box_b)
        read_box_b = client.get(reverse('wod-input-draft'), {
            **scope_params, 'plan_id': plan_b.pk,
        })
        assert read_box_b.status_code == 200
        assert read_box_b.json()['draft']['source_text'] == 'Texto confidencial do Box B'
        assert read_box_b.json()['draft']['draft_id'] == str(draft_b.pk)
    finally:
        with schema_context(get_public_schema_name()):
            Membership.objects.filter(user=actor, box_id__in=[test_tenant.pk, box_b.pk]).delete()
            box_b.delete()
        with connection.cursor() as cursor:
            cursor.execute(f'DROP SCHEMA IF EXISTS "{other_schema}" CASCADE')


@pytest.mark.django_db(transaction=True)
@pytest.mark.requires_postgres
def test_workout_planner_actions_do_not_touch_another_tenant_schema(test_tenant):
    """Ações do planner enxergam somente aulas e WODs do tenant ativo."""
    from control.models import Box, Membership

    call_command('bootstrap_roles')
    actor = get_user_model().objects.create_user(
        username=f'wod-planner-schema-http-{uuid4().hex}', password='test-password',
    )
    actor.groups.add(Group.objects.get(name=ROLE_COACH))
    Membership.objects.update_or_create(
        user=actor, box=test_tenant,
        defaults={'role': Membership.Role.COACH, 'is_primary_box': True},
    )
    suffix = uuid4().hex[:12]
    other_schema = f'box_wod_planner_{suffix}'
    with schema_context(get_public_schema_name()):
        box_b = Box.objects.create(
            slug=f'wod-planner-{suffix}',
            schema_name=other_schema,
            display_name='WOD Planner Box B',
            status=Box.Status.ACTIVE,
            owner_user=actor,
        )
        Membership.objects.create(
            user=actor, box=box_b, role=Membership.Role.COACH, is_primary_box=False,
        )
    with connection.cursor() as cursor:
        cursor.execute(f'CREATE SCHEMA "{other_schema}"')

    try:
        call_command('migrate_schemas', schema=other_schema, verbosity=0, interactive=False)
        target_date = timezone.localdate() + timedelta(days=280)
        target_date -= timedelta(days=target_date.weekday())
        with schema_context(test_tenant.schema_name):
            absent_session_id = (ClassSession.objects.order_by('-pk').values_list('pk', flat=True).first() or 0) + 10000
            assert not ClassSession.objects.filter(pk=absent_session_id).exists()
        with schema_context(other_schema):
            foreign_session = ClassSession.objects.create(
                pk=absent_session_id,
                title='Aula exclusiva do Box B',
                coach=actor,
                scheduled_at=timezone.make_aware(datetime.combine(target_date, time(9, 0))),
                duration_minutes=60,
                capacity=16,
            )
            foreign_workout = SessionWorkout.objects.create(
                session=foreign_session,
                title='WOD que pertence ao Box B',
                status=SessionWorkoutStatus.DRAFT,
                created_by=actor,
            )

        client = Client()
        client.force_login(actor)
        active_session = client.session
        active_session['active_box_id'] = test_tenant.pk
        active_session.save()

        duplicate = client.post(reverse(
            'workout-planner-duplicate-previous-slot', args=[foreign_session.pk],
        ))
        assert duplicate.status_code == 404
        delete = client.post(reverse(
            'workout-planner-delete-selected-workout', args=[foreign_session.pk],
        ), data={'week': target_date.isoformat()})
        assert delete.status_code == 404

        # O Coach não tem sessões nessa semana no Box A. Limpar a semana deve
        # operar no schema ativo e preservar o mesmo intervalo no Box B.
        clear_week = client.post(
            reverse('workout-planner-clear-week'), data={'week': target_date.isoformat()},
        )
        assert clear_week.status_code == 302
        with schema_context(other_schema):
            foreign_workout.refresh_from_db()
            assert foreign_workout.title == 'WOD que pertence ao Box B'
            assert SessionWorkout.objects.filter(pk=foreign_workout.pk).exists()

        manager = get_user_model().objects.create_user(
            username=f'wod-planner-telemetry-{uuid4().hex}', password='test-password',
        )
        manager.groups.add(Group.objects.get(name=ROLE_MANAGER))
        Membership.objects.update_or_create(
            user=manager, box=test_tenant,
            defaults={'role': Membership.Role.MANAGER, 'is_primary_box': True},
        )
        manager_client = Client()
        manager_client.force_login(manager)
        manager_session = manager_client.session
        manager_session['active_box_id'] = test_tenant.pk
        manager_session.save()
        telemetry = manager_client.post(
            reverse('workout-planner-template-picker-telemetry'),
            data={'event_name': 'opened', 'session_id': str(foreign_session.pk)},
        )
        assert telemetry.status_code == 204
        assert not WorkoutPlannerTemplatePickerEvent.objects.filter(actor=manager).exists()

        with schema_context(test_tenant.schema_name):
            local_session = ClassSession.objects.create(
                title='Cross local do Box A',
                coach=actor,
                scheduled_at=timezone.make_aware(datetime.combine(target_date, time(10, 0))),
                duration_minutes=60,
                capacity=16,
            )
            local_template = WorkoutTemplate.objects.create(
                name='Template confiável local A', created_by=actor,
                is_active=True, is_trusted=True,
            )
            absent_template_id = (
                WorkoutTemplate.objects.order_by('-pk').values_list('pk', flat=True).first() or 0
            ) + 10000
        with schema_context(other_schema):
            foreign_template = WorkoutTemplate.objects.create(
                pk=absent_template_id,
                name='Template confiável exclusivo B', created_by=actor,
                is_active=True, is_trusted=True,
            )
            WorkoutTemplateBlock.objects.create(
                template=foreign_template, title='Bloco privado B', kind='strength', sort_order=1,
            )

        # Sessão B + template A e sessão A + template B falham no tenant ativo.
        foreign_session_apply = manager_client.post(reverse(
            'workout-planner-apply-trusted-template',
            args=[foreign_session.pk, local_template.pk],
        ))
        assert foreign_session_apply.status_code == 404
        foreign_template_apply = manager_client.post(reverse(
            'workout-planner-apply-trusted-template',
            args=[local_session.pk, foreign_template.pk],
        ))
        assert foreign_template_apply.status_code == 404
        with schema_context(test_tenant.schema_name):
            assert not SessionWorkout.objects.filter(session=local_session).exists()
        with schema_context(other_schema):
            foreign_template.refresh_from_db()
            assert foreign_template.name == 'Template confiável exclusivo B'
            assert foreign_template.blocks.filter(title='Bloco privado B').exists()
    finally:
        with schema_context(get_public_schema_name()):
            Membership.objects.filter(user=actor, box_id__in=[test_tenant.pk, box_b.pk]).delete()
            box_b.delete()
        with connection.cursor() as cursor:
            cursor.execute(f'DROP SCHEMA IF EXISTS "{other_schema}" CASCADE')


@pytest.mark.django_db(transaction=True)
@pytest.mark.requires_postgres
def test_workout_action_and_rm_routes_do_not_resolve_another_tenant_schema(test_tenant):
    """Approval/history/editor/RM routes resolve supplied IDs only in active A."""
    from control.models import Box, Membership
    from operations.models import Attendance, AttendanceStatus
    from students.models import Student
    from student_app.models import (
        SessionWorkoutFollowUpAction,
        SessionWorkoutBlock,
        SessionWorkoutMovement,
        SessionWorkoutOperationalMemory,
        SessionWorkoutRmGapAction,
        StudentExerciseMax,
        WorkoutLoadType,
        WorkoutWeeklyManagementCheckpoint,
    )

    call_command('bootstrap_roles')
    actor = get_user_model().objects.create_user(
        username=f'wod-actions-schema-http-{uuid4().hex}', password='test-password',
    )
    actor.groups.add(Group.objects.get(name=ROLE_OWNER))
    Membership.objects.update_or_create(
        user=actor, box=test_tenant,
        defaults={'role': Membership.Role.OWNER, 'is_primary_box': True},
    )
    suffix = uuid4().hex[:12]
    other_schema = f'box_wod_actions_{suffix}'
    coach_actor = get_user_model().objects.create_user(
        username=f'wod-actions-coach-schema-http-{uuid4().hex}', password='test-password',
    )
    coach_actor.groups.add(Group.objects.get(name=ROLE_COACH))
    with schema_context(get_public_schema_name()):
        box_b = Box.objects.create(
            slug=f'wod-actions-{suffix}', schema_name=other_schema,
            display_name='WOD Actions Box B', status=Box.Status.ACTIVE, owner_user=actor,
        )
        Membership.objects.create(
            user=actor, box=box_b, role=Membership.Role.OWNER, is_primary_box=False,
        )
        Membership.objects.update_or_create(
            user=coach_actor, box=test_tenant,
            defaults={'role': Membership.Role.COACH, 'is_primary_box': False},
        )
        Membership.objects.create(
            user=coach_actor, box=box_b, role=Membership.Role.COACH, is_primary_box=True,
        )
    with connection.cursor() as cursor:
        cursor.execute(f'CREATE SCHEMA "{other_schema}"')

    pending_id = 2_000_000_000
    published_id = pending_id + 1
    session_pending_id = pending_id + 2
    session_published_id = pending_id + 3
    student_id = pending_id + 4
    collision_id = pending_id + 5
    session_collision_id = pending_id + 6
    coach_session_id = pending_id + 7
    scheduled_at = timezone.now() + timedelta(days=14)
    try:
        call_command('migrate_schemas', schema=other_schema, verbosity=0, interactive=False)
        with schema_context(test_tenant.schema_name):
            assert not SessionWorkout.objects.filter(pk__in=[pending_id, published_id]).exists()
            assert not Student.objects.filter(pk=student_id).exists()
            local_collision_session = ClassSession.objects.create(
                title='Aula local para colisão A', coach=actor,
                scheduled_at=scheduled_at, duration_minutes=60, capacity=16,
            )
            local_collision = SessionWorkout.objects.create(
                pk=collision_id, session=local_collision_session,
                title='Draft local A com PK coincidente',
                status=SessionWorkoutStatus.DRAFT, created_by=actor,
            )
            local_published_session = ClassSession.objects.create(
                pk=session_published_id, title='Aula publicada colisão A', coach=actor,
                scheduled_at=scheduled_at + timedelta(hours=1), duration_minutes=60, capacity=16,
            )
            local_published = SessionWorkout.objects.create(
                pk=published_id, session=local_published_session,
                title='Publicado local A com PK coincidente',
                status=SessionWorkoutStatus.PUBLISHED, created_by=actor,
            )
            local_student = Student.objects.create(
                pk=student_id, full_name='Aluno local A', phone='5511999990001',
                email='aluno-local-a@example.test',
            )
            Attendance.objects.create(
                student=local_student, session=local_published_session, status=AttendanceStatus.BOOKED,
            )
            rm_block = SessionWorkoutBlock.objects.create(
                workout=local_published, title='Força com RM', kind='strength', sort_order=1,
            )
            SessionWorkoutMovement.objects.create(
                block=rm_block, movement_slug='deadlift', movement_label='Deadlift',
                load_type=WorkoutLoadType.PERCENTAGE_OF_RM, sort_order=1,
            )
        with schema_context(other_schema):
            pending_session = ClassSession.objects.create(
                pk=session_pending_id, title='Aula pendente exclusiva B', coach=actor,
                scheduled_at=scheduled_at, duration_minutes=60, capacity=16,
            )
            pending = SessionWorkout.objects.create(
                pk=pending_id, session=pending_session, title='Pendente privado B',
                status=SessionWorkoutStatus.PENDING_APPROVAL, created_by=actor,
                submitted_by=actor, submitted_at=scheduled_at,
            )
            collision_session = ClassSession.objects.create(
                pk=session_collision_id, title='Aula da colisão exclusiva B', coach=actor,
                scheduled_at=scheduled_at + timedelta(hours=2), duration_minutes=60, capacity=16,
            )
            pending_collision = SessionWorkout.objects.create(
                pk=collision_id, session=collision_session, title='Pendente B com PK coincidente',
                status=SessionWorkoutStatus.PENDING_APPROVAL, created_by=actor,
                submitted_by=actor, submitted_at=scheduled_at,
            )
            published_session = ClassSession.objects.create(
                pk=session_published_id, title='Aula publicada exclusiva B', coach=actor,
                scheduled_at=scheduled_at + timedelta(hours=1), duration_minutes=60, capacity=16,
            )
            coach_session = ClassSession.objects.create(
                pk=coach_session_id, title='Aula do Coach exclusiva B', coach=coach_actor,
                scheduled_at=scheduled_at + timedelta(hours=3), duration_minutes=60, capacity=16,
            )
            published = SessionWorkout.objects.create(
                pk=published_id, session=published_session, title='Publicado privado B',
                status=SessionWorkoutStatus.PUBLISHED, created_by=actor,
            )
            student = Student.objects.create(
                pk=student_id, full_name='Aluno privado B', phone='5511987654321',
                email='aluno-privado-b@example.test',
            )
            Attendance.objects.create(
                student=student, session=published_session, status=AttendanceStatus.BOOKED,
            )
            today = timezone.localdate()
            week_start = today - timedelta(days=today.weekday())
            foreign_checkpoint = WorkoutWeeklyManagementCheckpoint.objects.create(
                week_start=week_start, execution_status='completed',
                responsible_role='owner', closure_status='complete',
                governance_commitment_status='executed',
                summary_note='Checkpoint exclusivo do Box B.', updated_by=actor,
            )

        client = Client()
        client.force_login(actor)
        active_session = client.session
        active_session['active_box_id'] = test_tenant.pk
        active_session.save()

        board = client.get(reverse('workout-approval-board'))
        assert board.status_code == 200
        assert 'Pendente privado B' not in board.content.decode()
        assert client.post(reverse('workout-approval-action', args=[pending_id, 'approve'])).status_code == 404
        batch = client.post(
            reverse('workout-approval-batch-action'),
            data={'workout_ids': [str(pending_id), str(collision_id)]},
        )
        assert batch.status_code == 302
        assert client.post(reverse('workout-approval-action', args=[collision_id, 'approve'])).status_code == 302
        follow_up = client.post(reverse('workout-follow-up-action', args=[published_id]), data={
            'action_key': 'desk-follow-up', 'action_label': 'Avisar turma',
            'result_status': 'completed', 'outcome_note': 'Registrado no box A.',
        })
        assert follow_up.status_code == 302
        memory = client.post(reverse('workout-operational-memory-create', args=[published_id]), data={
            'kind': 'monitoring_note', 'note': 'Memória local do box A.',
        })
        assert memory.status_code == 302
        rm_gap = client.post(reverse('workout-rm-gap-action', args=[published_id]), data={
            'student_id': str(student_id), 'exercise_slug': 'deadlift',
            'exercise_label': 'Deadlift', 'status': 'requested', 'note': 'Solicitado no box A.',
        })
        assert rm_gap.status_code == 302
        quick_edit = client.get(reverse('workout-student-rm-quick-edit', args=[published_id, student_id, 'deadlift']))
        assert quick_edit.status_code == 200
        assert 'Aluno local A' in quick_edit.content.decode()
        quick_edit_post = client.post(
            reverse('workout-student-rm-quick-edit', args=[published_id, student_id, 'deadlift']),
            data={'exercise_label': 'Deadlift', 'one_rep_max_kg': '100.00', 'notes': 'RM local A.'},
        )
        assert quick_edit_post.status_code == 302
        preview = client.get(
            reverse('workout-prescription-preview', args=[session_published_id]),
            data={'movement_slug': 'deadlift', 'load_type': WorkoutLoadType.PERCENTAGE_OF_RM, 'load_value': '70'},
        )
        assert preview.status_code == 200
        assert [item['name'] for item in preview.json()['students']] == ['Aluno local A']
        editor = client.get(reverse('coach-session-workout-editor', args=[session_published_id]))
        assert editor.status_code == 200
        assert 'Aula publicada colisão A' in editor.content.decode()
        coach_client = Client()
        coach_client.force_login(coach_actor)
        coach_session_state = coach_client.session
        coach_session_state['active_box_id'] = test_tenant.pk
        coach_session_state.save()
        assert coach_client.get(reverse('coach-session-workout-editor', args=[coach_session_id])).status_code == 404
        coach_session_state = coach_client.session
        coach_session_state['active_box_id'] = box_b.pk
        coach_session_state.save()
        coach_editor = coach_client.get(reverse('coach-session-workout-editor', args=[coach_session_id]))
        assert coach_editor.status_code == 200
        assert 'Aula do Coach exclusiva B' in coach_editor.content.decode()
        checkpoint_response = client.post(reverse('workout-weekly-checkpoint-update'), data={
            'execution_status': 'in_progress',
            'responsible_role': 'manager',
            'closure_status': 'partial',
            'governance_commitment_status': 'assumed',
            'governance_commitment_note': 'Compromisso do Box A.',
            'summary_note': 'Checkpoint criado no Box A.',
        })
        assert checkpoint_response.status_code == 302
        assert WorkoutWeeklyManagementCheckpoint.objects.get(week_start=week_start).summary_note == 'Checkpoint criado no Box A.'

        with schema_context(other_schema):
            pending.refresh_from_db()
            pending_collision.refresh_from_db()
            published.refresh_from_db()
            assert pending.status == SessionWorkoutStatus.PENDING_APPROVAL
            assert pending_collision.status == SessionWorkoutStatus.PENDING_APPROVAL
            assert published.status == SessionWorkoutStatus.PUBLISHED
            assert not SessionWorkoutFollowUpAction.objects.filter(workout=published).exists()
            assert not SessionWorkoutOperationalMemory.objects.filter(workout=published).exists()
            assert not SessionWorkoutRmGapAction.objects.filter(workout=published).exists()
            assert not student.exercise_maxes.exists()
            foreign_checkpoint.refresh_from_db()
            assert foreign_checkpoint.summary_note == 'Checkpoint exclusivo do Box B.'
        with schema_context(test_tenant.schema_name):
            local_collision.refresh_from_db()
            assert local_collision.status == SessionWorkoutStatus.DRAFT
            assert SessionWorkoutFollowUpAction.objects.filter(workout=local_published).count() == 1
            assert SessionWorkoutOperationalMemory.objects.filter(workout=local_published).count() == 1
            assert StudentExerciseMax.objects.filter(
                student=local_student, exercise_slug='deadlift', one_rep_max_kg='100.00',
            ).exists()
            assert SessionWorkoutRmGapAction.objects.get(workout=local_published, student=local_student).status == 'collected'
    finally:
        with schema_context(get_public_schema_name()):
            Membership.objects.filter(user=actor, box_id__in=[test_tenant.pk, box_b.pk]).delete()
            Membership.objects.filter(user=coach_actor, box_id__in=[test_tenant.pk, box_b.pk]).delete()
            box_b.delete()
        with connection.cursor() as cursor:
            cursor.execute(f'DROP SCHEMA IF EXISTS "{other_schema}" CASCADE')


@pytest.mark.django_db(transaction=True)
@pytest.mark.requires_postgres
def test_daily_and_weekly_apply_http_routes_follow_active_tenant_and_membership_role(test_tenant):
    """Preview/confirm HTTP resolve colliding IDs and ACL from active_box_id."""
    from control.models import Box, Membership
    from student_app.models import ReplicationBatch, WeeklyWodPlan

    call_command('bootstrap_roles')
    actor = get_user_model().objects.create_user(
        username=f'wod-apply-http-schema-{uuid4().hex}', password='test-password',
    )
    actor.groups.add(Group.objects.get(name=ROLE_OWNER), Group.objects.get(name=ROLE_COACH))
    receptionist = get_user_model().objects.create_user(
        username=f'wod-apply-http-reception-{uuid4().hex}', password='test-password',
    )
    receptionist.groups.add(Group.objects.get(name=ROLE_OWNER))
    manager = get_user_model().objects.create_user(
        username=f'wod-apply-http-manager-{uuid4().hex}', password='test-password',
    )
    manager.groups.add(Group.objects.get(name=ROLE_MANAGER))
    Membership.objects.update_or_create(
        user=actor, box=test_tenant,
        defaults={'role': Membership.Role.OWNER, 'is_primary_box': True},
    )
    suffix = uuid4().hex[:12]
    other_schema = f'box_wod_apply_http_{suffix}'
    with schema_context(get_public_schema_name()):
        box_b = Box.objects.create(
            slug=f'wod-apply-http-{suffix}', schema_name=other_schema,
            display_name='WOD Apply HTTP Box B', status=Box.Status.ACTIVE,
            owner_user=actor,
        )
        Membership.objects.create(
            user=actor, box=box_b, role=Membership.Role.COACH, is_primary_box=False,
        )
        Membership.objects.create(
            user=manager, box=box_b, role=Membership.Role.MANAGER, is_primary_box=True,
        )
        Membership.objects.create(
            user=receptionist, box=box_b, role=Membership.Role.RECEPTION, is_primary_box=False,
        )
        Membership.objects.update_or_create(
            user=receptionist, box=test_tenant,
            defaults={'role': Membership.Role.RECEPTION, 'is_primary_box': True},
        )
    with connection.cursor() as cursor:
        cursor.execute(f'CREATE SCHEMA "{other_schema}"')

    target_date = timezone.localdate() + timedelta(days=1)
    target_week_start = timezone.localdate() + timedelta(days=7 - timezone.localdate().weekday())
    # Keep the separate manager daily destination outside the weekly projection
    # window; otherwise the confirmed program-scoped weekly plan must include it.
    manager_daily_date = target_date - timedelta(days=1)
    manager_week_start = target_week_start + timedelta(days=7)
    daily_at = timezone.make_aware(datetime.combine(target_date, time(hour=12)))
    weekly_at = timezone.make_aware(datetime.combine(target_week_start, time(hour=12)))
    manager_daily_at = timezone.make_aware(datetime.combine(manager_daily_date, time(hour=12)))
    manager_weekly_at = timezone.make_aware(datetime.combine(manager_week_start, time(hour=12)))
    try:
        call_command('migrate_schemas', schema=other_schema, verbosity=0, interactive=False)
        with schema_context(test_tenant.schema_name):
            program_a = WorkoutProgram.objects.create(
                slug=f'wod-http-a-{suffix}', name='Programa HTTP Box A',
            )
            template_a = WorkoutTemplate.objects.create(name='Template HTTP Box A', created_by=actor)
            WorkoutTemplateBlock.objects.create(
                template=template_a, title='Bloco diário A', kind='strength', sort_order=1,
            )
            daily_session_a = ClassSession.objects.create(
                title='Aula diária HTTP A', class_type=ClassType.CROSS,
                workout_program=program_a, coach=actor, scheduled_at=daily_at,
                duration_minutes=60, capacity=12,
            )
            weekly_session_a = ClassSession.objects.create(
                title='Aula semanal HTTP A', class_type=ClassType.CROSS,
                workout_program=program_a, coach=actor, scheduled_at=weekly_at,
                duration_minutes=60, capacity=12,
            )
            plan_a = WeeklyWodPlan.objects.create(
                week_start=target_week_start, workout_program=program_a,
                label='Plano HTTP A', source_text='Fonte Box A',
                parsed_payload={'days': [{'weekday': 0, 'blocks': [{
                    'kind': 'strength', 'title': 'Bloco semanal A', 'movements': [],
                }]}]},
                status='confirmed', created_by=actor,
            )
        with schema_context(other_schema):
            program_b = WorkoutProgram.objects.create(
                pk=program_a.pk, slug=f'wod-http-b-{suffix}', name='Programa HTTP Box B',
            )
            template_b = WorkoutTemplate.objects.create(
                pk=template_a.pk, name='Template HTTP Box B', created_by=actor,
            )
            WorkoutTemplateBlock.objects.create(
                template=template_b, title='Bloco diário B', kind='strength', sort_order=1,
            )
            daily_session_b = ClassSession.objects.create(
                pk=daily_session_a.pk, title='Aula diária HTTP B', class_type=ClassType.CROSS,
                workout_program=program_b, coach=actor, scheduled_at=daily_at,
                duration_minutes=60, capacity=12,
            )
            weekly_session_b = ClassSession.objects.create(
                pk=weekly_session_a.pk, title='Aula semanal HTTP B', class_type=ClassType.CROSS,
                workout_program=program_b, coach=actor, scheduled_at=weekly_at,
                duration_minutes=60, capacity=12,
            )
            plan_b = WeeklyWodPlan.objects.create(
                pk=plan_a.pk, week_start=target_week_start, workout_program=program_b,
                label='Plano HTTP B', source_text='Fonte Box B',
                parsed_payload={'days': [{'weekday': 0, 'blocks': [{
                    'kind': 'strength', 'title': 'Bloco semanal B', 'movements': [],
                }]}]},
                status='confirmed', created_by=actor,
            )
            manager_daily_session_b = ClassSession.objects.create(
                pk=1_900_000_000,
                title='Aula diária Manager Box B', class_type=ClassType.CROSS,
                workout_program=program_b, coach=actor, scheduled_at=manager_daily_at,
                duration_minutes=60, capacity=12,
            )
            other_coach_daily_session_b = ClassSession.objects.create(
                pk=1_900_000_002,
                title='Aula diária de outro Coach B', class_type=ClassType.CROSS,
                workout_program=program_b, coach=manager, scheduled_at=daily_at,
                duration_minutes=60, capacity=12,
            )
            manager_weekly_session_b = ClassSession.objects.create(
                pk=1_900_000_001,
                title='Aula semanal Manager Box B', class_type=ClassType.CROSS,
                workout_program=program_b, coach=actor, scheduled_at=manager_weekly_at,
                duration_minutes=60, capacity=12,
            )
            manager_plan_b = WeeklyWodPlan.objects.create(
                pk=1_900_000_000,
                week_start=manager_week_start, workout_program=program_b,
                label='Plano semanal Manager B', source_text='Fonte Manager Box B',
                parsed_payload={'days': [{'weekday': 0, 'blocks': [{
                    'kind': 'strength', 'title': 'Bloco semanal Manager B', 'movements': [],
                }]}]},
                status='confirmed', created_by=manager,
            )
        with schema_context(test_tenant.schema_name):
            manager_daily_session_a_decoy = ClassSession.objects.create(
                pk=1_900_000_000,
                title='Aula diária Manager decoy A', class_type=ClassType.CROSS,
                workout_program=program_a, coach=actor,
                scheduled_at=manager_daily_at, duration_minutes=60, capacity=12,
            )
            manager_weekly_session_a_decoy = ClassSession.objects.create(
                pk=1_900_000_001,
                title='Aula semanal Manager decoy A', class_type=ClassType.CROSS,
                workout_program=program_a, coach=actor,
                scheduled_at=manager_weekly_at, duration_minutes=60, capacity=12,
            )
            manager_plan_a_decoy = WeeklyWodPlan.objects.create(
                pk=1_900_000_000,
                week_start=manager_week_start, workout_program=program_a,
                label='Plano semanal Manager decoy A', source_text='Fonte decoy A',
                parsed_payload={'days': [{'weekday': 0, 'blocks': [{
                    'kind': 'strength', 'title': 'Bloco decoy A', 'movements': [],
                }]}]},
                status='confirmed', created_by=manager,
            )

        client = Client()
        client.force_login(actor)

        def select_box(box):
            session = client.session
            session['active_box_id'] = box.pk
            session.save()

        for box, program, template, expected_daily, expected_weekly in (
            (test_tenant, program_a, template_a, 'Aula diária HTTP A', 'Aula semanal HTTP A'),
            (box_b, program_b, template_b, 'Aula diária HTTP B', 'Aula semanal HTTP B'),
        ):
            select_box(box)
            daily_preview_response = client.post(reverse('wod-day-program-preview'), data={
                'target_date': target_date.isoformat(), 'template_id': template.pk,
                'workout_program_id': program.pk, 'mode': 'replace_empty',
            })
            assert daily_preview_response.status_code == 200
            daily_preview = daily_preview_response.json()
            assert [entry['title'] for entry in daily_preview['entries']] == [expected_daily]
            daily_confirm = client.post(reverse('wod-day-program-confirm'), data={
                'intent_id': daily_preview['intent_id'],
                'fingerprint': daily_preview['fingerprint'],
            })
            assert daily_confirm.status_code == 200, daily_confirm.content
            assert daily_confirm.json()['applied_count'] == 1

            plan = plan_a if box == test_tenant else plan_b
            weekly_payload = {
                'action': 'preview_projection', 'plan_id': plan.pk,
                'target_week_start': target_week_start.strftime('%d/%m/%Y'),
                'class_types': [ClassType.CROSS],
            }
            weekly_preview_response = client.post(reverse('workout-smart-paste'), data=weekly_payload)
            assert weekly_preview_response.status_code == 200
            projection_preview = weekly_preview_response.context['projection_preview']
            assert [entry['session_title'] for entry in projection_preview['entries']] == [expected_weekly]
            weekly_confirm = client.post(reverse('workout-smart-paste'), data={
                **weekly_payload,
                'action': 'create_projection',
                'idempotency_key': projection_preview['intent_id'],
                'preview_token': projection_preview['confirm_token'],
            })
            assert weekly_confirm.status_code == 200

        manager_client = Client()
        manager_client.force_login(manager)
        manager_session = manager_client.session
        manager_session['active_box_id'] = box_b.pk
        manager_session.save()
        manager_daily_preview_response = manager_client.post(reverse('wod-day-program-preview'), data={
            'target_date': manager_daily_date.isoformat(), 'template_id': template_b.pk,
            'workout_program_id': program_b.pk, 'mode': 'replace_empty',
        })
        assert manager_daily_preview_response.status_code == 200, manager_daily_preview_response.content
        manager_daily_preview = manager_daily_preview_response.json()
        assert [entry['title'] for entry in manager_daily_preview['entries']] == ['Aula diária Manager Box B']
        manager_daily_confirm = manager_client.post(reverse('wod-day-program-confirm'), data={
            'intent_id': manager_daily_preview['intent_id'],
            'fingerprint': manager_daily_preview['fingerprint'],
        })
        assert manager_daily_confirm.status_code == 200, manager_daily_confirm.content

        manager_weekly_payload = {
            'action': 'preview_projection', 'plan_id': manager_plan_b.pk,
            'target_week_start': manager_week_start.strftime('%d/%m/%Y'),
            'class_types': [ClassType.CROSS],
        }
        manager_weekly_preview_response = manager_client.post(
            reverse('workout-smart-paste'), data=manager_weekly_payload,
        )
        assert manager_weekly_preview_response.status_code == 200
        manager_projection = manager_weekly_preview_response.context['projection_preview']
        assert [entry['session_title'] for entry in manager_projection['entries']] == [
            'Aula semanal Manager Box B',
        ]
        manager_weekly_confirm = manager_client.post(reverse('workout-smart-paste'), data={
            **manager_weekly_payload,
            'action': 'create_projection',
            'idempotency_key': manager_projection['intent_id'],
            'preview_token': manager_projection['confirm_token'],
        })
        assert manager_weekly_confirm.status_code == 200

        receptionist_box_b_client = Client()
        receptionist_box_b_client.force_login(receptionist)
        receptionist_box_b_session = receptionist_box_b_client.session
        receptionist_box_b_session['active_box_id'] = box_b.pk
        receptionist_box_b_session.save()
        manager_daily_denied = receptionist_box_b_client.post(reverse('wod-day-program-preview'), data={
            'target_date': manager_daily_date.isoformat(), 'template_id': template_b.pk,
            'workout_program_id': program_b.pk, 'mode': 'replace_empty',
        })
        assert manager_daily_denied.status_code == 403
        manager_weekly_denied = receptionist_box_b_client.post(
            reverse('workout-smart-paste'), data=manager_weekly_payload,
        )
        assert manager_weekly_denied.status_code == 403
        manager_daily_confirm_denied = receptionist_box_b_client.post(
            reverse('wod-day-program-confirm'), data={
                'intent_id': manager_daily_preview['intent_id'],
                'fingerprint': manager_daily_preview['fingerprint'],
            },
        )
        assert manager_daily_confirm_denied.status_code == 403
        manager_weekly_confirm_denied = receptionist_box_b_client.post(
            reverse('workout-smart-paste'), data={
                **manager_weekly_payload,
                'action': 'create_projection',
                'idempotency_key': manager_projection['intent_id'],
                'preview_token': manager_projection['confirm_token'],
            },
        )
        assert manager_weekly_confirm_denied.status_code == 403

        receptionist_client = Client()
        receptionist_client.force_login(receptionist)
        receptionist_session = receptionist_client.session
        receptionist_session['active_box_id'] = test_tenant.pk
        receptionist_session.save()
        denied = receptionist_client.post(reverse('wod-day-program-preview'), data={
            'target_date': target_date.isoformat(), 'template_id': template_a.pk,
            'workout_program_id': program_a.pk, 'mode': 'replace_empty',
        })
        assert denied.status_code == 403

        with schema_context(test_tenant.schema_name):
            assert SessionWorkout.objects.filter(session=daily_session_a).count() == 1
            assert SessionWorkout.objects.filter(session=weekly_session_a).count() == 1
            assert ReplicationBatch.objects.filter(weekly_plan=plan_a).count() == 1
            assert SessionWorkout.objects.get(session=weekly_session_a).blocks.get().title == 'Bloco semanal A'
            assert not SessionWorkout.objects.filter(
                session__in=[manager_daily_session_a_decoy, manager_weekly_session_a_decoy],
            ).exists()
            assert not ReplicationBatch.objects.filter(weekly_plan=manager_plan_a_decoy).exists()
        with schema_context(other_schema):
            assert SessionWorkout.objects.filter(session=daily_session_b).count() == 1
            assert not SessionWorkout.objects.filter(session=other_coach_daily_session_b).exists()
            assert SessionWorkout.objects.filter(session=weekly_session_b).count() == 1
            assert SessionWorkout.objects.filter(session=manager_daily_session_b).count() == 1
            assert SessionWorkout.objects.filter(session=manager_weekly_session_b).count() == 1
            assert ReplicationBatch.objects.filter(weekly_plan=plan_b).count() == 1
            assert ReplicationBatch.objects.filter(weekly_plan=manager_plan_b).count() == 1
            assert SessionWorkout.objects.get(session=weekly_session_b).blocks.get().title == 'Bloco semanal B'
            assert SessionWorkout.objects.get(session=manager_daily_session_b).blocks.get().title == 'Bloco diário B'
            assert SessionWorkout.objects.get(session=manager_weekly_session_b).blocks.get().title == 'Bloco semanal Manager B'
    finally:
        with schema_context(get_public_schema_name()):
            Membership.objects.filter(
                user_id__in=[actor.pk, receptionist.pk, manager.pk], box_id__in=[test_tenant.pk, box_b.pk],
            ).delete()
            box_b.delete()
        with connection.cursor() as cursor:
            cursor.execute(f'DROP SCHEMA IF EXISTS "{other_schema}" CASCADE')
