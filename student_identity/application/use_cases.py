from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from .commands import (
    AuthenticateStudentWithProviderCommand,
    CreateStudentBoxInviteLinkCommand,
    CreateStudentInvitationCommand,
    TransferStudentToBoxCommand,
)
from .ports import StudentIdentityRepositoryPort
from .results import StudentBoxInviteLinkRecord, StudentIdentityAuthResult, StudentInvitationResult, StudentTransferResult


class CreateStudentInvitation:
    def __init__(self, repository: StudentIdentityRepositoryPort):
        self.repository = repository

    def execute(self, command: CreateStudentInvitationCommand) -> StudentInvitationResult:
        student = self.repository.find_student_by_id(command.student_id)
        if student is None:
            return StudentInvitationResult(success=False, invitation=None, failure_reason='student-not-found')

        invited_email = (getattr(student, 'email', '') or '').strip().lower()
        if not invited_email and command.onboarding_journey != 'imported_lead_invite':
            return StudentInvitationResult(success=False, invitation=None, failure_reason='email-required')

        existing_identity = self.repository.find_live_by_student_id(student.id)
        if existing_identity is not None and existing_identity.box_root_slug != command.box_root_slug:
            return StudentInvitationResult(success=False, invitation=None, failure_reason='student-box-mismatch')

        if command.invite_type == 'open_box':
            window_hours = max(1, int(getattr(settings, 'STUDENT_OPEN_BOX_INVITE_WINDOW_HOURS', 24)))
            limit = max(1, int(getattr(settings, 'STUDENT_OPEN_BOX_INVITE_LIMIT_PER_WINDOW', 25)))
            recent_open_box_invites = self.repository.count_open_box_invites_since(
                box_root_slug=command.box_root_slug,
                since=timezone.now() - timedelta(hours=window_hours),
            )
            if recent_open_box_invites >= limit:
                return StudentInvitationResult(
                    success=False,
                    invitation=None,
                    failure_reason='open-box-rate-limit-exceeded',
                )

        invitation = self.repository.create_invitation(
            student=student,
            invited_email=invited_email,
            box_root_slug=command.box_root_slug,
            invite_type=command.invite_type,
            onboarding_journey=command.onboarding_journey,
            expires_in_days=command.expires_in_days,
            actor_id=command.actor_id,
        )
        return StudentInvitationResult(success=True, invitation=invitation)


class CreateStudentBoxInviteLink:
    def __init__(self, repository: StudentIdentityRepositoryPort):
        self.repository = repository

    def execute(self, command: CreateStudentBoxInviteLinkCommand) -> StudentBoxInviteLinkRecord:
        return self.repository.create_or_replace_box_invite_link(
            box_root_slug=command.box_root_slug,
            expires_in_days=command.expires_in_days,
            max_uses=command.max_uses,
            actor_id=command.actor_id,
        )


class AuthenticateStudentWithProvider:
    def __init__(self, repository: StudentIdentityRepositoryPort):
        self.repository = repository

    def execute(self, command: AuthenticateStudentWithProviderCommand) -> StudentIdentityAuthResult:
        provider_subject = command.provider_subject.strip().lower()
        if not provider_subject:
            return StudentIdentityAuthResult(success=False, identity=None, failure_reason='provider-subject-required')

        existing_by_subject = self.repository.find_by_provider_subject(provider_subject=provider_subject)
        if existing_by_subject is not None:
            if existing_by_subject.box_root_slug != command.box_root_slug:
                return StudentIdentityAuthResult(success=False, identity=None, failure_reason='box-root-mismatch')
            return StudentIdentityAuthResult(success=True, identity=self.repository.mark_authenticated(existing_by_subject))

        invitation = None
        student = None
        if command.invite_token.strip():
            invitation = self.repository.find_invitation_by_token(command.invite_token.strip())
            if invitation is None:
                return StudentIdentityAuthResult(success=False, identity=None, failure_reason='invite-not-found')
            if invitation.box_root_slug != command.box_root_slug:
                return StudentIdentityAuthResult(success=False, identity=None, failure_reason='invite-box-mismatch')
            if invitation.is_expired:
                return StudentIdentityAuthResult(success=False, identity=None, failure_reason='invite-expired')
            if invitation.invited_email and invitation.invited_email.strip().lower() != command.email.strip().lower():
                return StudentIdentityAuthResult(success=False, identity=None, failure_reason='invite-email-mismatch')
            student = invitation.student
        else:
            candidates = self.repository.find_student_candidates_by_email(email=command.email)
            if len(candidates) != 1:
                return StudentIdentityAuthResult(success=False, identity=None, failure_reason='student-email-ambiguous')
            student = candidates[0]

        existing_identity = self.repository.find_live_by_student_id(student.id)
        if existing_identity is not None and existing_identity.box_root_slug != command.box_root_slug:
            return StudentIdentityAuthResult(success=False, identity=None, failure_reason='student-box-mismatch')

        saved = self.repository.save_identity(
            student=student,
            box_root_slug=command.box_root_slug,
            provider=command.provider,
            provider_subject=provider_subject,
            email=command.email,
            invitation=invitation,
        )
        return StudentIdentityAuthResult(success=True, identity=saved)


class TransferStudentToBox:
    def __init__(self, repository: StudentIdentityRepositoryPort):
        self.repository = repository

    def execute(self, command: TransferStudentToBoxCommand) -> StudentTransferResult:
        identity = self.repository.find_identity_by_id(command.identity_id)
        if identity is None:
            return StudentTransferResult(success=False, identity=None, failure_reason='identity-not-found')
        if identity.box_root_slug == command.to_box_root_slug:
            return StudentTransferResult(success=False, identity=None, failure_reason='same-box')

        existing_in_target = self.repository.find_live_by_email_and_box(
            email=identity.email,
            box_root_slug=command.to_box_root_slug,
        )
        if existing_in_target is not None and existing_in_target.id != identity.id:
            return StudentTransferResult(success=False, identity=None, failure_reason='target-box-email-conflict')

        updated_identity, transfer_id = self.repository.transfer_identity(
            identity=identity,
            to_box_root_slug=command.to_box_root_slug,
            actor_id=command.actor_id,
            reason=command.reason,
        )
        return StudentTransferResult(
            success=True,
            identity=updated_identity,
            transfer_id=transfer_id,
        )
