"""
ARQUIVO: testes de PublicWorkoutProgramDraft + create_program_draft/
approve_and_publish_draft/reject_program_draft/_resolve_stable_program_id.

POR QUE ELE EXISTE:
- e' o gate de revisao humana obrigatoria (decisao confirmada do Renan:
  NADA gerado por IA — ou digitado a mao — vira PublicWorkoutProgram sem
  aprovacao explicita). Precisa provar que aprovar/rejeitar so' funciona
  uma vez por rascunho, e que publish_program (ja' existente, nunca
  modificado) e' quem publica de verdade.
- test_approving_second_draft_continues_the_same_version_series e' a
  prova de regressao de um bug real encontrado na revisao do plano: um
  program_id gerado do zero a cada aprovacao (ex.: carimbado com a data)
  reseta a contagem de `version` pra 1 a cada vez, mesmo sendo o 2o/3o
  programa real do aluno — _resolve_stable_program_id existe exatamente
  pra evitar isso.
"""

from django.db import IntegrityError
from django.test import TestCase

from public_workouts.models import (
    PublicWorkoutAccount,
    PublicWorkoutProgram,
    PublicWorkoutProgramDraft,
    PublicWorkoutProgramDraftSource,
    PublicWorkoutProgramDraftStatus,
)
from public_workouts.schema import build_example_payload
from public_workouts.services import (
    ProgramDraftReviewError,
    approve_and_publish_draft,
    create_program_draft,
    reject_program_draft,
)


def _payload_for(slug: str) -> dict:
    payload = build_example_payload()
    payload['program_id'] = f'{slug}-qualquer-coisa'  # nunca deveria sobreviver a aprovacao
    return payload


class ProgramDraftModelTests(TestCase):
    def setUp(self):
        self.account = PublicWorkoutAccount.objects.create(email='aluno@example.com')

    def test_two_pending_drafts_for_same_account_and_slug_raise_integrity_error(self):
        create_program_draft(
            account_id=self.account.pk, slug='bruno', payload=_payload_for('bruno'),
            source=PublicWorkoutProgramDraftSource.MANUAL,
        )
        with self.assertRaises(IntegrityError):
            create_program_draft(
                account_id=self.account.pk, slug='bruno', payload=_payload_for('bruno'),
                source=PublicWorkoutProgramDraftSource.MANUAL,
            )

    def test_new_pending_draft_allowed_after_previous_one_rejected(self):
        first = create_program_draft(
            account_id=self.account.pk, slug='bruno', payload=_payload_for('bruno'),
            source=PublicWorkoutProgramDraftSource.MANUAL,
        )
        reject_program_draft(draft_id=first.pk, reviewed_by=None)

        second = create_program_draft(
            account_id=self.account.pk, slug='bruno', payload=_payload_for('bruno'),
            source=PublicWorkoutProgramDraftSource.MANUAL,
        )
        self.assertEqual(PublicWorkoutProgramDraft.objects.filter(account=self.account).count(), 2)
        self.assertEqual(second.status, PublicWorkoutProgramDraftStatus.PENDING_REVIEW)


class ApproveAndPublishDraftTests(TestCase):
    def setUp(self):
        self.account = PublicWorkoutAccount.objects.create(email='aluno@example.com')

    def test_approving_publishes_active_program_version_1(self):
        draft = create_program_draft(
            account_id=self.account.pk, slug='bruno', payload=_payload_for('bruno'),
            source=PublicWorkoutProgramDraftSource.AI_GENERATED, ai_model='claude-haiku-4-5-20251001',
        )

        program = approve_and_publish_draft(draft_id=draft.pk, reviewed_by=None)

        self.assertEqual(program.version, 1)
        self.assertTrue(program.is_active)
        draft.refresh_from_db()
        self.assertEqual(draft.status, PublicWorkoutProgramDraftStatus.APPROVED)
        self.assertIsNotNone(draft.reviewed_at)

    def test_program_id_never_trusts_the_drafts_payload(self):
        draft = create_program_draft(
            account_id=self.account.pk, slug='bruno', payload=_payload_for('bruno'),
            source=PublicWorkoutProgramDraftSource.MANUAL,
        )

        program = approve_and_publish_draft(draft_id=draft.pk, reviewed_by=None)

        self.assertNotEqual(program.program_id, 'bruno-qualquer-coisa')
        self.assertEqual(program.program_id, 'bruno-program')

    def test_approving_second_draft_continues_the_same_version_series(self):
        """Regressao: um program_id novo a cada aprovacao (ex.: carimbado
        com a data de geracao) faria a 2a aprovacao nascer v1 de novo, em
        vez de v2 — quebrando silenciosamente o historico de versoes do
        aluno."""
        first_draft = create_program_draft(
            account_id=self.account.pk, slug='bruno', payload=_payload_for('bruno'),
            source=PublicWorkoutProgramDraftSource.AI_GENERATED,
        )
        first_program = approve_and_publish_draft(draft_id=first_draft.pk, reviewed_by=None)

        # Um segundo rascunho de IA, com um program_id DIFERENTE do primeiro
        # (mesmo cenario de um pipeline que carimba program_id com a data).
        second_payload = _payload_for('bruno')
        second_payload['program_id'] = 'bruno-rascunho-outro-dia-completamente-diferente'
        second_draft = create_program_draft(
            account_id=self.account.pk, slug='bruno', payload=second_payload,
            source=PublicWorkoutProgramDraftSource.AI_GENERATED,
        )

        second_program = approve_and_publish_draft(draft_id=second_draft.pk, reviewed_by=None)

        self.assertEqual(second_program.program_id, first_program.program_id)
        self.assertEqual(second_program.version, 2)
        self.assertTrue(second_program.is_active)
        first_program.refresh_from_db()
        self.assertFalse(first_program.is_active)

    def test_approving_non_pending_draft_raises_and_does_not_republish(self):
        draft = create_program_draft(
            account_id=self.account.pk, slug='bruno', payload=_payload_for('bruno'),
            source=PublicWorkoutProgramDraftSource.MANUAL,
        )
        approve_and_publish_draft(draft_id=draft.pk, reviewed_by=None)

        with self.assertRaises(ProgramDraftReviewError):
            approve_and_publish_draft(draft_id=draft.pk, reviewed_by=None)

        self.assertEqual(PublicWorkoutProgram.objects.filter(slug='bruno').count(), 1)


class RejectProgramDraftTests(TestCase):
    def setUp(self):
        self.account = PublicWorkoutAccount.objects.create(email='aluno@example.com')

    def test_rejecting_never_creates_a_published_program(self):
        draft = create_program_draft(
            account_id=self.account.pk, slug='bruno', payload=_payload_for('bruno'),
            source=PublicWorkoutProgramDraftSource.AI_GENERATED,
        )

        reject_program_draft(draft_id=draft.pk, reviewed_by=None, reason='movimento errado pro joelho')

        draft.refresh_from_db()
        self.assertEqual(draft.status, PublicWorkoutProgramDraftStatus.REJECTED)
        self.assertEqual(draft.rejection_reason, 'movimento errado pro joelho')
        self.assertFalse(PublicWorkoutProgram.objects.filter(slug='bruno').exists())

    def test_rejecting_non_pending_draft_raises(self):
        draft = create_program_draft(
            account_id=self.account.pk, slug='bruno', payload=_payload_for('bruno'),
            source=PublicWorkoutProgramDraftSource.MANUAL,
        )
        reject_program_draft(draft_id=draft.pk, reviewed_by=None)

        with self.assertRaises(ProgramDraftReviewError):
            reject_program_draft(draft_id=draft.pk, reviewed_by=None)
