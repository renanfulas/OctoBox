from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CreateStudentInvitationCommand:
    student_id: int
    invited_email: str
    box_root_slug: str
    invite_type: str = 'individual'
    onboarding_journey: str = 'registered_student_invite'
    expires_in_days: int = 7
    actor_id: int | None = None


@dataclass(frozen=True, slots=True)
class AuthenticateStudentWithProviderCommand:
    provider: str
    email: str
    provider_subject: str
    box_root_slug: str
    invite_token: str = ''


@dataclass(frozen=True, slots=True)
class CreateStudentBoxInviteLinkCommand:
    box_root_slug: str
    expires_in_days: int = 30
    max_uses: int = 200
    actor_id: int | None = None


@dataclass(frozen=True, slots=True)
class TransferStudentToBoxCommand:
    identity_id: int
    to_box_root_slug: str
    actor_id: int | None = None
    reason: str = ''
