"""
ARQUIVO: cobertura do gate de entrada PAR-Q + termo (Onda B).

POR QUE ELE EXISTE:
- valida o criterio de aceite da Onda B do plano
  docs/plans/student-parq-waiver-entry-gate-corda.md: caminho feliz, caminho
  flagged, liberacao manual, rollback pela feature flag e a guarda contra
  `active_membership is None`/nao-ACTIVE (secao 6.1 do plano).

PONTO CRITICO:
- exige PostgreSQL + django-tenants (conftest cria o schema box_test).
"""

from __future__ import annotations

from io import StringIO

from django.core.cache import cache
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from auditing.models import AuditEvent
from student_app._test_fixtures import STUDENT_SESSION_COOKIE, auth_cookie_value, create_onboarded_student
from student_identity.models import StudentBoxMembership, StudentConsent, StudentConsentDocumentKind, StudentParqOutcome
from student_identity.parq_questions import PARQ_V1_QUESTIONS


def _seed_documents():
    call_command('seed_consent_documents', stdout=StringIO())


def _consent_post_data(*, parq_version='1', waiver_version='1', all_no=True, flagged_index=0):
    data = {'parq_version': parq_version, 'waiver_version': waiver_version}
    for index in range(1, len(PARQ_V1_QUESTIONS) + 1):
        data[f'parq_{index}'] = 'no' if all_no or index - 1 != flagged_index else 'yes'
    return data


@override_settings(STUDENT_CONSENT_GATE_ENABLED=True)
class StudentConsentGateTests(TestCase):
    def setUp(self):
        cache.clear()
        _seed_documents()
        self.client = Client()
        self.student, self.identity = create_onboarded_student()
        self.client.cookies[STUDENT_SESSION_COOKIE] = auth_cookie_value(self.identity)

    def _membership(self):
        return StudentBoxMembership.objects.get(identity=self.identity)

    def test_home_redirects_to_consent_when_missing(self):
        response = self.client.get(reverse('student-app-home'))
        self.assertRedirects(response, reverse('student-app-consent'))

    def test_clear_outcome_enters_normally(self):
        response = self.client.post(reverse('student-app-consent'), data=_consent_post_data(all_no=True))
        self.assertRedirects(response, reverse('student-app-home'))

        parq_consent = StudentConsent.objects.get(identity=self.identity, document_kind=StudentConsentDocumentKind.PARQ)
        self.assertEqual(parq_consent.parq_outcome, StudentParqOutcome.CLEAR)
        self.assertFalse(self._membership().clearance_required)

        # revisita: consentimento em dia, nao volta a ver o gate
        response = self.client.get(reverse('student-app-home'))
        self.assertEqual(response.status_code, 200)

    def test_flagged_outcome_blocks_entry_until_cleared(self):
        response = self.client.post(reverse('student-app-consent'), data=_consent_post_data(all_no=False, flagged_index=2))
        self.assertRedirects(response, reverse('student-app-clearance'))

        membership = self._membership()
        self.assertTrue(membership.clearance_required)
        self.assertIsNone(membership.cleared_at)

        parq_consent = StudentConsent.objects.get(identity=self.identity, document_kind=StudentConsentDocumentKind.PARQ)
        self.assertEqual(parq_consent.parq_outcome, StudentParqOutcome.FLAGGED)

        # qualquer rota do app cai na parede de liberacao, nao so a home
        for route_name in ('student-app-home', 'student-app-grade', 'student-app-wod'):
            with self.subTest(route=route_name):
                response = self.client.get(reverse(route_name))
                self.assertRedirects(response, reverse('student-app-clearance'))

        # staff libera -> volta a entrar normalmente
        membership.mark_cleared(by=None)
        membership.save(update_fields=['cleared_at', 'cleared_by', 'updated_at'])
        response = self.client.get(reverse('student-app-home'))
        self.assertEqual(response.status_code, 200)

    def test_events_recorded_with_registered_student_invite_journey_by_default(self):
        self.client.post(reverse('student-app-consent'), data=_consent_post_data(all_no=True))
        actions = set(
            AuditEvent.objects.filter(target_id=str(self.identity.id)).values_list('action', flat=True)
        )
        self.assertIn('student_onboarding.registered_student_invite.consent_step_viewed', actions)
        self.assertIn('student_onboarding.registered_student_invite.parq_completed', actions)

    def test_forged_unknown_parq_version_is_rejected_without_recording_clear(self):
        response = self.client.post(
            reverse('student-app-consent'),
            data={'parq_version': 'does-not-exist', 'waiver_version': '1'},
        )
        self.assertRedirects(response, reverse('student-app-consent'))
        self.assertFalse(StudentConsent.objects.filter(identity=self.identity).exists())

    def test_no_active_box_route_is_never_gated(self):
        # regressao do achado da revisao do plano: active_membership pode ser
        # None (ou nao-ACTIVE) nessas rotas; o gate nunca pode rodar nelas.
        StudentBoxMembership.objects.filter(identity=self.identity).delete()
        response = self.client.get(reverse('student-app-no-active-box'))
        self.assertEqual(response.status_code, 200)


class StudentConsentGateDisabledTests(TestCase):
    """Flag OFF (default) = rollback instantaneo: nenhum gate aparece."""

    def setUp(self):
        cache.clear()
        _seed_documents()
        self.client = Client()
        self.student, self.identity = create_onboarded_student()
        self.client.cookies[STUDENT_SESSION_COOKIE] = auth_cookie_value(self.identity)

    def test_home_is_not_gated_when_flag_off(self):
        response = self.client.get(reverse('student-app-home'))
        self.assertEqual(response.status_code, 200)
