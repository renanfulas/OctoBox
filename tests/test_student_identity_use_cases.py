"""
ARQUIVO: testes de unidade dos use cases de student_identity.

POR QUE EXISTE:
- student_identity é Tier 1 (bloqueia acesso do aluno ao produto).
- Os use cases são pura lógica com repositório injetado — perfeitos para
  unit tests sem banco, rápidos e deterministas.
- Anteriormente não havia nenhum teste cobrindo branches de erro de
  CreateStudentInvitation, AuthenticateStudentWithProvider ou TransferStudentToBox.

CAMADA: L1 (unit) — sem banco, sem HTTP, sem fixtures de tenant.
TEMPO ALVO: < 100ms para a suite inteira deste arquivo.

CONVENÇÃO:
- Repositório mockado via create_autospec do Protocol — garante que
  refactors na assinatura do port quebram os testes imediatamente.
- failure_reason é testado por string exata (sem assertIn genérico).
"""

from __future__ import annotations

import unittest
from unittest.mock import create_autospec, MagicMock

from student_identity.application.commands import (
    AuthenticateStudentWithProviderCommand,
    CreateStudentInvitationCommand,
    TransferStudentToBoxCommand,
)
from student_identity.application.ports import StudentIdentityRepositoryPort
from student_identity.application.results import (
    StudentIdentityRecord,
    StudentInvitationRecord,
)
from student_identity.application.use_cases import (
    AuthenticateStudentWithProvider,
    CreateStudentInvitation,
    TransferStudentToBox,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _repo() -> MagicMock:
    """Repositório mockado com autospec — assinatura do Protocol é respeitada."""
    return create_autospec(StudentIdentityRepositoryPort, instance=True)


def _student(student_id: int = 1, email: str = 'aluno@test.com') -> MagicMock:
    s = MagicMock()
    s.id = student_id
    s.email = email
    return s


def _invitation_record(**kw) -> StudentInvitationRecord:
    defaults = dict(
        id=1, token='tok-abc', student_id=1, student_name='Aluno',
        invite_type='individual', onboarding_journey='registered_student_invite',
        invited_email='aluno@test.com', box_root_slug='academia-x',
        expires_at_iso='2030-01-01T00:00:00+00:00',
    )
    defaults.update(kw)
    return StudentInvitationRecord(**defaults)


def _identity_record(**kw) -> StudentIdentityRecord:
    defaults = dict(
        id=1, student_id=1, student_name='Aluno', email='aluno@test.com',
        provider='google', box_root_slug='academia-x',
        primary_box_root_slug='academia-x', status='active',
    )
    defaults.update(kw)
    return StudentIdentityRecord(**defaults)


def _invite_cmd(**kw):
    defaults = dict(
        student_id=1, invited_email='aluno@test.com',
        box_root_slug='academia-x', invite_type='individual',
        onboarding_journey='registered_student_invite',
        expires_in_days=7, actor_id=1,
    )
    defaults.update(kw)
    return CreateStudentInvitationCommand(**defaults)


def _auth_cmd(**kw):
    defaults = dict(
        provider='google', email='aluno@test.com',
        provider_subject='google:uid-abc', box_root_slug='academia-x',
        invite_token='',
    )
    defaults.update(kw)
    return AuthenticateStudentWithProviderCommand(**defaults)


def _transfer_cmd(**kw):
    defaults = dict(
        identity_id=1, to_box_root_slug='academia-b',
        actor_id=10, reason='transfer',
    )
    defaults.update(kw)
    return TransferStudentToBoxCommand(**defaults)


# ---------------------------------------------------------------------------
# CreateStudentInvitation
# ---------------------------------------------------------------------------

class CreateStudentInvitationTest(unittest.TestCase):
    """L1: lógica pura sem banco."""

    def _uc(self, repo=None):
        return CreateStudentInvitation(repository=repo or _repo())

    def test_failure_when_student_not_found(self):
        repo = _repo()
        repo.find_student_by_id.return_value = None

        result = self._uc(repo).execute(_invite_cmd())

        self.assertFalse(result.success)
        self.assertEqual(result.failure_reason, 'student-not-found')
        repo.create_invitation.assert_not_called()

    def test_failure_when_email_empty_and_not_imported_lead(self):
        repo = _repo()
        repo.find_student_by_id.return_value = _student(email='')
        repo.find_live_by_student_id.return_value = None

        result = self._uc(repo).execute(_invite_cmd(
            invited_email='',
            onboarding_journey='registered_student_invite',
        ))

        self.assertFalse(result.success)
        self.assertEqual(result.failure_reason, 'email-required')
        repo.create_invitation.assert_not_called()

    def test_imported_lead_invite_bypasses_email_required_rule(self):
        """onboarding_journey='imported_lead_invite' pode ter email vazio."""
        repo = _repo()
        repo.find_student_by_id.return_value = _student(email='')
        repo.find_live_by_student_id.return_value = None
        repo.create_invitation.return_value = _invitation_record(invited_email='')

        result = self._uc(repo).execute(_invite_cmd(
            invited_email='',
            onboarding_journey='imported_lead_invite',
        ))

        self.assertTrue(result.success)

    def test_failure_when_student_belongs_to_different_box(self):
        repo = _repo()
        repo.find_student_by_id.return_value = _student()
        repo.find_live_by_student_id.return_value = _identity_record(
            box_root_slug='outra-academia'
        )

        result = self._uc(repo).execute(_invite_cmd(box_root_slug='academia-nova'))

        self.assertFalse(result.success)
        self.assertEqual(result.failure_reason, 'student-box-mismatch')
        repo.create_invitation.assert_not_called()

    def test_failure_when_open_box_rate_limit_exceeded(self):
        repo = _repo()
        repo.find_student_by_id.return_value = _student()
        repo.find_live_by_student_id.return_value = None
        repo.count_open_box_invites_since.return_value = 25  # limite atingido

        result = self._uc(repo).execute(_invite_cmd(invite_type='open_box'))

        self.assertFalse(result.success)
        self.assertEqual(result.failure_reason, 'open-box-rate-limit-exceeded')
        repo.create_invitation.assert_not_called()

    def test_open_box_rate_limit_not_checked_for_individual_invite(self):
        repo = _repo()
        repo.find_student_by_id.return_value = _student()
        repo.find_live_by_student_id.return_value = None
        repo.create_invitation.return_value = _invitation_record()

        self._uc(repo).execute(_invite_cmd(invite_type='individual'))

        repo.count_open_box_invites_since.assert_not_called()

    def test_success_returns_invitation_record(self):
        repo = _repo()
        invitation = _invitation_record()
        repo.find_student_by_id.return_value = _student()
        repo.find_live_by_student_id.return_value = None
        repo.create_invitation.return_value = invitation

        result = self._uc(repo).execute(_invite_cmd())

        self.assertTrue(result.success)
        self.assertEqual(result.invitation, invitation)
        self.assertEqual(result.failure_reason, '')

    def test_actor_id_and_expires_in_days_forwarded_to_repository(self):
        """Parâmetros do command devem chegar intactos ao repositório."""
        repo = _repo()
        repo.find_student_by_id.return_value = _student()
        repo.find_live_by_student_id.return_value = None
        repo.create_invitation.return_value = _invitation_record()

        self._uc(repo).execute(_invite_cmd(actor_id=99, expires_in_days=14))

        kwargs = repo.create_invitation.call_args.kwargs
        self.assertEqual(kwargs['actor_id'], 99)
        self.assertEqual(kwargs['expires_in_days'], 14)


# ---------------------------------------------------------------------------
# AuthenticateStudentWithProvider
# ---------------------------------------------------------------------------

class AuthenticateStudentWithProviderTest(unittest.TestCase):
    """L1: branches críticos de autenticação de aluno."""

    def _uc(self, repo=None):
        return AuthenticateStudentWithProvider(repository=repo or _repo())

    def test_failure_when_provider_subject_empty(self):
        repo = _repo()

        result = self._uc(repo).execute(_auth_cmd(provider_subject='   '))

        self.assertFalse(result.success)
        self.assertEqual(result.failure_reason, 'provider-subject-required')
        repo.find_by_provider_subject.assert_not_called()

    def test_failure_when_existing_identity_belongs_to_different_box(self):
        repo = _repo()
        existing = _identity_record(box_root_slug='outra-academia')
        repo.find_by_provider_subject.return_value = existing

        result = self._uc(repo).execute(_auth_cmd(box_root_slug='academia-x'))

        self.assertFalse(result.success)
        self.assertEqual(result.failure_reason, 'box-root-mismatch')
        repo.mark_authenticated.assert_not_called()

    def test_success_for_known_provider_subject_same_box(self):
        repo = _repo()
        existing = _identity_record()
        repo.find_by_provider_subject.return_value = existing
        repo.mark_authenticated.return_value = existing

        result = self._uc(repo).execute(_auth_cmd())

        self.assertTrue(result.success)
        self.assertEqual(result.identity, existing)
        repo.mark_authenticated.assert_called_once_with(existing)

    def test_failure_when_invite_token_not_found(self):
        repo = _repo()
        repo.find_by_provider_subject.return_value = None
        repo.find_invitation_by_token.return_value = None

        result = self._uc(repo).execute(_auth_cmd(invite_token='token-invalido'))

        self.assertFalse(result.success)
        self.assertEqual(result.failure_reason, 'invite-not-found')

    def test_failure_when_no_invite_and_email_ambiguous(self):
        """Sem invite_token e com múltiplos students para o email."""
        repo = _repo()
        repo.find_by_provider_subject.return_value = None
        repo.find_student_candidates_by_email.return_value = [
            _student(student_id=1),
            _student(student_id=2),
        ]

        result = self._uc(repo).execute(_auth_cmd(invite_token=''))

        self.assertFalse(result.success)
        self.assertEqual(result.failure_reason, 'student-email-ambiguous')
        repo.save_identity.assert_not_called()


# ---------------------------------------------------------------------------
# TransferStudentToBox
# ---------------------------------------------------------------------------

class TransferStudentToBoxTest(unittest.TestCase):
    """L1: TransferStudentToBox — branches de validação."""

    def _uc(self, repo=None):
        return TransferStudentToBox(repository=repo or _repo())

    def test_failure_when_identity_not_found(self):
        repo = _repo()
        repo.find_identity_by_id.return_value = None

        result = self._uc(repo).execute(_transfer_cmd())

        self.assertFalse(result.success)
        self.assertEqual(result.failure_reason, 'identity-not-found')
        repo.transfer_identity.assert_not_called()

    def test_failure_when_transferring_to_same_box(self):
        repo = _repo()
        repo.find_identity_by_id.return_value = _identity_record(
            box_root_slug='academia-b'
        )

        result = self._uc(repo).execute(_transfer_cmd(to_box_root_slug='academia-b'))

        self.assertFalse(result.success)
        self.assertEqual(result.failure_reason, 'same-box')
        repo.transfer_identity.assert_not_called()

    def test_failure_when_email_already_exists_in_target_box(self):
        repo = _repo()
        identity = _identity_record(box_root_slug='academia-a', id=1)
        conflicting = _identity_record(box_root_slug='academia-b', id=99)
        repo.find_identity_by_id.return_value = identity
        repo.find_live_by_email_and_box.return_value = conflicting  # conflito de email

        result = self._uc(repo).execute(_transfer_cmd(to_box_root_slug='academia-b'))

        self.assertFalse(result.success)
        self.assertEqual(result.failure_reason, 'target-box-email-conflict')
        repo.transfer_identity.assert_not_called()

    def test_success_calls_transfer_identity_with_correct_args(self):
        repo = _repo()
        identity = _identity_record(box_root_slug='academia-a')
        transferred = _identity_record(box_root_slug='academia-b')
        repo.find_identity_by_id.return_value = identity
        repo.find_live_by_email_and_box.return_value = None
        repo.transfer_identity.return_value = (transferred, 42)

        result = self._uc(repo).execute(_transfer_cmd(
            identity_id=1, to_box_root_slug='academia-b', actor_id=7, reason='mudou cidade'
        ))

        self.assertTrue(result.success)
        self.assertEqual(result.transfer_id, 42)
        repo.transfer_identity.assert_called_once_with(
            identity=identity,
            to_box_root_slug='academia-b',
            actor_id=7,
            reason='mudou cidade',
        )


if __name__ == '__main__':
    unittest.main()
