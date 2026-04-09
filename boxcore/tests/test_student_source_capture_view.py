"""
ARQUIVO: testes da captura externa segura de origem declarada.

POR QUE ELE EXISTE:
- garante que o link seguro consiga registrar a origem declarada no proprio OctoBox.
- protege a porta futura para mensagens e formularios externos sem login.
"""

from django.test import TestCase
from django.urls import reverse

from students.infrastructure.source_capture_links import build_student_source_capture_token
from students.models import Student


class StudentSourceCaptureViewTests(TestCase):
    def test_secure_link_can_record_declared_source(self):
        student = Student.objects.create(
            full_name='Aluno Link Seguro',
            phone='5511999995555',
            acquisition_source='instagram',
            resolved_acquisition_source='instagram',
            source_resolution_method='manual_form',
        )
        token = build_student_source_capture_token(student_id=student.id)

        response = self.client.post(
            reverse('student-source-capture'),
            data={
                'token': token,
                'declared_acquisition_source': 'referral',
                'declared_source_detail': 'indicacao da Paula',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Obrigado. Sua resposta foi registrada com sucesso.')
        student.refresh_from_db()
        declaration = student.source_declarations.get(is_active=True)
        self.assertEqual(declaration.declared_acquisition_source, 'referral')
        self.assertEqual(declaration.declared_source_channel, 'secure_link')
        self.assertTrue(student.source_conflict_flag)
        self.assertEqual(student.source_resolution_reason, 'operational_declared_conflict')
