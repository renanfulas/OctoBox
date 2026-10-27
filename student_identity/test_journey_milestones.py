import pytest
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from django.db import close_old_connections, connection
from django_tenants.utils import schema_context
from django.utils import timezone



@pytest.mark.django_db
def test_cohort_start_and_activation_are_durable_and_idempotent(test_tenant):
    from student_app.models import StudentJourneyMilestone
    from student_identity.funnel_events import record_student_onboarding_event

    metadata = {
        'box_root_slug': test_tenant.schema_name,
        'invitation_id': 8801,
    }
    for _ in range(2):
        record_student_onboarding_event(
            journey='imported_lead_invite',
            event='invite_created',
            target_model='student_identity.StudentAppInvitation',
            target_id='8801',
            metadata=metadata,
        )
    record_student_onboarding_event(
        journey='imported_lead_invite',
        event='app_entry_completed',
        target_model='student_identity.StudentIdentity',
        target_id='401',
        metadata={
            **metadata,
            'identity_id': 401,
        },
    )

    assert StudentJourneyMilestone.objects.count() == 2
    start = StudentJourneyMilestone.objects.get(milestone='invite_created')
    activation = StudentJourneyMilestone.objects.get(milestone='app_entry_completed')
    assert start.idempotency_key
    assert start.cohort_kind == activation.cohort_kind == 'invitation'
    assert start.cohort_key == activation.cohort_key == '8801'
    assert activation.identity_id == 401
    assert activation.contract_version == 1


@pytest.mark.django_db
def test_public_callback_routes_cohort_fact_and_audit_to_resolved_tenant(test_tenant):
    from auditing.models import AuditEvent
    from student_app.models import StudentJourneyMilestone
    from student_identity.funnel_events import record_student_onboarding_event

    with schema_context('public'):
        assert connection.schema_name == 'public'
        record_student_onboarding_event(
            journey='mass_box_invite',
            event='link_created',
            target_model='student_identity.StudentBoxInviteLink',
            target_id='8802',
            metadata={
                'box_root_slug': test_tenant.schema_name,
                'box_invite_link_id': 8802,
            },
        )
        record_student_onboarding_event(
            journey='mass_box_invite',
            event='link_created',
            target_model='student_identity.StudentBoxInviteLink',
            target_id='8806',
            metadata={
                'box_root_slug': test_tenant.slug,
                'box_invite_link_id': 8806,
            },
        )
        assert connection.schema_name == 'public'

    assert connection.schema_name == test_tenant.schema_name
    milestone = StudentJourneyMilestone.objects.get(milestone='link_created', cohort_key='8802')
    assert milestone.cohort_kind == 'invite_link'
    assert milestone.cohort_key == '8802'
    assert StudentJourneyMilestone.objects.filter(
        milestone='link_created', cohort_key='8806',
    ).exists()
    assert AuditEvent.objects.filter(action='student_onboarding.mass_box_invite.link_created').exists()


@pytest.mark.django_db
def test_tenant_milestone_writer_accepts_own_legacy_box_slug_only(test_tenant):
    from student_app.models import StudentJourneyMilestone
    from student_identity.funnel_events import record_student_onboarding_event

    with schema_context(test_tenant.schema_name):
        record_student_onboarding_event(
            journey='mass_box_invite',
            event='link_created',
            target_model='student_identity.StudentBoxInviteLink',
            target_id='8804',
            metadata={
                'box_root_slug': test_tenant.slug,
                'box_invite_link_id': 8804,
            },
        )
        assert StudentJourneyMilestone.objects.filter(
            milestone='link_created', cohort_key='8804',
        ).exists()

        with pytest.raises(RuntimeError, match='tenant divergente'):
            record_student_onboarding_event(
                journey='mass_box_invite',
                event='link_created',
                target_model='student_identity.StudentBoxInviteLink',
                target_id='8805',
                metadata={
                    'box_root_slug': 'another-box-slug',
                    'box_invite_link_id': 8805,
                },
            )


@pytest.mark.django_db(transaction=True)
@pytest.mark.requires_postgres
def test_concurrent_retries_create_one_cohort_milestone(test_tenant):
    from student_app.models import StudentJourneyMilestone
    from student_identity.funnel_events import record_student_onboarding_event

    barrier = Barrier(2)
    metadata = {'box_root_slug': test_tenant.schema_name, 'invitation_id': 8803}

    def record_from_independent_connection():
        close_old_connections()
        try:
            barrier.wait(timeout=5)
            with schema_context(test_tenant.schema_name):
                return record_student_onboarding_event(
                    journey='imported_lead_invite',
                    event='invite_created',
                    target_model='student_identity.StudentAppInvitation',
                    target_id='8803',
                    metadata=metadata,
                )
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _index: record_from_independent_connection(), range(2)))

    assert results[0] is not None and results[1] is not None
    with schema_context(test_tenant.schema_name):
        milestone = StudentJourneyMilestone.objects.get(milestone='invite_created')
        assert StudentJourneyMilestone.objects.filter(
            idempotency_key=milestone.idempotency_key,
        ).count() == 1


@pytest.mark.django_db
def test_cohort_query_joins_invitation_activation_to_authenticated_student_activity(test_tenant):
    from student_app.models import (
        StudentAppActivityKind,
        StudentJourneyMilestone,
    )
    from student_app.application.activity import record_student_app_activity
    from student_identity.models import StudentIdentity
    from student_identity.queries.activation_cohorts import build_activation_cohort_reports
    from students.models import Student

    now = timezone.now()
    start_at = now - timedelta(days=20)
    activation_at = start_at + timedelta(days=3)
    return_at = start_at + timedelta(days=9)
    identity = StudentIdentity.objects.create(
        provider='google',
        provider_subject='cohort-query-provider-subject',
        email='cohort-query@example.test',
        student_name='Cohort Student',
        box_root_slug=test_tenant.schema_name,
    )
    student = Student.objects.create(
        full_name='Cohort Student',
        phone='5511987654321',
        email='cohort-query@example.test',
        identity=identity,
    )
    StudentJourneyMilestone.objects.create(
        idempotency_key='a' * 64,
        journey='imported_lead_invite',
        milestone='invite_created',
        subject_kind='invitation',
        subject_key='9911',
        cohort_kind='invitation',
        cohort_key='9911',
        occurred_at=start_at,
        timezone_name='America/Sao_Paulo',
    )
    StudentJourneyMilestone.objects.create(
        idempotency_key='b' * 64,
        journey='imported_lead_invite',
        milestone='app_entry_completed',
        subject_kind='identity',
        subject_key=str(identity.id),
        cohort_kind='invitation',
        cohort_key='9911',
        identity_id=identity.id,
        occurred_at=activation_at,
        timezone_name='America/Sao_Paulo',
    )
    from unittest.mock import patch
    with patch('django.utils.timezone.now', return_value=return_at):
            record_student_app_activity(
                student=student,
                kind=StudentAppActivityKind.WOD_VIEWED,
                identity_id=identity.id,
            )
            record_student_app_activity(
                student=student,
                kind=StudentAppActivityKind.WOD_VIEWED,
                identity_id=identity.id,
            )
            record_student_app_activity(
                student=student,
                kind=StudentAppActivityKind.ATTENDANCE_CONFIRMED,
                identity_id=identity.id,
            )

    assert StudentJourneyMilestone.objects.filter(milestone='authenticated_return').count() == 1

    report = next(
        item for item in build_activation_cohort_reports(now=now)
        if item['journey'] == 'imported_lead_invite'
    )

    assert report['eligible_count'] == 1
    assert report['activated_count'] == 1
    assert report['retained_count'] == 1
    assert report['activation_rate'] == 100.0
    assert report['retention_rate'] == 100.0


@pytest.mark.django_db
def test_first_staff_checkin_is_tenant_local_and_idempotent(test_tenant):
    from operations.facade.workspace import run_apply_attendance_action
    from operations.models import Attendance, AttendanceStatus, ClassSession
    from student_app.models import StudentJourneyMilestone
    from students.models import Student

    student = Student.objects.create(full_name='Check-in cohort student', phone='5511999900123')
    first_session = ClassSession.objects.create(
        title='Check-in cohort A',
        scheduled_at=timezone.now(),
        duration_minutes=60,
        capacity=10,
    )
    second_session = ClassSession.objects.create(
        title='Check-in cohort B',
        scheduled_at=timezone.now() + timedelta(days=1),
        duration_minutes=60,
        capacity=10,
    )
    third_session = ClassSession.objects.create(
        title='Check-in cohort C',
        scheduled_at=timezone.now() + timedelta(days=2),
        duration_minutes=60,
        capacity=10,
    )
    first_attendance = Attendance.objects.create(
        student=student,
        session=first_session,
        status=AttendanceStatus.BOOKED,
    )
    later_attendance = Attendance.objects.create(
        student=student,
        session=second_session,
        status=AttendanceStatus.BOOKED,
    )
    absent_student = Student.objects.create(full_name='Absent cohort student', phone='5511999900457')
    absent_attendance = Attendance.objects.create(
        student=absent_student,
        session=third_session,
        status=AttendanceStatus.BOOKED,
    )
    checkout_student = Student.objects.create(full_name='Checkout cohort student', phone='5511999900458')
    checkout_attendance = Attendance.objects.create(
        student=checkout_student,
        session=third_session,
        status=AttendanceStatus.BOOKED,
    )

    run_apply_attendance_action(actor_id=None, attendance_id=first_attendance.pk, action='check-in')
    run_apply_attendance_action(actor_id=None, attendance_id=later_attendance.pk, action='check-in')
    run_apply_attendance_action(actor_id=None, attendance_id=absent_attendance.pk, action='absent')
    run_apply_attendance_action(actor_id=None, attendance_id=checkout_attendance.pk, action='check-out')

    milestone = StudentJourneyMilestone.objects.get(milestone='first_checkin', subject_key=str(student.pk))
    checkout_milestone = StudentJourneyMilestone.objects.get(
        milestone='first_checkin', subject_key=str(checkout_student.pk)
    )
    assert StudentJourneyMilestone.objects.filter(milestone='first_checkin').count() == 2
    assert milestone.journey == 'attendance'
    assert milestone.subject_kind == 'student'
    assert milestone.subject_key == str(student.pk)
    assert milestone.cohort_kind == 'box_student'
    assert milestone.cohort_key == str(student.pk)
    assert milestone.identity_id is None
    assert milestone.contract_version == 1
    assert checkout_milestone.occurred_at == Attendance.objects.get(pk=checkout_attendance.pk).check_in_at
    assert not StudentJourneyMilestone.objects.filter(
        milestone='first_checkin', subject_key=str(absent_student.pk)
    ).exists()
    assert Attendance.objects.get(pk=first_attendance.pk).status == AttendanceStatus.CHECKED_IN
    assert Attendance.objects.get(pk=later_attendance.pk).status == AttendanceStatus.CHECKED_IN
    assert Attendance.objects.get(pk=checkout_attendance.pk).status == AttendanceStatus.CHECKED_OUT


@pytest.mark.django_db
def test_checkin_milestone_failure_rolls_back_staff_attendance_mutation(test_tenant):
    from operations.facade.workspace import run_apply_attendance_action
    from operations.models import Attendance, AttendanceStatus, ClassSession
    from students.models import Student

    student = Student.objects.create(full_name='Rollback check-in student', phone='5511999900456')
    session = ClassSession.objects.create(
        title='Check-in rollback',
        scheduled_at=timezone.now(),
        duration_minutes=60,
        capacity=10,
    )
    attendance = Attendance.objects.create(
        student=student,
        session=session,
        status=AttendanceStatus.BOOKED,
    )

    from unittest.mock import patch

    with patch(
        'student_identity.cohort_milestones.record_student_first_checkin',
        side_effect=RuntimeError('milestone write failed'),
    ):
        with pytest.raises(RuntimeError, match='milestone write failed'):
            run_apply_attendance_action(actor_id=None, attendance_id=attendance.pk, action='check-in')

    attendance.refresh_from_db()
    assert attendance.status == AttendanceStatus.BOOKED
    assert attendance.check_in_at is None
