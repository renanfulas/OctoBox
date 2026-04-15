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
from django.utils import timezone

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
            status=IntakeStatus.REVIEWING,
        )

    def test_redirects_when_user_is_not_authenticated(self):
        response = self.client.get(reverse('intake-center'))

        self.assertEqual(response.status_code, 302)

    def test_intake_center_renders_queue_and_primary_actions(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('intake-center'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="intake-queue-board"')
        self.assertContains(response, 'Navegacao principal de entradas')
        self.assertContains(response, 'Buscar por nome...')
        self.assertContains(response, 'Lead Central')
        self.assertContains(response, 'Lead aberto')
        self.assertContains(response, 'pode abrir a ficha definitiva direto daqui')
        self.assertContains(response, f'/alunos/novo/?intake={self.convertible_intake.id}#student-form-essential')
        self.assertContains(response, 'Recusar')
        self.assertContains(response, 'Conversar no WhatsApp')
        self.assertContains(response, 'Novo Lead')
        self.assertContains(response, 'Novo Intake')

    def test_owner_can_create_lead_inside_intake_center(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('intake-center'),
            data={
                'form_kind': 'quick-create',
                'entry_kind': 'lead',
                'lead-create-full_name': 'Lead Hero',
                'lead-create-phone': '5511998887777',
                'lead-create-email': 'lead.hero@example.com',
                'lead-create-source': 'manual',
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        created_entry = StudentIntake.objects.get(full_name='Lead Hero')
        self.assertEqual(created_entry.status, IntakeStatus.NEW)
        self.assertEqual(created_entry.raw_payload.get('entry_kind'), 'lead')
        self.assertContains(response, 'Lead cadastrado com sucesso na Central de Intake.')

    def test_owner_can_create_intake_inside_intake_center(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('intake-center'),
            data={
                'form_kind': 'quick-create',
                'entry_kind': 'intake',
                'intake-create-full_name': 'Intake Hero',
                'intake-create-phone': '5511991112222',
                'intake-create-email': 'intake.hero@example.com',
                'intake-create-source': 'whatsapp',
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        created_entry = StudentIntake.objects.get(full_name='Intake Hero')
        self.assertEqual(created_entry.status, IntakeStatus.NEW)
        self.assertEqual(created_entry.raw_payload.get('entry_kind'), 'intake')
        self.assertContains(response, 'Intake cadastrado com sucesso na Central de Intake.')

    def test_intake_center_filters_queue_by_status(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('intake-center'), {'status': IntakeStatus.REVIEWING})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Triado Central')
        self.assertNotContains(response, 'Lead Central')
        self.assertContains(response, 'aria-label="Fila: 1.', html=False)
        self.assertNotContains(response, 'pulse-pending has-count')

    def test_intake_center_kpis_link_to_server_scoped_queue_filters(self):
        self.convertible_intake.assigned_to = self.reception
        self.convertible_intake.save(update_fields=['assigned_to'])
        old_intake = StudentIntake.objects.create(
            full_name='Lead Antigo',
            phone='5511999995555',
            email='lead.antigo@example.com',
            source='manual',
            status=IntakeStatus.NEW,
        )
        StudentIntake.objects.filter(pk=old_intake.pk).update(
            created_at=timezone.now() - timezone.timedelta(days=3),
            updated_at=timezone.now() - timezone.timedelta(days=3),
        )
        self.client.force_login(self.user)

        response = self.client.get(reverse('intake-center'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'href="?panel=tab-intake-queue&amp;created_window=today"')
        self.assertContains(response, 'href="?panel=tab-intake-queue&amp;assignment=assigned"')

        today_response = self.client.get(
            reverse('intake-center'),
            {'panel': 'tab-intake-queue', 'created_window': 'today'},
        )
        self.assertEqual(today_response.status_code, 200)
        self.assertContains(today_response, 'Lead Central')
        self.assertContains(today_response, 'Triado Central')
        self.assertNotContains(today_response, 'Lead Antigo')
        self.assertContains(today_response, 'aria-label="Fila: 2.', html=False)

        assigned_response = self.client.get(
            reverse('intake-center'),
            {'panel': 'tab-intake-queue', 'assignment': 'assigned'},
        )
        self.assertEqual(assigned_response.status_code, 200)
        self.assertContains(assigned_response, 'Triado Central')
        self.assertNotContains(assigned_response, 'Lead Central')
        self.assertContains(assigned_response, 'aria-label="Fila: 1.', html=False)

    def test_reception_can_reject_from_intake_center(self):
        self.client.force_login(self.reception)

        response = self.client.post(
            reverse('intake-center'),
            data={
                'intake_id': self.intake.id,
                'action': 'reject-intake',
                'return_query': '',
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.intake.refresh_from_db()
        self.assertEqual(self.intake.status, IntakeStatus.REJECTED)
        self.assertContains(response, 'foi rejeitado e saiu da fila ativa')
