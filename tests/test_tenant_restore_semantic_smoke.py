"""Regression tests for shared/tenant references checked after selective restore."""

from io import StringIO
from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from django.apps import apps
from django.core.management import call_command
from django.core.management.base import CommandError
from django_tenants.utils import get_public_schema_name, schema_context
from django.utils import timezone


@pytest.mark.django_db
def test_restore_semantic_smoke_accepts_valid_links_and_rejects_cross_box_drift(test_tenant):
    if test_tenant is None:
        pytest.skip('requires PostgreSQL and django-tenants')

    from control.models import Box, Membership
    from control.services import _bootstrap_roles, _seed_plans
    from finance.models import Payment
    from integrations.stripe.models import StripePaymentRef
    from operations.models import WorkoutApprovalPolicySetting
    from student_app.models import StudentProfileChangeRequest
    from student_identity.models import (
        StudentAppInvitation,
        StudentBoxInviteLink,
        StudentBoxMembership,
        StudentConsent,
        StudentIdentity,
        StudentPushSubscription,
        StudentTransfer,
    )

    box = test_tenant
    owner = box.owner_user
    Membership.objects.get_or_create(
        user=owner,
        box=box,
        defaults={'role': Membership.Role.OWNER, 'is_primary_box': True},
    )
    _bootstrap_roles(box)
    _seed_plans(box)

    suffix = uuid4().hex
    Student = apps.get_model('boxcore', 'Student')
    with schema_context(box.schema_name):
        student = Student.objects.create(
            full_name=f'Restore semantic {suffix}',
            phone=f'555{int(suffix[:8], 16):08d}',
        )
        identity = StudentIdentity.objects.create(
            student_id=student.pk,
            student_name=student.full_name,
            box=box,
            box_root_slug=box.schema_name,
            primary_box=box,
            primary_box_root_slug=box.schema_name,
            provider='google',
            provider_subject=f'restore-semantic-{suffix}',
            email=f'restore-semantic-{suffix}@example.test',
        )
        Student.objects.filter(pk=student.pk).update(identity_id=identity.pk)
        membership = StudentBoxMembership.objects.create(
            identity=identity,
            student_id=student.pk,
            box=box,
            box_root_slug=box.schema_name,
        )
        profile_request = StudentProfileChangeRequest.objects.create(
            student_id=student.pk,
            identity_id=identity.pk,
            requested_payload={'full_name': 'Updated name'},
        )
        approval_policy = WorkoutApprovalPolicySetting.objects.create(
            box_id=box.pk,
            approval_policy='strict',
        )
        payment = Payment.objects.create(
            student=student,
            due_date=timezone.localdate(),
            amount=Decimal('100.00'),
            stripe_payment_intent_id=f'pi_restore_{suffix}',
        )
        expires_at = timezone.now() + timedelta(days=3)
        consent = StudentConsent.objects.create(
            identity=identity,
            box=box,
            box_root_slug=box.schema_name,
            document_kind='waiver',
            version='restore-smoke-v1',
        )
        invitation = StudentAppInvitation.objects.create(
            student_id=student.pk,
            student_name=student.full_name,
            box=box,
            box_root_slug=box.schema_name,
            invited_email=f'restore-invite-{suffix}@example.test',
            expires_at=expires_at,
        )
        invite_link = StudentBoxInviteLink.objects.create(
            box=box,
            box_root_slug=box.schema_name,
            expires_at=expires_at,
        )
        push_subscription = StudentPushSubscription.objects.create(
            identity=identity,
            box=box,
            box_root_slug=box.schema_name,
            endpoint=f'https://push.example.test/{suffix}',
        )
    payment_ref = StripePaymentRef.objects.create(
        payment_intent_id=f'pi_restore_{suffix}',
        session_id=f'cs_restore_{suffix}',
        box_schema=box.schema_name,
        payment_id=payment.pk,
    )

    output = StringIO()
    try:
        call_command(
            'smoke_test_tenant',
            slug=box.slug,
            schema_only=True,
            restore_semantic=True,
            verbose=True,
            stdout=output,
        )
    except CommandError as exc:
        pytest.fail(f'{exc}\n{output.getvalue()}')
    assert 'C5S:' in output.getvalue()
    assert 'Student/identity e 1 StudentBoxMembership e 4 âncoras shared, 0 StudentTransfer' in output.getvalue()
    assert '1 StripePaymentRef' in output.getvalue()
    assert '1 StudentProfileChangeRequest e 0 StudentJourneyMilestone e 1 WorkoutApprovalPolicySetting coerentes' in output.getvalue()

    WorkoutApprovalPolicySetting.objects.filter(pk=approval_policy.pk).update(box_id=box.pk + 1)
    mismatched_approval_policy_output = StringIO()
    with pytest.raises(CommandError):
        call_command(
            'smoke_test_tenant',
            slug=box.slug,
            schema_only=True,
            restore_semantic=True,
            verbose=True,
            stdout=mismatched_approval_policy_output,
        )
    assert 'WorkoutApprovalPolicySetting' in mismatched_approval_policy_output.getvalue()
    assert 'box_id aponta para' in mismatched_approval_policy_output.getvalue()
    WorkoutApprovalPolicySetting.objects.filter(pk=approval_policy.pk).update(box_id=box.pk)

    StripePaymentRef.objects.filter(pk=payment_ref.pk).update(payment_id=payment.pk + 1)
    missing_payment_output = StringIO()
    with pytest.raises(CommandError):
        call_command(
            'smoke_test_tenant',
            slug=box.slug,
            schema_only=True,
            restore_semantic=True,
            verbose=True,
            stdout=missing_payment_output,
        )
    assert 'StripePaymentRef' in missing_payment_output.getvalue()
    assert 'Payment' in missing_payment_output.getvalue()
    assert 'ausente no tenant' in missing_payment_output.getvalue()
    StripePaymentRef.objects.filter(pk=payment_ref.pk).update(payment_id=payment.pk)

    StripePaymentRef.objects.filter(pk=payment_ref.pk).update(box_schema=box.slug)
    noncanonical_payment_output = StringIO()
    with pytest.raises(CommandError):
        call_command(
            'smoke_test_tenant',
            slug=box.slug,
            schema_only=True,
            restore_semantic=True,
            verbose=True,
            stdout=noncanonical_payment_output,
        )
    assert 'box_schema não canônico' in noncanonical_payment_output.getvalue()
    StripePaymentRef.objects.filter(pk=payment_ref.pk).update(box_schema=box.schema_name)

    # The active resolver accepts a legacy root value as either schema_name or
    # Box.slug when the newer Box FK has not been backfilled yet.
    StudentBoxMembership.objects.filter(pk=membership.pk).update(box_id=None, box_root_slug=box.slug)
    StudentIdentity.objects.filter(pk=identity.pk).update(
        box_id=None,
        box_root_slug=box.slug,
        primary_box_id=None,
        primary_box_root_slug=box.slug,
    )
    legacy_output = StringIO()
    try:
        call_command(
            'smoke_test_tenant',
            slug=box.slug,
            schema_only=True,
            restore_semantic=True,
            verbose=True,
            stdout=legacy_output,
        )
    except CommandError as exc:
        pytest.fail(f'{exc}\n{legacy_output.getvalue()}')
    assert '1 StudentBoxMembership' in legacy_output.getvalue()
    StudentBoxMembership.objects.filter(pk=membership.pk).update(box_id=box.pk, box_root_slug=box.schema_name)
    StudentIdentity.objects.filter(pk=identity.pk).update(
        box_id=box.pk,
        box_root_slug=box.schema_name,
        primary_box_id=box.pk,
        primary_box_root_slug=box.schema_name,
    )

    StudentBoxMembership.objects.filter(pk=membership.pk).update(box_root_slug='box_wrong')
    mismatch_output = StringIO()
    with pytest.raises(CommandError):
        call_command(
            'smoke_test_tenant',
            slug=box.slug,
            schema_only=True,
            restore_semantic=True,
            verbose=True,
            stdout=mismatch_output,
        )
    assert 'box_root_slug divergente' in mismatch_output.getvalue()
    StudentBoxMembership.objects.filter(pk=membership.pk).update(box_root_slug=box.schema_name)

    with schema_context(get_public_schema_name()):
        other_box = Box.objects.create(
            slug=f'restore-semantic-{suffix[:12]}',
            schema_name=f'box_restore_semantic_{suffix[:12]}',
            display_name='Synthetic semantic neighbor',
            status=Box.Status.ACTIVE,
            owner_user=owner,
        )
    other_identity = StudentIdentity.objects.create(
        student_id=student.pk,
        student_name='Synthetic neighbor identity',
        box=other_box,
        box_root_slug=other_box.schema_name,
        primary_box=other_box,
        primary_box_root_slug=other_box.schema_name,
        provider='google',
        provider_subject=f'restore-semantic-neighbor-{suffix}',
        email=f'restore-semantic-neighbor-{suffix}@example.test',
    )
    StripePaymentRef.objects.filter(pk=payment_ref.pk).update(
        box_schema=other_box.schema_name,
        payment_id=payment.pk + 1,
    )
    cross_box_payment_output = StringIO()
    with pytest.raises(CommandError):
        call_command(
            'smoke_test_tenant',
            slug=box.slug,
            schema_only=True,
            restore_semantic=True,
            verbose=True,
            stdout=cross_box_payment_output,
        )
    assert 'StripePaymentRef' in cross_box_payment_output.getvalue()
    assert 'Payment intent resolve para outro Box/pagamento' in cross_box_payment_output.getvalue()
    StripePaymentRef.objects.filter(pk=payment_ref.pk).update(
        box_schema=box.schema_name,
        payment_id=payment.pk,
    )

    StudentAppInvitation.objects.filter(pk=invitation.pk).update(box_root_slug=other_box.schema_name)
    conflicting_anchor_output = StringIO()
    with pytest.raises(CommandError):
        call_command(
            'smoke_test_tenant',
            slug=box.slug,
            schema_only=True,
            restore_semantic=True,
            verbose=True,
            stdout=conflicting_anchor_output,
        )
    assert 'StudentAppInvitation' in conflicting_anchor_output.getvalue()
    assert 'box_root_slug divergente' in conflicting_anchor_output.getvalue()
    StudentAppInvitation.objects.filter(pk=invitation.pk).update(box_root_slug=box.schema_name)

    transfer = StudentTransfer.objects.create(
        identity=identity,
        student_id=student.pk,
        from_box=box,
        from_box_root_slug=box.schema_name,
        to_box=other_box,
        to_box_root_slug=other_box.schema_name,
    )
    valid_transfer_output = StringIO()
    try:
        call_command(
            'smoke_test_tenant',
            slug=box.slug,
            schema_only=True,
            restore_semantic=True,
            verbose=True,
            stdout=valid_transfer_output,
        )
    except CommandError as exc:
        pytest.fail(f'{exc}\n{valid_transfer_output.getvalue()}')
    assert '1 StudentTransfer' in valid_transfer_output.getvalue()
    StudentTransfer.objects.filter(pk=transfer.pk).update(from_box_root_slug=other_box.schema_name)
    conflicting_transfer_output = StringIO()
    with pytest.raises(CommandError):
        call_command(
            'smoke_test_tenant',
            slug=box.slug,
            schema_only=True,
            restore_semantic=True,
            verbose=True,
            stdout=conflicting_transfer_output,
        )
    assert 'StudentTransfer' in conflicting_transfer_output.getvalue()
    assert 'de origem divergente' in conflicting_transfer_output.getvalue()
    StudentTransfer.objects.filter(pk=transfer.pk).update(from_box_root_slug=box.schema_name)

    StudentProfileChangeRequest.objects.filter(pk=profile_request.pk).update(identity_id=other_identity.pk)
    cross_box_request_output = StringIO()
    with pytest.raises(CommandError):
        call_command(
            'smoke_test_tenant',
            slug=box.slug,
            schema_only=True,
            restore_semantic=True,
            verbose=True,
            stdout=cross_box_request_output,
        )
    assert 'StudentProfileChangeRequest' in cross_box_request_output.getvalue()
    assert 'pertence a outro Box' in cross_box_request_output.getvalue()
    StudentProfileChangeRequest.objects.filter(pk=profile_request.pk).update(identity_id=identity.pk)

    with schema_context(box.schema_name):
        Student.objects.filter(pk=student.pk).update(identity_id=other_identity.pk)
    cross_box_output = StringIO()
    with pytest.raises(CommandError):
        call_command(
            'smoke_test_tenant',
            slug=box.slug,
            schema_only=True,
            restore_semantic=True,
            verbose=True,
            stdout=cross_box_output,
        )
    assert 'pertence a outro Box' in cross_box_output.getvalue()

    StudentIdentity.objects.filter(pk=identity.pk).update(student_id=student.pk + 100)
    with schema_context(box.schema_name):
        Student.objects.filter(pk=student.pk).update(identity_id=None)
    weak_link_output = StringIO()
    with pytest.raises(CommandError):
        call_command(
            'smoke_test_tenant',
            slug=box.slug,
            schema_only=True,
            restore_semantic=True,
            verbose=True,
            stdout=weak_link_output,
        )
    assert 'aponta para Student' in weak_link_output.getvalue()
