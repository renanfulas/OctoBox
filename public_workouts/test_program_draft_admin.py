"""
ARQUIVO: testes do admin de PublicWorkoutProgramDraft + da acao "Gerar
rascunho de treino com IA" em PublicWorkoutSubscriptionAdmin.

POR QUE ELE EXISTE:
- e' a prova de que o gate de revisao humana funciona de ponta a ponta
  pelo Django admin: rascunho pendente e' editavel (diferente de
  PublicWorkoutMealPlanAdmin — aqui NAO ha' snapshot publicado ainda pra
  proteger), aprovado/rejeitado vira somente-leitura, "Aprovar e publicar"
  chama o publish_program ja' existente, "Rejeitar" nunca toca
  PublicWorkoutProgram.
- a acao em PublicWorkoutSubscriptionAdmin e' a UNICA superficie que aciona
  IA neste app — precisa provar que so' gera rascunho com plan_slug E
  anamnese ja' preenchidos, e que falha de IA nunca quebra a tela (so'
  mensagem de aviso).
"""

import json
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from public_workouts.models import (
    PublicWorkoutAccount,
    PublicWorkoutMovement,
    PublicWorkoutMovementModality,
    PublicWorkoutMovementStatus,
    PublicWorkoutProgram,
    PublicWorkoutProgramDraft,
    PublicWorkoutProgramDraftStatus,
    PublicWorkoutSubscription,
    PublicWorkoutSubscriptionStatus,
    PublicWorkoutTier,
)
from public_workouts.schema import build_example_payload
from public_workouts.services import create_program_draft, save_training_profile


def _valid_payload_json() -> str:
    return json.dumps(build_example_payload())


class PublicWorkoutProgramDraftAdminTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.superuser = User.objects.create_superuser(
            username='admin', email='admin@example.com', password='senha-forte-123',
        )
        self.client.force_login(self.superuser)
        self.account = PublicWorkoutAccount.objects.create(email='aluno@example.com')

    def _add_url(self):
        return reverse('admin:public_workouts_publicworkoutprogramdraft_add')

    def _change_url(self, pk):
        return reverse('admin:public_workouts_publicworkoutprogramdraft_change', args=[pk])

    def _changelist_url(self):
        return reverse('admin:public_workouts_publicworkoutprogramdraft_changelist')

    def test_valid_payload_creates_pending_review_draft(self):
        response = self.client.post(self._add_url(), data={
            'account': self.account.pk,
            'slug': 'bruno',
            'payload': _valid_payload_json(),
            'source': 'manual',
        }, follow=True)

        self.assertEqual(response.status_code, 200)
        draft = PublicWorkoutProgramDraft.objects.get(account=self.account)
        self.assertEqual(draft.status, PublicWorkoutProgramDraftStatus.PENDING_REVIEW)
        self.assertFalse(PublicWorkoutProgram.objects.exists())  # nunca publica sozinho

    def test_invalid_json_is_rejected_without_creating_a_row(self):
        response = self.client.post(self._add_url(), data={
            'account': self.account.pk,
            'slug': 'bruno',
            'payload': '{isso nao e json',
            'source': 'manual',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'JSON invalido')
        self.assertEqual(PublicWorkoutProgramDraft.objects.count(), 0)

    def test_schema_invalid_payload_is_rejected_without_creating_a_row(self):
        broken = build_example_payload()
        del broken['days']

        response = self.client.post(self._add_url(), data={
            'account': self.account.pk,
            'slug': 'bruno',
            'payload': json.dumps(broken),
            'source': 'manual',
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(PublicWorkoutProgramDraft.objects.count(), 0)

    def test_pending_review_draft_is_editable(self):
        draft = create_program_draft(
            account_id=self.account.pk, slug='bruno', payload=build_example_payload(), source='manual'
        )

        response = self.client.get(self._change_url(draft.pk))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="_save"')

    def test_approved_draft_is_not_editable(self):
        draft = create_program_draft(
            account_id=self.account.pk, slug='bruno', payload=build_example_payload(), source='manual'
        )
        self.client.post(self._changelist_url(), {
            'action': 'approve_and_publish_action',
            '_selected_action': [str(draft.pk)],
        })

        response = self.client.get(self._change_url(draft.pk))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'name="_save"')

    def test_approve_and_publish_action_activates_a_real_program(self):
        draft = create_program_draft(
            account_id=self.account.pk, slug='bruno', payload=build_example_payload(), source='manual'
        )

        self.client.post(self._changelist_url(), {
            'action': 'approve_and_publish_action',
            '_selected_action': [str(draft.pk)],
        })

        draft.refresh_from_db()
        self.assertEqual(draft.status, PublicWorkoutProgramDraftStatus.APPROVED)
        program = PublicWorkoutProgram.objects.get(slug='bruno')
        self.assertTrue(program.is_active)

    def test_reject_action_never_creates_a_program(self):
        draft = create_program_draft(
            account_id=self.account.pk, slug='bruno', payload=build_example_payload(), source='manual'
        )

        self.client.post(self._changelist_url(), {
            'action': 'reject_action',
            '_selected_action': [str(draft.pk)],
        })

        draft.refresh_from_db()
        self.assertEqual(draft.status, PublicWorkoutProgramDraftStatus.REJECTED)
        self.assertFalse(PublicWorkoutProgram.objects.exists())


class GenerateAiDraftSubscriptionActionTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.superuser = User.objects.create_superuser(
            username='admin2', email='admin2@example.com', password='senha-forte-123',
        )
        self.client.force_login(self.superuser)
        self.account = PublicWorkoutAccount.objects.create(email='aluno@example.com')
        self.subscription = PublicWorkoutSubscription.objects.create(
            account=self.account,
            plan_slug='bruno',
            tier=PublicWorkoutTier.COMPLETO,
            status=PublicWorkoutSubscriptionStatus.ACTIVE,
        )
        PublicWorkoutMovement.objects.create(
            slug='agachamento-livre', label_pt='Agachamento livre',
            modality=PublicWorkoutMovementModality.STRENGTH, status=PublicWorkoutMovementStatus.ACTIVE,
        )

    def _changelist_url(self):
        return reverse('admin:public_workouts_publicworkoutsubscription_changelist')

    def _run_action(self):
        return self.client.post(self._changelist_url(), {
            'action': 'generate_ai_draft',
            '_selected_action': [str(self.subscription.pk)],
        }, follow=True)

    def test_errors_without_plan_slug(self):
        self.subscription.plan_slug = None
        self.subscription.save(update_fields=['plan_slug'])

        response = self._run_action()

        self.assertContains(response, 'defina plan_slug')
        self.assertFalse(PublicWorkoutProgramDraft.objects.exists())

    def test_errors_without_training_profile(self):
        response = self._run_action()

        self.assertContains(response, 'não respondeu')
        self.assertFalse(PublicWorkoutProgramDraft.objects.exists())

    def test_warns_when_generation_fails(self):
        save_training_profile(
            account_id=self.account.pk, goal='hypertrophy', physical_restrictions=[],
            physical_restrictions_detail='', training_experience='less_than_6_months', days_per_week=3,
            training_location='full_gym', motivation='', biggest_difficulty='', consent_given=True,
        )

        with mock.patch(
            'public_workouts.admin.generate_program_draft_payload', return_value=(None, 'claude-haiku-4-5-20251001')
        ):
            response = self._run_action()

        self.assertContains(response, 'geração falhou')
        self.assertFalse(PublicWorkoutProgramDraft.objects.exists())

    def test_creates_pending_draft_on_success(self):
        save_training_profile(
            account_id=self.account.pk, goal='hypertrophy', physical_restrictions=[],
            physical_restrictions_detail='', training_experience='less_than_6_months', days_per_week=3,
            training_location='full_gym', motivation='', biggest_difficulty='', consent_given=True,
        )

        with mock.patch(
            'public_workouts.admin.generate_program_draft_payload',
            return_value=(build_example_payload(), 'claude-haiku-4-5-20251001'),
        ):
            response = self._run_action()

        self.assertContains(response, 'rascunho gerado')
        draft = PublicWorkoutProgramDraft.objects.get(account=self.account)
        self.assertEqual(draft.status, PublicWorkoutProgramDraftStatus.PENDING_REVIEW)
        self.assertEqual(draft.source, 'ai_generated')
        self.assertEqual(draft.ai_model, 'claude-haiku-4-5-20251001')

    def test_second_generation_with_pending_draft_already_open_warns_instead_of_duplicating(self):
        save_training_profile(
            account_id=self.account.pk, goal='hypertrophy', physical_restrictions=[],
            physical_restrictions_detail='', training_experience='less_than_6_months', days_per_week=3,
            training_location='full_gym', motivation='', biggest_difficulty='', consent_given=True,
        )
        create_program_draft(
            account_id=self.account.pk, slug='bruno', payload=build_example_payload(), source='ai_generated'
        )

        with mock.patch(
            'public_workouts.admin.generate_program_draft_payload',
            return_value=(build_example_payload(), 'claude-haiku-4-5-20251001'),
        ):
            response = self._run_action()

        self.assertContains(response, 'já existe rascunho pendente')
        self.assertEqual(PublicWorkoutProgramDraft.objects.filter(account=self.account).count(), 1)
