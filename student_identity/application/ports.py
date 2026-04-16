from __future__ import annotations

from typing import Protocol

from .results import StudentIdentityRecord, StudentInvitationRecord


class StudentIdentityRepositoryPort(Protocol):
    def find_student_by_id(self, student_id: int):
        ...

    def find_identity_by_id(self, identity_id: int):
        ...

    def find_live_by_student_id(self, student_id: int):
        ...

    def find_live_by_email_and_box(self, *, email: str, box_root_slug: str):
        ...

    def find_by_provider_subject(self, *, provider_subject: str):
        ...

    def find_invitation_by_token(self, token: str):
        ...

    def find_student_candidates_by_email(self, *, email: str):
        ...

    def create_invitation(
        self,
        *,
        student,
        invited_email: str,
        box_root_slug: str,
        expires_in_days: int,
        actor_id: int | None,
    ) -> StudentInvitationRecord:
        ...

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
        ...

    def mark_authenticated(self, identity) -> StudentIdentityRecord:
        ...

    def transfer_identity(
        self,
        *,
        identity,
        to_box_root_slug: str,
        actor_id: int | None,
        reason: str,
    ) -> tuple[StudentIdentityRecord, int]:
        ...
