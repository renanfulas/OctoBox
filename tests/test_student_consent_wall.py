"""
Onda C do gate de entrada — parede de clearance + gate (b).

Cobre o que sustenta o verde da homologacao desta onda:
- aluno flagged e BARRADO na entrada (redirect para a parede)
- a propria parede renderiza (sem loop)
- aluno liberado (cleared_at) passa
- aluno sem flag nao ve a parede
- gate OFF e no-op
"""
from __future__ import annotations

from io import StringIO

from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from shared_support.box_runtime import get_box_runtime_slug
from student_identity.infrastructure.session import build_student_session_value
from student_identity.models import (
    StudentBoxMembership,
    StudentBoxMembershipStatus,
    StudentIdentity,
    StudentIdentityProvider,
    StudentIdentityStatus,
)
from students.models import Student

from student_app.workflows.consent_workflows import record_consent


def _seed():
    call_command('seed_consent_documents', stdout=StringIO())


class ClearanceWallTests(TestCase):
    def setUp(self):
        _seed()
        self.client = Client()
        self.slug = get_box_runtime_slug()
        self.student = Student.objects.create(
            full_name='Atleta Wall', phone='5511666661111', email='wall@example.com',
        )
        self.identity = StudentIdentity.objects.create(
            student_id=self.student.id, student_name=self.student.full_name,
            box_root_slug=self.slug, primary_box_root_slug=self.slug,
            provider=StudentIdentityProvider.GOOGLE, provider_subject='subject-wall',
            email='wall@example.com', status=StudentIdentityStatus.ACTIVE,
        )
        self.membership = StudentBoxMembership.objects.create(
            identity=self.identity, student_id=self.student.id, box_root_slug=self.slug,
            status=StudentBoxMembershipStatus.ACTIVE,
        )
        self.client.cookies['octobox_student_session'] = build_student_session_value(
            identity_id=self.identity.id, box_root_slug=self.slug,
        )

    def _flag(self):
        record_consent(identity=self.identity, box=None, box_root_slug=self.slug, is_flagged=True)
        self.membership.refresh_from_db()

    @override_settings(STUDENT_CONSENT_GATE_ENABLED=True)
    def test_flagged_member_is_redirected_to_clearance_wall(self):
        self._flag()
        response = self.client.get(reverse('student-app-home'))
        self.assertRedirects(response, reverse('student-app-clearance'), fetch_redirect_response=False)

    @override_settings(STUDENT_CONSENT_GATE_ENABLED=True)
    def test_clearance_path_itself_renders(self):
        self._flag()
        response = self.client.get(reverse('student-app-clearance'))
        self.assertEqual(response.status_code, 200)

    @override_settings(STUDENT_CONSENT_GATE_ENABLED=True)
    def test_cleared_member_passes(self):
        self._flag()
        self.membership.mark_cleared(by=None)
        self.membership.save(update_fields=['cleared_at', 'cleared_by', 'updated_at'])
        response = self.client.get(reverse('student-app-home'))
        self.assertEqual(response.status_code, 200)

    @override_settings(STUDENT_CONSENT_GATE_ENABLED=True)
    def test_clear_member_not_redirected_to_wall(self):
        record_consent(identity=self.identity, box=None, box_root_slug=self.slug, is_flagged=False)
        response = self.client.get(reverse('student-app-home'))
        self.assertEqual(response.status_code, 200)

    def test_flag_off_does_not_show_wall(self):
        self._flag()
        response = self.client.get(reverse('student-app-home'))
        self.assertNotEqual(response.get('Location', ''), reverse('student-app-clearance'))
