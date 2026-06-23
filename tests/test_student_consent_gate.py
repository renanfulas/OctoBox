"""
Onda B do gate de entrada — tela de consentimento + gate no dispatch.

Cobre o que sustenta o verde da homologacao desta onda:
- decisao clear/flagged e gravacao versionada (workflow)
- flagged marca clearance_required + emite eventos de funil
- waiver_accepted NAO e emitido (placeholder nao-vinculante, B1)
- form: outcome por respostas + waiver obrigatorio
- gate no dispatch: redireciona quando falta consentimento, e so com a flag ligada
"""
from __future__ import annotations

from io import StringIO

from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from auditing.models import AuditEvent
from shared_support.box_runtime import get_box_runtime_slug
from student_identity.infrastructure.session import build_student_session_value
from student_identity.models import (
    StudentBoxMembership,
    StudentBoxMembershipStatus,
    StudentConsent,
    StudentConsentDocumentKind,
    StudentIdentity,
    StudentIdentityProvider,
    StudentIdentityStatus,
    StudentParqOutcome,
)
from students.models import Student

from student_app.consent_content import PARQ_QUESTION_KEYS
from student_app.forms import StudentConsentForm
from student_app.workflows.consent_workflows import consent_is_pending, record_consent


def _seed():
    call_command('seed_consent_documents', stdout=StringIO())


def _make_student_and_identity(subject='subject-consent'):
    slug = get_box_runtime_slug()
    student = Student.objects.create(
        full_name='Atleta Consent', phone='5511666660000', email=f'{subject}@example.com',
    )
    identity = StudentIdentity.objects.create(
        student_id=student.id, student_name=student.full_name,
        box_root_slug=slug, primary_box_root_slug=slug,
        provider=StudentIdentityProvider.GOOGLE, provider_subject=subject,
        email=f'{subject}@example.com', status=StudentIdentityStatus.ACTIVE,
    )
    membership = StudentBoxMembership.objects.create(
        identity=identity, student_id=student.id, box_root_slug=slug,
        status=StudentBoxMembershipStatus.ACTIVE,
    )
    return student, identity, membership


class ConsentWorkflowTests(TestCase):
    def setUp(self):
        _seed()
        self.student, self.identity, self.membership = _make_student_and_identity()
        self.slug = get_box_runtime_slug()

    def test_consent_pending_true_before_and_false_after(self):
        self.assertTrue(consent_is_pending(identity=self.identity, box_root_slug=self.slug))
        record_consent(identity=self.identity, box=None, box_root_slug=self.slug, is_flagged=False)
        self.assertFalse(consent_is_pending(identity=self.identity, box_root_slug=self.slug))

    def test_record_consent_clear(self):
        result = record_consent(identity=self.identity, box=None, box_root_slug=self.slug, is_flagged=False)
        self.assertEqual(result.outcome, StudentParqOutcome.CLEAR)
        self.assertFalse(result.clearance_required)
        self.assertEqual(StudentConsent.objects.filter(identity=self.identity).count(), 2)
        self.membership.refresh_from_db()
        self.assertFalse(self.membership.clearance_required)

    def test_record_consent_flagged_sets_clearance_and_events(self):
        result = record_consent(identity=self.identity, box=None, box_root_slug=self.slug, is_flagged=True)
        self.assertEqual(result.outcome, StudentParqOutcome.FLAGGED)
        self.assertTrue(result.clearance_required)
        self.membership.refresh_from_db()
        self.assertTrue(self.membership.clearance_required)
        self.assertIsNone(self.membership.cleared_at)
        parq = StudentConsent.objects.get(identity=self.identity, document_kind=StudentConsentDocumentKind.PARQ)
        self.assertEqual(parq.parq_outcome, StudentParqOutcome.FLAGGED)
        self.assertTrue(AuditEvent.objects.filter(action='student_onboarding.entry_gate.parq_flagged').exists())
        self.assertTrue(AuditEvent.objects.filter(action='student_onboarding.entry_gate.clearance_pending').exists())

    def test_waiver_accepted_event_is_not_emitted(self):
        # B1: aceite de waiver placeholder nao e vinculante -> sem evento waiver_accepted
        record_consent(identity=self.identity, box=None, box_root_slug=self.slug, is_flagged=False)
        self.assertFalse(AuditEvent.objects.filter(action__contains='waiver_accepted').exists())

    def test_record_consent_is_idempotent(self):
        record_consent(identity=self.identity, box=None, box_root_slug=self.slug, is_flagged=False)
        record_consent(identity=self.identity, box=None, box_root_slug=self.slug, is_flagged=False)
        self.assertEqual(StudentConsent.objects.filter(identity=self.identity).count(), 2)


class ConsentFormTests(TestCase):
    def _data(self, *, waiver=True, flagged_key=None):
        data = {key: 'nao' for key in PARQ_QUESTION_KEYS}
        if flagged_key:
            data[flagged_key] = 'sim'
        if waiver:
            data['waiver_accepted'] = 'on'
        return data

    def test_clear_when_all_no(self):
        form = StudentConsentForm(data=self._data())
        self.assertTrue(form.is_valid(), form.errors)
        self.assertFalse(form.is_flagged)

    def test_flagged_when_any_yes(self):
        form = StudentConsentForm(data=self._data(flagged_key='q2'))
        self.assertTrue(form.is_valid(), form.errors)
        self.assertTrue(form.is_flagged)

    def test_invalid_without_waiver(self):
        form = StudentConsentForm(data=self._data(waiver=False))
        self.assertFalse(form.is_valid())
        self.assertIn('waiver_accepted', form.errors)


class ConsentGateRedirectTests(TestCase):
    def setUp(self):
        _seed()
        self.client = Client()
        self.student, self.identity, self.membership = _make_student_and_identity('subject-gate')
        self.slug = get_box_runtime_slug()
        self.client.cookies['octobox_student_session'] = build_student_session_value(
            identity_id=self.identity.id, box_root_slug=self.slug,
        )

    def test_gate_off_does_not_redirect_to_consent(self):
        # flag default OFF -> nenhum gate
        response = self.client.get(reverse('student-app-home'))
        self.assertNotEqual(response.get('Location', ''), reverse('student-app-consent'))

    @override_settings(STUDENT_CONSENT_GATE_ENABLED=True)
    def test_gate_on_redirects_when_consent_pending(self):
        response = self.client.get(reverse('student-app-home'))
        self.assertRedirects(response, reverse('student-app-consent'), fetch_redirect_response=False)

    @override_settings(STUDENT_CONSENT_GATE_ENABLED=True)
    def test_consent_path_itself_is_not_redirected(self):
        response = self.client.get(reverse('student-app-consent'))
        self.assertEqual(response.status_code, 200)

    @override_settings(STUDENT_CONSENT_GATE_ENABLED=True)
    def test_gate_passes_after_consent_recorded(self):
        record_consent(identity=self.identity, box=None, box_root_slug=self.slug, is_flagged=False)
        response = self.client.get(reverse('student-app-home'))
        self.assertEqual(response.status_code, 200)
