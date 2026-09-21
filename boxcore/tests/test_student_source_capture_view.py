"""
ARQUIVO: testes da captura externa segura de origem declarada.

POR QUE ELE EXISTE:
- garante que o link seguro consiga registrar a origem declarada no proprio OctoBox.
- protege a porta futura para mensagens e formularios externos sem login.
"""

from django.test import TestCase
from django.urls import reverse

from students.infrastructure.source_capture_links import build_student_source_capture_token
from tests.factories import StudentFactory


class StudentSourceCaptureViewTests(TestCase):
    def test_secure_link_can_record_declared_source(self):
        student = StudentFactory(
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

    def test_missing_token_shows_specific_message_instead_of_generic_404(self):
        # Onda 4 (docs/plans/student-login-magic-link-bugs-corda.md): antes desta
        # onda, token ausente/invalido/aluno-nao-encontrado caiam todos no Http404
        # generico do site (templates/404.html), sem dizer o motivo.
        response = self.client.get(reverse('student-source-capture'))

        self.assertEqual(response.status_code, 404)
        self.assertContains(response, 'Esse link está incompleto.', status_code=404)

    def test_invalid_token_shows_specific_message_instead_of_generic_404(self):
        response = self.client.get(reverse('student-source-capture'), {'token': 'nao-e-um-token-valido'})

        self.assertEqual(response.status_code, 404)
        self.assertContains(response, 'Não conseguimos validar esse link.', status_code=404)

    def test_student_not_found_shows_specific_message_instead_of_generic_404(self):
        token = build_student_source_capture_token(student_id=999999999)

        response = self.client.get(reverse('student-source-capture'), {'token': token})

        self.assertEqual(response.status_code, 404)
        self.assertContains(response, 'Não encontramos seu cadastro.', status_code=404)
