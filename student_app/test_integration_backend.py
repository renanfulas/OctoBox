"""
ARQUIVO: testes de integracao do app do aluno com o backend.

POR QUE ELE EXISTE:
- O tests.py legado exercita as views via HTTP. Aqui atacamos a fronteira do
  servico de aplicacao (os use cases) diretamente contra o ORM/Postgres, um
  angulo complementar que valida que a camada de aplicacao continua falando
  com o banco e costurando dominio + snapshots.

O QUE ESTE ARQUIVO TESTA:
1. GetStudentDashboard.execute monta um resultado coerente direto do backend
   para um aluno sem aulas publicadas.
2. GetStudentMonthSchedule.execute marca feriado brasileiro e devolve a grade
   mensal completa (amarra brazilian_holidays ao use case).
3. Round-trip real: POST em /aluno/rm/adicionar/ persiste o RM e, em seguida,
   GetStudentWorkoutPrescription.execute le esse RM do banco e calcula a carga
   recomendada (HTTP -> ORM -> use case -> dominio).

PONTO CRITICO:
- Exige PostgreSQL + django-tenants (conftest cria o schema box_test).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.test import Client, TestCase
from django.urls import reverse

from student_app._test_fixtures import (
    STUDENT_SESSION_COOKIE,
    auth_cookie_value,
    create_onboarded_student,
)
from student_app.application.use_cases import (
    GetStudentDashboard,
    GetStudentMonthSchedule,
    GetStudentWorkoutPrescription,
)
from student_app.models import StudentExerciseMax


class StudentBackendIntegrationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.student, self.identity = create_onboarded_student()
        self.client.cookies[STUDENT_SESSION_COOKIE] = auth_cookie_value(self.identity)

    def test_dashboard_use_case_returns_coherent_result_without_sessions(self):
        result = GetStudentDashboard().execute(identity=self.identity)

        self.assertEqual(result.student_name, self.student.full_name)
        self.assertEqual(result.box_root_slug, self.identity.box_root_slug)
        self.assertEqual(result.next_sessions, ())
        self.assertIsInstance(result.membership_label, str)

    def test_month_schedule_use_case_marks_brazilian_holiday(self):
        days = GetStudentMonthSchedule().execute(
            identity=self.identity,
            reference_date=date(2026, 1, 1),
        )

        real_days = [day for day in days if day.date is not None]
        self.assertEqual(len(real_days), 31)  # janeiro tem 31 dias

        new_year = next(day for day in real_days if day.date == date(2026, 1, 1))
        self.assertTrue(new_year.is_holiday)
        self.assertEqual(new_year.holiday_name, 'Ano Novo')

        regular_day = next(day for day in real_days if day.date == date(2026, 1, 5))
        self.assertFalse(regular_day.is_holiday)

    def test_rm_posted_over_http_is_read_back_by_prescription_use_case(self):
        response = self.client.post(
            reverse('student-app-rm-add'),
            {'exercise_label': 'Agachamento', 'one_rep_max_kg': '102.5'},
            follow=False,
        )
        self.assertEqual(response.status_code, 302)

        record = StudentExerciseMax.objects.get(student=self.student)
        self.assertEqual(record.one_rep_max_kg, Decimal('102.5'))

        prescription = GetStudentWorkoutPrescription().execute(
            student=self.student,
            exercise_slug=record.exercise_slug,
            percentage=Decimal('70'),
        )

        self.assertIsNotNone(prescription)
        self.assertEqual(prescription.exercise_label, 'Agachamento')
        # 70% de 102.5 = 71.75 -> arredondado HALF_UP ao incremento de 2.5kg = 72.50
        self.assertEqual(prescription.rounded_load_label, '72.50 kg')
        self.assertIn('102.5', prescription.one_rep_max_label)
