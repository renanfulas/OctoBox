"""
ARQUIVO: testes da declaracao de origem e reconciliacao comercial do aluno.

POR QUE ELE EXISTE:
- protege a separacao entre origem operacional, declarada e resolvida.
- garante que conflitos e excecoes controladas fiquem auditaveis para analytics e ML.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase

from students.facade import run_student_source_declaration_record
from students.models import Student, StudentSourceDeclaration


class StudentSourceDeclarationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username='source-owner',
            email='source-owner@example.com',
            password='senha-forte-123',
        )

    def test_declared_source_conflict_keeps_operational_and_marks_conflict(self):
        student = Student.objects.create(
            full_name='Aluno Conflito',
            phone='5511999998888',
            acquisition_source='instagram',
            acquisition_source_detail='story da unidade',
            resolved_acquisition_source='instagram',
            resolved_source_detail='story da unidade',
            source_resolution_method='manual_form',
            source_confidence='medium',
        )

        result = run_student_source_declaration_record(
            student_id=student.id,
            declared_acquisition_source='referral',
            declared_source_detail='indicacao da Ana',
            declared_source_channel='google_form',
            declared_source_response_id='resp-1',
            actor_id=self.user.id,
        )

        student.refresh_from_db()
        active_declaration = student.source_declarations.get(is_active=True)

        self.assertEqual(result.resolved_acquisition_source, 'instagram')
        self.assertTrue(result.source_conflict_flag)
        self.assertEqual(result.source_confidence, 'low')
        self.assertEqual(student.resolved_acquisition_source, 'instagram')
        self.assertEqual(student.source_resolution_reason, 'operational_declared_conflict')
        self.assertTrue(student.source_conflict_flag)
        self.assertEqual(active_declaration.declared_acquisition_source, 'referral')
        self.assertEqual(active_declaration.declared_source_channel, 'google_form')

    def test_declared_source_can_replace_unidentified_operational(self):
        student = Student.objects.create(
            full_name='Aluno Reconciliado',
            phone='5511999997777',
            acquisition_source='unidentified',
            acquisition_source_detail='',
            resolved_acquisition_source='unidentified',
            source_resolution_method='manual_form',
            source_confidence='low',
        )

        result = run_student_source_declaration_record(
            student_id=student.id,
            declared_acquisition_source='google',
            declared_source_detail='Google Maps',
            declared_source_channel='google_form',
            declared_source_response_id='resp-2',
            actor_id=self.user.id,
        )

        student.refresh_from_db()

        self.assertEqual(result.resolved_acquisition_source, 'google')
        self.assertFalse(result.source_conflict_flag)
        self.assertEqual(result.source_confidence, 'medium')
        self.assertEqual(student.resolved_acquisition_source, 'google')
        self.assertEqual(student.resolved_source_detail, 'Google Maps')
        self.assertEqual(student.source_resolution_method, 'declared_only')
        self.assertEqual(student.source_resolution_reason, 'declared_replaced_unidentified_operational')

    def test_new_declared_source_deactivates_previous_active_response(self):
        student = Student.objects.create(
            full_name='Aluno Historico',
            phone='5511999996666',
            acquisition_source='instagram',
            resolved_acquisition_source='instagram',
            source_resolution_method='manual_form',
        )
        first_result = run_student_source_declaration_record(
            student_id=student.id,
            declared_acquisition_source='instagram',
            declared_source_channel='google_form',
            declared_source_response_id='resp-3',
            actor_id=self.user.id,
        )
        second_result = run_student_source_declaration_record(
            student_id=student.id,
            declared_acquisition_source='whatsapp',
            declared_source_channel='google_form',
            declared_source_response_id='resp-4',
            actor_id=self.user.id,
        )

        declarations = StudentSourceDeclaration.objects.filter(student=student).order_by('created_at')

        self.assertEqual(first_result.student_id, student.id)
        self.assertEqual(second_result.student_id, student.id)
        self.assertEqual(declarations.count(), 2)
        self.assertFalse(declarations.first().is_active)
        self.assertTrue(declarations.last().is_active)

