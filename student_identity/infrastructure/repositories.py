from __future__ import annotations

from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from student_identity.application.results import StudentIdentityRecord, StudentInvitationRecord
from student_identity.models import (
    StudentAppInvitation,
    StudentIdentity,
    StudentIdentityStatus,
    StudentTransfer,
    StudentTransferStatus,
)
from students.models import Student


def _identity_record(identity: StudentIdentity) -> StudentIdentityRecord:
    return StudentIdentityRecord(
        id=identity.id,
        student_id=identity.student_id,
        student_name=identity.student.full_name,
        email=identity.email,
        provider=identity.provider,
        box_root_slug=identity.box_root_slug,
        status=identity.status,
    )


def _invitation_record(invitation: StudentAppInvitation) -> StudentInvitationRecord:
    return StudentInvitationRecord(
        id=invitation.id,
        token=str(invitation.token),
        student_id=invitation.student_id,
        student_name=invitation.student.full_name,
        invited_email=invitation.invited_email,
        box_root_slug=invitation.box_root_slug,
        expires_at_iso=invitation.expires_at.isoformat(),
        accepted_at_iso=invitation.accepted_at.isoformat() if invitation.accepted_at else '',
    )


class DjangoStudentIdentityRepository:
    def find_student_by_id(self, student_id: int):
        return Student.objects.filter(pk=student_id).first()

    def find_identity_by_id(self, identity_id: int):
        return StudentIdentity.objects.select_related('student').filter(pk=identity_id).first()

    def find_live_by_student_id(self, student_id: int):
        return (
            StudentIdentity.objects.select_related('student')
            .filter(student_id=student_id, status__in=[StudentIdentityStatus.PENDING, StudentIdentityStatus.ACTIVE])
            .first()
        )

    def find_live_by_email_and_box(self, *, email: str, box_root_slug: str):
        return (
            StudentIdentity.objects.select_related('student')
            .filter(
                email__iexact=(email or '').strip(),
                box_root_slug=box_root_slug,
                status__in=[StudentIdentityStatus.PENDING, StudentIdentityStatus.ACTIVE],
            )
            .first()
        )

    def find_by_provider_subject(self, *, provider_subject: str):
        return (
            StudentIdentity.objects.select_related('student')
            .filter(provider_subject=provider_subject)
            .first()
        )

    def find_invitation_by_token(self, token: str):
        return (
            StudentAppInvitation.objects.select_related('student')
            .filter(token=token)
            .first()
        )

    def find_student_candidates_by_email(self, *, email: str):
        return list(Student.objects.filter(email__iexact=(email or '').strip()).order_by('id'))

    @transaction.atomic
    def create_invitation(
        self,
        *,
        student,
        invited_email: str,
        box_root_slug: str,
        expires_in_days: int,
        actor_id: int | None,
    ) -> StudentInvitationRecord:
        now = timezone.now()
        (
            StudentAppInvitation.objects
            .filter(
                student=student,
                box_root_slug=box_root_slug,
                accepted_at__isnull=True,
                expires_at__gt=now,
            )
            .update(expires_at=now)
        )
        invitation = StudentAppInvitation.objects.create(
            student=student,
            box_root_slug=box_root_slug,
            invited_email=(invited_email or '').strip().lower(),
            expires_at=now + timedelta(days=max(1, expires_in_days)),
            created_by_id=actor_id,
        )
        invitation = StudentAppInvitation.objects.select_related('student').get(pk=invitation.pk)
        return _invitation_record(invitation)

    @transaction.atomic
    def save_identity(
        self,
        *,
        student,
        box_root_slug: str,
        provider: str,
        provider_subject: str,
        email: str,
        invitation=None,
    ) -> StudentIdentityRecord:
        identity = self.find_live_by_student_id(student.id)
        if identity is None:
            identity = StudentIdentity(
                student=student,
                box_root_slug=box_root_slug,
                provider=provider,
                provider_subject=provider_subject,
                email=(email or '').strip().lower(),
                invited_at=timezone.now() if invitation is not None else None,
            )
        else:
            identity.box_root_slug = box_root_slug
            identity.provider = provider
            identity.provider_subject = provider_subject
            identity.email = (email or '').strip().lower()
            if invitation is not None and identity.invited_at is None:
                identity.invited_at = timezone.now()

        identity.mark_authenticated()
        identity.save()

        if invitation is not None and invitation.accepted_at is None:
            invitation.accepted_at = timezone.now()
            invitation.save(update_fields=['accepted_at'])

        if not student.email:
            student.email = identity.email
            student.save(update_fields=['email'])

        return _identity_record(identity)

    @transaction.atomic
    def mark_authenticated(self, identity) -> StudentIdentityRecord:
        identity.mark_authenticated()
        identity.save(update_fields=['status', 'activated_at', 'last_authenticated_at'])
        return _identity_record(identity)

    @transaction.atomic
    def transfer_identity(
        self,
        *,
        identity,
        to_box_root_slug: str,
        actor_id: int | None,
        reason: str,
    ) -> tuple[StudentIdentityRecord, int]:
        transfer = StudentTransfer.objects.create(
            identity=identity,
            student=identity.student,
            from_box_root_slug=identity.box_root_slug,
            to_box_root_slug=to_box_root_slug,
            status=StudentTransferStatus.COMPLETED,
            requested_by_id=actor_id,
            completed_at=timezone.now(),
            reason=reason,
            audit_summary=f'Transferencia concluida de {identity.box_root_slug} para {to_box_root_slug}.',
        )
        identity.box_root_slug = to_box_root_slug
        identity.last_authenticated_at = timezone.now()
        identity.save(update_fields=['box_root_slug', 'last_authenticated_at'])
        return _identity_record(identity), transfer.id
