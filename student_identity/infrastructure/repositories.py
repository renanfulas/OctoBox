from __future__ import annotations

from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from student_identity.application.results import StudentBoxInviteLinkRecord, StudentIdentityRecord, StudentInvitationRecord
from student_identity.models import (
    StudentAppInvitation,
    StudentBoxInviteLink,
    StudentBoxMembership,
    StudentBoxMembershipStatus,
    StudentIdentity,
    StudentIdentityStatus,
    StudentInvitationType,
    StudentOnboardingJourney,
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
        primary_box_root_slug=identity.primary_box_root_slug,
        status=identity.status,
    )


def _invitation_record(invitation: StudentAppInvitation) -> StudentInvitationRecord:
    return StudentInvitationRecord(
        id=invitation.id,
        token=str(invitation.token),
        student_id=invitation.student_id,
        student_name=invitation.student.full_name,
        invite_type=invitation.invite_type,
        onboarding_journey=invitation.onboarding_journey,
        invited_email=invitation.invited_email,
        box_root_slug=invitation.box_root_slug,
        expires_at_iso=invitation.expires_at.isoformat(),
        accepted_at_iso=invitation.accepted_at.isoformat() if invitation.accepted_at else '',
    )


def _box_invite_link_record(link: StudentBoxInviteLink) -> StudentBoxInviteLinkRecord:
    return StudentBoxInviteLinkRecord(
        id=link.id,
        token=str(link.token),
        box_root_slug=link.box_root_slug,
        expires_at_iso=link.expires_at.isoformat(),
        max_uses=link.max_uses,
        use_count=link.use_count,
        paused_at_iso=link.paused_at.isoformat() if link.paused_at else '',
        revoked_at_iso=link.revoked_at.isoformat() if link.revoked_at else '',
    )


class DjangoStudentIdentityRepository:
    def _ensure_membership_status(
        self,
        *,
        identity: StudentIdentity,
        student: Student,
        box_root_slug: str,
        invitation=None,
        actor_id: int | None = None,
        status: str = StudentBoxMembershipStatus.ACTIVE,
    ) -> StudentBoxMembership:
        membership, _ = StudentBoxMembership.objects.get_or_create(
            identity=identity,
            box_root_slug=box_root_slug,
            defaults={
                'student': student,
                'status': status,
                'created_from_invite': invitation,
                'approved_by_id': actor_id,
            },
        )
        membership.student = student
        if invitation is not None and membership.created_from_invite_id is None:
            membership.created_from_invite = invitation
        if status == StudentBoxMembershipStatus.ACTIVE:
            membership.mark_active()
            if actor_id is not None and membership.approved_by_id is None:
                membership.approved_by_id = actor_id
        else:
            membership.status = status
        membership.save()
        return membership

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

    def find_box_invite_link_by_token(self, token: str):
        return StudentBoxInviteLink.objects.filter(token=token).first()

    def find_student_candidates_by_email(self, *, email: str):
        return list(Student.objects.filter(email__iexact=(email or '').strip()).order_by('id'))

    def count_open_box_invites_since(self, *, box_root_slug: str, since):
        return StudentAppInvitation.objects.filter(
            box_root_slug=box_root_slug,
            invite_type=StudentInvitationType.OPEN_BOX,
            created_at__gte=since,
        ).count()

    @transaction.atomic
    def create_invitation(
        self,
        *,
        student,
        invited_email: str,
        box_root_slug: str,
        invite_type: str,
        onboarding_journey: str,
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
            invite_type=invite_type,
            onboarding_journey=onboarding_journey or StudentOnboardingJourney.REGISTERED_STUDENT_INVITE,
            invited_email=(invited_email or '').strip().lower(),
            expires_at=now + timedelta(days=max(1, expires_in_days)),
            created_by_id=actor_id,
        )
        invitation = StudentAppInvitation.objects.select_related('student').get(pk=invitation.pk)
        return _invitation_record(invitation)

    @transaction.atomic
    def create_or_replace_box_invite_link(
        self,
        *,
        box_root_slug: str,
        expires_in_days: int,
        max_uses: int,
        actor_id: int | None,
    ) -> StudentBoxInviteLinkRecord:
        now = timezone.now()
        (
            StudentBoxInviteLink.objects
            .filter(
                box_root_slug=box_root_slug,
                paused_at__isnull=True,
                revoked_at__isnull=True,
                expires_at__gt=now,
            )
            .update(revoked_at=now)
        )
        link = StudentBoxInviteLink.objects.create(
            box_root_slug=box_root_slug,
            expires_at=now + timedelta(days=max(1, expires_in_days)),
            max_uses=max(1, max_uses),
            created_by_id=actor_id,
        )
        return _box_invite_link_record(link)

    @transaction.atomic
    def record_box_invite_acceptance(self, link: StudentBoxInviteLink) -> StudentBoxInviteLink:
        StudentBoxInviteLink.objects.filter(pk=link.pk).update(
            use_count=link.use_count + 1,
            updated_at=timezone.now(),
        )
        return StudentBoxInviteLink.objects.get(pk=link.pk)

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
                primary_box_root_slug=box_root_slug,
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
            if not identity.primary_box_root_slug:
                identity.primary_box_root_slug = box_root_slug
            if invitation is not None and identity.invited_at is None:
                identity.invited_at = timezone.now()

        identity.mark_authenticated()
        identity.save()
        membership_status = StudentBoxMembershipStatus.ACTIVE
        if invitation is not None and invitation.invite_type == StudentInvitationType.OPEN_BOX:
            membership_status = StudentBoxMembershipStatus.PENDING_APPROVAL

        self._ensure_membership_status(
            identity=identity,
            student=student,
            box_root_slug=box_root_slug,
            invitation=invitation,
            status=membership_status,
        )

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
        self._ensure_membership_status(
            identity=identity,
            student=identity.student,
            box_root_slug=identity.box_root_slug,
            status=StudentBoxMembershipStatus.ACTIVE,
        )
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
        previous_box_root_slug = identity.box_root_slug
        previous_membership = (
            StudentBoxMembership.objects
            .filter(identity=identity, box_root_slug=previous_box_root_slug)
            .first()
        )
        if previous_membership is None:
            previous_membership = StudentBoxMembership.objects.create(
                identity=identity,
                student=identity.student,
                box_root_slug=previous_box_root_slug,
                status=StudentBoxMembershipStatus.INACTIVE,
                revoked_reason=reason,
                revoked_at=timezone.now(),
            )
        else:
            previous_membership.status = StudentBoxMembershipStatus.INACTIVE
            previous_membership.revoked_reason = reason
            previous_membership.revoked_at = timezone.now()
            previous_membership.save(update_fields=['status', 'revoked_reason', 'revoked_at', 'updated_at'])
        identity.box_root_slug = to_box_root_slug
        identity.primary_box_root_slug = to_box_root_slug
        identity.last_authenticated_at = timezone.now()
        identity.save(update_fields=['box_root_slug', 'primary_box_root_slug', 'last_authenticated_at'])
        self._ensure_membership_status(
            identity=identity,
            student=identity.student,
            box_root_slug=to_box_root_slug,
            actor_id=actor_id,
            status=StudentBoxMembershipStatus.ACTIVE,
        )
        return _identity_record(identity), transfer.id
