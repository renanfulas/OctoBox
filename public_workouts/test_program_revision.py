"""Revisão guiada de programa ativo: cópia, gate humano e versão de origem."""

from copy import deepcopy

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from public_workouts.guided_draft import prepare_guided_payload
from public_workouts.models import (
    PublicWorkoutAccount, PublicWorkoutMovement, PublicWorkoutMovementModality,
    PublicWorkoutMovementStatus, PublicWorkoutProgram, PublicWorkoutProgramDraft,
    PublicWorkoutProgramDraftStatus, PublicWorkoutSubscription,
    PublicWorkoutSubscriptionStatus, PublicWorkoutTier,
)
from public_workouts.program_revision import ProgramRevisionError, create_guided_revision_draft
from public_workouts.schema import build_example_payload
from public_workouts.services import (
    ProgramDraftReviewError, approve_and_publish_draft, publish_program, save_training_profile,
)


class PrepareGuidedPayloadTests(SimpleTestCase):
    def test_prepares_only_clear_text_without_mutating_source(self):
        source = build_example_payload()
        movement = source['days'][0]['blocks'][0]['movements'][0]
        ambiguous = deepcopy(movement)
        ambiguous['reps_spec'] = 'séries a combinar'
        source['days'][0]['blocks'][0]['movements'].append(ambiguous)
        original = deepcopy(source)

        prepared, count, unresolved = prepare_guided_payload(source)

        self.assertEqual((count, unresolved), (1, 1))
        self.assertEqual(source, original)
        self.assertIn('guided_prescription', prepared['days'][0]['blocks'][0]['movements'][0])
        self.assertNotIn('guided_prescription', prepared['days'][0]['blocks'][0]['movements'][1])


class ProgramRevisionTests(TestCase):
    def setUp(self):
        self.account = PublicWorkoutAccount.objects.create(email='revisao@example.com')
        self.subscription = PublicWorkoutSubscription.objects.create(
            account=self.account, plan_slug='bruno', tier=PublicWorkoutTier.COMPLETO,
            status=PublicWorkoutSubscriptionStatus.ACTIVE,
        )
        PublicWorkoutMovement.objects.create(
            slug='agachamento-livre', label_pt='Agachamento livre',
            modality=PublicWorkoutMovementModality.STRENGTH,
            status=PublicWorkoutMovementStatus.ACTIVE,
        )
        self.original = publish_program(slug='bruno', payload=build_example_payload())

    def test_revision_is_pending_and_original_program_remains_active(self):
        original_payload = deepcopy(self.original.payload)
        draft, prepared, unresolved = create_guided_revision_draft(subscription_id=self.subscription.pk)

        self.assertEqual((prepared, unresolved), (1, 0))
        self.assertEqual(draft.base_program_id, self.original.pk)
        self.assertEqual(draft.status, PublicWorkoutProgramDraftStatus.PENDING_REVIEW)
        self.assertIn('guided_prescription', draft.payload['days'][0]['blocks'][0]['movements'][0])
        self.original.refresh_from_db()
        self.assertTrue(self.original.is_active)
        self.assertEqual(self.original.payload, original_payload)
        self.assertEqual(PublicWorkoutProgram.objects.count(), 1)

    def test_revision_keeps_training_restrictions_visible_to_reviewer(self):
        save_training_profile(
            account_id=self.account.pk, goal='hypertrophy', physical_restrictions=['joelho'],
            physical_restrictions_detail='', training_experience='less_than_6_months',
            days_per_week=3, training_location='full_gym', motivation='',
            biggest_difficulty='', consent_given=True,
        )
        draft, _, _ = create_guided_revision_draft(subscription_id=self.subscription.pk)
        self.assertEqual(draft.training_profile_snapshot['physical_restrictions'], ['joelho'])

    def test_second_revision_does_not_overwrite_pending_review(self):
        create_guided_revision_draft(subscription_id=self.subscription.pk)
        with self.assertRaisesMessage(ProgramRevisionError, 'Já existe rascunho pendente'):
            create_guided_revision_draft(subscription_id=self.subscription.pk)
        self.assertEqual(PublicWorkoutProgramDraft.objects.count(), 1)

    def test_shared_slug_is_not_silently_revised_for_two_accounts(self):
        other = PublicWorkoutAccount.objects.create(email='outro@example.com')
        PublicWorkoutSubscription.objects.create(
            account=other, plan_slug='bruno', tier=PublicWorkoutTier.COMPLETO,
            status=PublicWorkoutSubscriptionStatus.ACTIVE,
        )
        with self.assertRaisesMessage(ProgramRevisionError, 'Slug compartilhado'):
            create_guided_revision_draft(subscription_id=self.subscription.pk)
        self.assertFalse(PublicWorkoutProgramDraft.objects.exists())

    def test_reviewed_revision_publishes_new_version(self):
        draft, _, _ = create_guided_revision_draft(subscription_id=self.subscription.pk)
        program = approve_and_publish_draft(draft_id=draft.pk, reviewed_by=None)

        self.assertEqual(program.version, self.original.version + 1)
        self.assertTrue(program.is_active)
        self.original.refresh_from_db()
        self.assertFalse(self.original.is_active)
        draft.refresh_from_db()
        self.assertEqual(draft.status, PublicWorkoutProgramDraftStatus.APPROVED)

    def test_stale_revision_cannot_replace_newer_active_program(self):
        draft, _, _ = create_guided_revision_draft(subscription_id=self.subscription.pk)
        newer = publish_program(slug='bruno', payload=build_example_payload())

        with self.assertRaisesMessage(ProgramDraftReviewError, 'versão de origem deixou'):
            approve_and_publish_draft(draft_id=draft.pk, reviewed_by=None)

        draft.refresh_from_db()
        newer.refresh_from_db()
        self.assertEqual(draft.status, PublicWorkoutProgramDraftStatus.PENDING_REVIEW)
        self.assertTrue(newer.is_active)
        self.assertEqual(PublicWorkoutProgram.objects.count(), 2)

    def test_admin_action_creates_reviewable_draft(self):
        user = get_user_model().objects.create_superuser(
            username='curva-review', email='review@example.com', password='senha-forte-123',
        )
        self.client.force_login(user)
        response = self.client.post(
            reverse('admin:public_workouts_publicworkoutsubscription_changelist'),
            {'action': 'create_guided_revision', '_selected_action': [str(self.subscription.pk)]},
            follow=True,
        )

        self.assertContains(response, 'Nada foi publicado')
        self.assertEqual(PublicWorkoutProgramDraft.objects.get().base_program_id, self.original.pk)
        self.assertEqual(PublicWorkoutProgram.objects.count(), 1)
