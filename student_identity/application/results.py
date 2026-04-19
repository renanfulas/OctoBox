from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class StudentInvitationRecord:
    id: int
    token: str
    student_id: int
    student_name: str
    invite_type: str
    onboarding_journey: str
    invited_email: str
    box_root_slug: str
    expires_at_iso: str
    accepted_at_iso: str = ''


@dataclass(frozen=True, slots=True)
class StudentIdentityRecord:
    id: int
    student_id: int
    student_name: str
    email: str
    provider: str
    box_root_slug: str
    primary_box_root_slug: str
    status: str


@dataclass(frozen=True, slots=True)
class StudentIdentityAuthResult:
    success: bool
    identity: StudentIdentityRecord | None
    failure_reason: str = ''


@dataclass(frozen=True, slots=True)
class StudentInvitationResult:
    success: bool
    invitation: StudentInvitationRecord | None
    failure_reason: str = ''


@dataclass(frozen=True, slots=True)
class StudentTransferResult:
    success: bool
    identity: StudentIdentityRecord | None
    transfer_id: int | None = None
    failure_reason: str = ''


@dataclass(frozen=True, slots=True)
class StudentBoxInviteLinkRecord:
    id: int
    token: str
    box_root_slug: str
    expires_at_iso: str
    max_uses: int
    use_count: int
    paused_at_iso: str = ''
    revoked_at_iso: str = ''
