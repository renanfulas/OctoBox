"""
ARQUIVO: testes do ponto unico de transicao de estagio do intake (Onda 4).

POR QUE ELE EXISTE:
- transition_intake_status() e mark_intake_first_contact() sao o unico
  caminho legitimo de mutacao de StudentIntake.status/first_contacted_at.
  Sem cobertura direta, uma regressao aqui volta a espalhar transicao sem
  desfecho datado e sem audit event pelos 3 arquivos que ja tinham esse
  problema antes da Onda 4.
"""

import re
from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from auditing.models import AuditEvent
from onboarding.models import IntakeStatus, StudentIntake
from onboarding.stage_transitions import mark_intake_first_contact, transition_intake_status


class TransitionIntakeStatusTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='intake-transitions-actor',
            email='intake-transitions@example.com',
            password='senha-forte-123',
        )
        self.intake = StudentIntake.objects.create(
            full_name='Lead Transicao',
            phone='5511999995555',
            source='manual',
            status=IntakeStatus.NEW,
        )

    def test_non_terminal_transition_does_not_stamp_anything(self):
        transition_intake_status(intake=self.intake, to_status=IntakeStatus.REVIEWING, actor=self.user)

        self.intake.refresh_from_db()
        self.assertEqual(self.intake.status, IntakeStatus.REVIEWING)
        self.assertIsNone(self.intake.converted_at)
        self.assertIsNone(self.intake.rejected_at)

    def test_rejected_stamps_rejected_at_once(self):
        before = timezone.now()
        transition_intake_status(intake=self.intake, to_status=IntakeStatus.REJECTED, actor=self.user)

        self.intake.refresh_from_db()
        first_rejected_at = self.intake.rejected_at
        self.assertIsNotNone(first_rejected_at)
        self.assertGreaterEqual(first_rejected_at, before)
        self.assertIsNone(self.intake.converted_at)

        # chamar de novo (ex: reprocessamento) nao pode mover o carimbo.
        transition_intake_status(intake=self.intake, to_status=IntakeStatus.REJECTED, actor=self.user)
        self.intake.refresh_from_db()
        self.assertEqual(self.intake.rejected_at, first_rejected_at)

    def test_approved_stamps_converted_at_and_conversion_kind(self):
        transition_intake_status(
            intake=self.intake,
            to_status=IntakeStatus.APPROVED,
            actor=self.user,
            conversion_kind='enrollment',
        )

        self.intake.refresh_from_db()
        self.assertIsNotNone(self.intake.converted_at)
        self.assertEqual(self.intake.conversion_kind, 'enrollment')
        self.assertIsNone(self.intake.rejected_at)

    def test_matched_does_not_stamp_converted_at(self):
        """Regressao do achado A3: MATCHED (convite disparado) nao e
        conversao comercial e nao pode gravar converted_at."""
        transition_intake_status(intake=self.intake, to_status=IntakeStatus.MATCHED, actor=self.user)

        self.intake.refresh_from_db()
        self.assertEqual(self.intake.status, IntakeStatus.MATCHED)
        self.assertIsNone(self.intake.converted_at)

    def test_transition_emits_audit_event_with_stage_metadata(self):
        transition_intake_status(
            intake=self.intake,
            to_status=IntakeStatus.REVIEWING,
            actor=self.user,
            surface='intake_center',
        )

        event = AuditEvent.objects.get(
            action='intake_stage_changed',
            target_model='studentintake',
            target_id=str(self.intake.id),
        )
        self.assertEqual(event.metadata['from_status'], IntakeStatus.NEW)
        self.assertEqual(event.metadata['to_status'], IntakeStatus.REVIEWING)
        self.assertEqual(event.metadata['surface'], 'intake_center')
        self.assertEqual(event.actor_id, self.user.id)

    def test_extra_update_fields_are_persisted_in_the_same_save(self):
        self.intake.notes = 'nota extra'
        transition_intake_status(
            intake=self.intake,
            to_status=IntakeStatus.REVIEWING,
            extra_update_fields=('notes',),
        )

        self.intake.refresh_from_db()
        self.assertEqual(self.intake.notes, 'nota extra')


class MarkIntakeFirstContactTests(TestCase):
    def setUp(self):
        self.intake = StudentIntake.objects.create(
            full_name='Lead Contato',
            phone='5511999996666',
            source='import',
            status=IntakeStatus.NEW,
        )

    def test_marks_first_contact_once(self):
        before = timezone.now()
        mark_intake_first_contact(intake=self.intake)

        self.intake.refresh_from_db()
        first_contacted_at = self.intake.first_contacted_at
        self.assertIsNotNone(first_contacted_at)
        self.assertGreaterEqual(first_contacted_at, before)

        mark_intake_first_contact(intake=self.intake)
        self.intake.refresh_from_db()
        self.assertEqual(self.intake.first_contacted_at, first_contacted_at)


class BackfillIntakeOutcomeMarkersTests(TestCase):
    """Exercita a funcao de dados da migration 0029 diretamente contra o
    registry de apps corrente — dispensa rodar o executor de migrations
    completo, e os models resolvidos sao os mesmos (campos ja existem)."""

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='intake-backfill-actor',
            email='intake-backfill@example.com',
            password='senha-forte-123',
        )

    def test_backfill_recovers_converted_at_from_audit_event(self):
        import importlib

        backfill_module = importlib.import_module(
            'boxcore.migrations.0029_backfill_intake_outcome_markers'
        )

        intake = StudentIntake.objects.create(
            full_name='Lead Historico Convertido',
            phone='5511999997777',
            source='manual',
            status=IntakeStatus.APPROVED,
        )
        self.assertIsNone(intake.converted_at)

        AuditEvent.objects.create(
            actor=self.user,
            action='student_intake_converted',
            target_model='studentintake',
            target_id=str(intake.id),
            target_label=intake.full_name,
            description='Lead convertido em aluno pela tela leve.',
            metadata={'student_id': 999},
        )

        from django.apps import apps as live_apps

        backfill_module.backfill_outcome_markers(live_apps, None)

        intake.refresh_from_db()
        self.assertIsNotNone(intake.converted_at)
        self.assertEqual(intake.conversion_kind, 'enrollment')

    def test_backfill_recovers_first_contacted_at_from_handoff_event(self):
        import importlib

        backfill_module = importlib.import_module(
            'boxcore.migrations.0029_backfill_intake_outcome_markers'
        )

        intake = StudentIntake.objects.create(
            full_name='Lead Historico Contatado',
            phone='5511999998888',
            source='import',
            status=IntakeStatus.MATCHED,
        )
        self.assertIsNone(intake.first_contacted_at)

        AuditEvent.objects.create(
            actor=self.user,
            action='student_onboarding.imported_lead_invite.whatsapp_handoff_opened',
            target_model='studentappinvitation',
            target_id='1',
            target_label='invite',
            description='Handoff do WhatsApp aberto a partir da Central de Entradas.',
            metadata={'intake_id': intake.id, 'invitation_id': 1},
        )

        from django.apps import apps as live_apps

        backfill_module.backfill_outcome_markers(live_apps, None)

        intake.refresh_from_db()
        self.assertIsNotNone(intake.first_contacted_at)

    def test_backfill_does_not_overwrite_already_stamped_values(self):
        import importlib

        backfill_module = importlib.import_module(
            'boxcore.migrations.0029_backfill_intake_outcome_markers'
        )

        original_converted_at = timezone.now() - timezone.timedelta(days=10)
        intake = StudentIntake.objects.create(
            full_name='Lead Ja Datado',
            phone='5511999999999',
            source='manual',
            status=IntakeStatus.APPROVED,
            converted_at=original_converted_at,
            conversion_kind='enrollment',
        )
        AuditEvent.objects.create(
            actor=self.user,
            action='student_intake_converted',
            target_model='studentintake',
            target_id=str(intake.id),
            target_label=intake.full_name,
            metadata={},
        )

        from django.apps import apps as live_apps

        backfill_module.backfill_outcome_markers(live_apps, None)

        intake.refresh_from_db()
        self.assertEqual(intake.converted_at, original_converted_at)


class NoDirectStatusMutationOutsideHelperTests(TestCase):
    """Guarda de regressao: os 3 pontos de chamada corrigidos na Onda 4 nao
    podem voltar a gravar StudentIntake.status por fora de
    transition_intake_status(). Escopo deliberadamente estreito (arquivos
    especificos, nao o repo inteiro) — um grep generico por 'status' bateria
    em dezenas de outros models (Payment, Enrollment, Membership, etc.) que
    nao tem nada a ver com este contrato.
    """

    CALL_SITES_THAT_MUST_USE_THE_HELPER = (
        'onboarding/facade.py',
        'onboarding/intake_invite_actions.py',
        'students/infrastructure/django_intakes.py',
    )
    DIRECT_STATUS_SAVE_PATTERN = re.compile(r"save\(\s*update_fields\s*=\s*\[[^\]]*'status'")

    def test_call_sites_do_not_save_status_directly(self):
        repo_root = Path(__file__).resolve().parent.parent
        for relative_path in self.CALL_SITES_THAT_MUST_USE_THE_HELPER:
            with self.subTest(file=relative_path):
                content = (repo_root / relative_path).read_text(encoding='utf-8')
                match = self.DIRECT_STATUS_SAVE_PATTERN.search(content)
                self.assertIsNone(
                    match,
                    f'{relative_path} voltou a gravar status fora de transition_intake_status()',
                )
