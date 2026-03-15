"""
ARQUIVO: testes da Central de Intake.

POR QUE ELE EXISTE:
- Protege a nova fronteira visual de onboarding que passa a concentrar a fila principal de entradas.

O QUE ESTE ARQUIVO FAZ:
1. Testa acesso autenticado da central.
2. Testa renderizacao da fila e do handoff para conversao em aluno.

PONTOS CRITICOS:
- Se falhar, o sistema pode continuar com a rota antiga em Alunos e perder a nova fronteira canonica de intake.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from access.roles import ROLE_RECEPTION
from onboarding.models import IntakeStatus, StudentIntake


class IntakeCenterViewTests(TestCase):
    def setUp(self):
        cache.clear()
        call_command('bootstrap_roles')
        self.user = get_user_model().objects.create_superuser(
            username='intake-owner',
            email='intake-owner@example.com',
            password='senha-forte-123',
        )
        self.reception = get_user_model().objects.create_user(
            username='intake-reception',
            email='intake-reception@example.com',
            password='senha-forte-123',
            is_staff=True,
        )
        self.reception.groups.add(Group.objects.get(name=ROLE_RECEPTION))
        self.intake = StudentIntake.objects.create(
            full_name='Lead Central',
            phone='5511999993333',
            email='lead.central@example.com',
            source='whatsapp',
            status=IntakeStatus.NEW,
        )
        self.convertible_intake = StudentIntake.objects.create(
            full_name='Triado Central',
            phone='5511999994444',
            email='triado.central@example.com',
            source='manual',
            status=IntakeStatus.MATCHED,
        )

    def test_redirects_when_user_is_not_authenticated(self):
        response = self.client.get(reverse('intake-center'))

        self.assertEqual(response.status_code, 302)

    def test_intake_center_renders_queue_and_conversion_handoff(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('intake-center'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Triagem e conversao antes do aluno definitivo.')
        self.assertContains(response, 'id="intake-queue-board"')
        self.assertContains(response, 'Lead Central')
        self.assertContains(response, 'Lead aberto')
        self.assertContains(response, 'Triar antes de converter')
        self.assertContains(response, f'/alunos/novo/?intake={self.convertible_intake.id}#student-form-essential')

    def test_intake_center_filters_queue_by_status(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('intake-center'), {'status': IntakeStatus.MATCHED})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Triado Central')
        self.assertNotContains(response, 'Lead Central')
        self.assertContains(response, 'aria-label="Prioridade: 1.', html=False)
        self.assertNotContains(response, 'pulse-pending has-count')

    def test_reception_can_assume_and_start_review_from_intake_center(self):
        self.client.force_login(self.reception)

        assign_response = self.client.post(
            reverse('intake-center'),
            data={
                'intake_id': self.intake.id,
                'action': 'assign-to-me',
                'return_query': '',
            },
            follow=True,
        )

        self.assertEqual(assign_response.status_code, 200)
        self.intake.refresh_from_db()
        self.assertEqual(self.intake.assigned_to_id, self.reception.id)
        self.assertContains(assign_response, 'agora esta com voce')

        review_response = self.client.post(
            reverse('intake-center'),
            data={
                'intake_id': self.intake.id,
                'action': 'start-review',
                'return_query': '',
            },
            follow=True,
        )

        self.assertEqual(review_response.status_code, 200)
        self.intake.refresh_from_db()
        self.assertEqual(self.intake.status, IntakeStatus.REVIEWING)
        self.assertContains(review_response, 'entrou em revisao')