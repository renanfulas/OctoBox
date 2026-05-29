"""
ARQUIVO: testes de control.services (ciclo de vida de Box).

POR QUE EXISTE:
- control.services provisiona e arquiva Boxes — path crítico de onboarding.
- Bug aqui impede novos clientes de entrar. Não havia nenhum teste.

CAMADAS:
- L1 (unit): derive_slug — puro, sem banco.
- L2 (integration): provision_box / reprovision_box — banco SQLite real.
  _run_step é mockado para evitar DDL (CREATE SCHEMA, etc.) que requer PostgreSQL.
  O que testamos é a orquestração de steps, criação de modelos e idempotência.
- L3 (requires_postgres): archive_box — ALTER SCHEMA é DDL real, só em PostgreSQL.

MOCK PATH CORRETO:
- Box é importado lazily dentro das funções (from control.models import Box).
  Patch em 'control.models.Box' intercepta o import corretamente.
- _run_step é definido no módulo, então 'control.services._run_step' funciona.
"""

from __future__ import annotations

import unittest
from unittest.mock import patch, MagicMock

from django.test import TestCase, SimpleTestCase


# ---------------------------------------------------------------------------
# L1 — derive_slug (puro, sem banco)
# ---------------------------------------------------------------------------

class DeriveSlugTest(SimpleTestCase):
    """Testa derive_slug sem tocar no banco."""

    # Box é importado dentro da função — patch no ponto de definição original.
    @patch('control.models.Box')
    def test_returns_base_slug_when_no_collision(self, MockBox):
        MockBox.objects.filter.return_value.exists.return_value = False
        from control.services import derive_slug

        slug = derive_slug('Minha Academia')

        self.assertEqual(slug, 'minha-academia')

    @patch('control.models.Box')
    def test_appends_suffix_2_on_first_collision(self, MockBox):
        MockBox.objects.filter.return_value.exists.side_effect = [True, False]
        from control.services import derive_slug

        slug = derive_slug('Minha Academia')

        self.assertEqual(slug, 'minha-academia-2')

    @patch('control.models.Box')
    def test_increments_suffix_on_multiple_collisions(self, MockBox):
        # base, base-2, base-3 colidem; base-4 livre
        MockBox.objects.filter.return_value.exists.side_effect = [
            True, True, True, False
        ]
        from control.services import derive_slug

        slug = derive_slug('box')

        self.assertEqual(slug, 'box-4')

    @patch('control.models.Box')
    def test_empty_name_produces_box_fallback(self, MockBox):
        MockBox.objects.filter.return_value.exists.return_value = False
        from control.services import derive_slug

        slug = derive_slug('')

        self.assertEqual(slug, 'box')

    @patch('control.models.Box')
    def test_long_name_truncated_to_max_59_chars(self, MockBox):
        MockBox.objects.filter.return_value.exists.return_value = False
        from control.services import derive_slug

        slug = derive_slug('a' * 100)

        self.assertLessEqual(len(slug), 59)  # 55 base + '-NNN' max

    @patch('control.models.Box')
    def test_generated_slug_matches_slug_re(self, MockBox):
        MockBox.objects.filter.return_value.exists.return_value = False
        from control.services import derive_slug, SLUG_RE

        slug = derive_slug('Academia de CrossFit & Yoga 2025!')

        self.assertRegex(slug, SLUG_RE)

    @patch('control.models.Box')
    def test_raises_value_error_after_999_collisions(self, MockBox):
        MockBox.objects.filter.return_value.exists.return_value = True  # sempre colide
        from control.services import derive_slug

        with self.assertRaises(ValueError) as ctx:
            derive_slug('academia')

        self.assertIn('999', str(ctx.exception))


# ---------------------------------------------------------------------------
# L2 — provision_box e reprovision_box
# ---------------------------------------------------------------------------

class ProvisionBoxTest(TestCase):
    """
    Testa orquestração de provision_box com _run_step mockado.
    Usa banco real (SQLite) para verificar criação de Box, Membership,
    BoxProvisioningEvent e lógica de idempotência.
    """

    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.owner = User.objects.create_user(
            username='owner_provision_test',
            email='owner@provision.test',
        )

    def _provision(self, slug='academia-teste', display_name='Academia Teste',
                   pending_signup=None, mock_run_step=None):
        """Helper que provisiona um Box com _run_step mockado."""
        from control.services import provision_box
        return provision_box(
            owner_user=self.owner,
            display_name=display_name,
            slug=slug,
            pending_signup=pending_signup,
        )

    @patch('control.services._run_step')
    def test_box_is_active_after_all_steps_complete(self, mock_step):
        from control.models import Box
        mock_step.return_value = None

        box = self._provision()

        box.refresh_from_db()
        self.assertEqual(box.status, Box.Status.ACTIVE)

    @patch('control.services._run_step')
    def test_schema_name_derived_from_slug(self, mock_step):
        mock_step.return_value = None

        box = self._provision(slug='minha-academia')

        self.assertEqual(box.schema_name, 'box_minha-academia')

    @patch('control.services._run_step')
    def test_owner_membership_created_with_owner_role(self, mock_step):
        from control.models import Membership
        mock_step.return_value = None

        box = self._provision()

        membership = Membership.objects.filter(user=self.owner, box=box).first()
        self.assertIsNotNone(membership, 'Membership não foi criado')
        self.assertEqual(membership.role, Membership.Role.OWNER)
        self.assertTrue(membership.is_primary_box)

    @patch('control.services._run_step')
    def test_idempotent_for_same_pending_signup(self, mock_step):
        """Segunda chamada com mesmo pending_signup retorna o mesmo Box."""
        from control.models import Box
        from signup.models import PendingSignup
        mock_step.return_value = None

        pending = PendingSignup.objects.create(
            email='idempotent@test.com',
        )

        box1 = self._provision(slug='academia-idem', pending_signup=pending)
        box2 = self._provision(slug='academia-idem', pending_signup=pending)

        self.assertEqual(box1.pk, box2.pk)
        self.assertEqual(Box.objects.filter(pending_signup=pending).count(), 1)

    def test_invalid_slug_raises_before_any_step(self):
        """Slug inválido (maiúsculo/especial) levanta ValueError sem criar nada."""
        from control.models import Box
        from control.services import provision_box

        with self.assertRaises(ValueError) as ctx:
            provision_box(
                owner_user=self.owner,
                display_name='X',
                slug='SLUG_INVALIDO',
            )

        self.assertIn('Slug inválido', str(ctx.exception))
        self.assertEqual(Box.objects.filter(slug='SLUG_INVALIDO').count(), 0)

    @patch('control.services._run_step')
    def test_all_provisioning_steps_get_ok_event(self, mock_step):
        from control.models import BoxProvisioningEvent
        from control.services import PROVISIONING_STEPS
        mock_step.return_value = None

        box = self._provision(slug='academia-events')

        ok_steps = set(
            BoxProvisioningEvent.objects.filter(box=box, status='ok')
            .values_list('step', flat=True)
        )
        self.assertEqual(ok_steps, set(PROVISIONING_STEPS))

    @patch('control.services._run_step')
    def test_failed_step_creates_failed_event_and_reraises(self, mock_step):
        from control.models import BoxProvisioningEvent
        mock_step.side_effect = RuntimeError('DDL falhou')

        with self.assertRaises(RuntimeError):
            self._provision(slug='academia-falha')

        failed_evt = BoxProvisioningEvent.objects.filter(status='failed').first()
        self.assertIsNotNone(failed_evt, 'Evento de falha não foi criado')
        self.assertIn('DDL falhou', failed_evt.detail)

    @patch('control.services._run_step')
    def test_reprovision_skips_completed_steps(self, mock_step):
        """Steps com evento 'ok' NÃO são re-executados no reprovision."""
        from control.models import Box, BoxProvisioningEvent
        from control.services import reprovision_box
        mock_step.return_value = None

        box = self._provision(slug='academia-reprov')

        # Simula interrupção: seed_plans voltou para failed
        BoxProvisioningEvent.objects.filter(
            box=box, step='seed_plans'
        ).update(status='failed')
        Box.objects.filter(pk=box.pk).update(status=Box.Status.PROVISIONING)
        box.refresh_from_db()
        mock_step.reset_mock()

        reprovision_box(box)

        called_steps = [c.args[0] for c in mock_step.call_args_list]
        self.assertIn('seed_plans', called_steps)
        self.assertNotIn('create_schema', called_steps)
        self.assertNotIn('migrate', called_steps)
        self.assertNotIn('bootstrap_roles', called_steps)


# ---------------------------------------------------------------------------
# L3 — archive_box (requer PostgreSQL — skip em SQLite)
# ---------------------------------------------------------------------------

class ArchiveBoxTest(TestCase):
    """
    archive_box usa ALTER SCHEMA RENAME — DDL real que só existe em PostgreSQL.
    Em SQLite: testa apenas a lógica de short-circuit (box já ARCHIVED).
    Em PostgreSQL: testa o rename completo.
    """

    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.owner = User.objects.create_user(
            username='owner_archive_test',
            email='owner@archive.test',
        )

    @patch('control.services._run_step')
    def _make_active_box(self, mock_step):
        mock_step.return_value = None
        from control.services import provision_box
        return provision_box(
            owner_user=self.owner,
            display_name='Academia Arquivo',
            slug='academia-arquivo',
        )

    def test_already_archived_box_is_returned_unchanged(self):
        """archive_box em box já ARCHIVED é noop — não levanta exceção."""
        from control.models import Box
        from control.services import archive_box

        box = self._make_active_box()
        Box.objects.filter(pk=box.pk).update(status=Box.Status.ARCHIVED)
        box.refresh_from_db()

        result = archive_box(box, reason='noop test')

        self.assertEqual(result.status, Box.Status.ARCHIVED)

    def test_archive_box_changes_status_to_archived_on_postgres(self):
        """Em PostgreSQL: status muda para ARCHIVED após rename do schema."""
        from django.db import connection
        if connection.vendor != 'postgresql':
            self.skipTest('Requer PostgreSQL com django-tenants')

        from control.models import Box
        from control.services import archive_box

        box = self._make_active_box()
        result = archive_box(box, reason='ci-test')

        result.refresh_from_db()
        self.assertEqual(result.status, Box.Status.ARCHIVED)
        self.assertTrue(result.schema_name.startswith('archived_box_'))


if __name__ == '__main__':
    unittest.main()
