"""
ARQUIVO: testes de student_identity/oauth_journeys.py — jornada especial do box_invite_link.

POR QUE ELE EXISTE:
- Onda 1 (docs/plans/student-login-magic-link-bugs-corda.md): antes desta onda nao existia
  nenhum teste para oauth_journeys.py. O bug (aluno com identidade em outro box recebendo
  500 ao usar o link em massa) vivia exatamente nesse arquivo, sem cobertura.
"""
from dataclasses import dataclass
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock

from django.test import RequestFactory

from student_identity.application.results import StudentIdentityAuthResult
from student_identity.oauth_journeys import handle_student_special_oauth_journey


@dataclass(frozen=True)
class _FakeIdentityPayload:
    provider: str = 'google'
    provider_subject: str = 'google-subject-123'
    email: str = 'aluno@example.com'


def _make_repository(*, box_invite_link):
    repository = MagicMock()
    repository.find_box_invite_link_by_token.return_value = box_invite_link
    return repository


def _make_box_invite_link(*, can_accept=True):
    return SimpleNamespace(
        id=1,
        token='11111111-1111-1111-1111-111111111111',
        box_id=42,
        box_root_slug='box-b',
        can_accept=can_accept,
        use_count=0,
    )


class HandleStudentSpecialOauthJourneyBoxInviteLinkTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _make_request(self):
        request = self.factory.get('/aluno/auth/google/callback/')
        return request

    def test_box_root_mismatch_does_not_fall_through_to_onboarding(self):
        # Onda 1: antes desta correcao, qualquer result.success=False (inclusive
        # box-root-mismatch) caia no wizard de onboarding, que tentava criar uma
        # segunda StudentIdentity com o mesmo provider_subject -> IntegrityError.
        box_invite_link = _make_box_invite_link()
        repository = _make_repository(box_invite_link=box_invite_link)
        result = StudentIdentityAuthResult(success=False, identity=None, failure_reason='box-root-mismatch')

        response = handle_student_special_oauth_journey(
            request=self._make_request(),
            provider='google',
            identity_payload=_FakeIdentityPayload(),
            state_payload={'invite_token': str(box_invite_link.token)},
            result=result,
            repository=repository,
        )

        self.assertIsNone(response)
        repository.record_box_invite_acceptance.assert_not_called()

    def test_invite_not_found_proceeds_to_onboarding_wizard(self):
        # Aluno genuinamente novo: failure_reason='invite-not-found' e o unico motivo
        # que deve seguir pro wizard.
        box_invite_link = _make_box_invite_link()
        repository = _make_repository(box_invite_link=box_invite_link)
        result = StudentIdentityAuthResult(success=False, identity=None, failure_reason='invite-not-found')

        response = handle_student_special_oauth_journey(
            request=self._make_request(),
            provider='google',
            identity_payload=_FakeIdentityPayload(),
            state_payload={'invite_token': str(box_invite_link.token)},
            result=result,
            repository=repository,
        )

        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/aluno/', response.url)
        repository.record_box_invite_acceptance.assert_called_once_with(box_invite_link)

    def test_success_redirects_home_and_ignores_failure_reason(self):
        box_invite_link = _make_box_invite_link()
        repository = _make_repository(box_invite_link=box_invite_link)
        identity_record = SimpleNamespace(id=7, box_root_slug='box-b')
        result = StudentIdentityAuthResult(success=True, identity=identity_record)

        response = handle_student_special_oauth_journey(
            request=self._make_request(),
            provider='google',
            identity_payload=_FakeIdentityPayload(),
            state_payload={'invite_token': str(box_invite_link.token)},
            result=result,
            repository=repository,
        )

        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 302)
        repository.record_box_invite_acceptance.assert_not_called()
