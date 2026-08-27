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

import pytest
from unittest.mock import patch, MagicMock

from django.test import TestCase, SimpleTestCase, override_settings


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

@pytest.mark.public_schema
class ProvisionBoxTest(TestCase):
    """
    Testa orquestração de provision_box com _run_step mockado.

    @pytest.mark.public_schema (Sprint 9): roda no schema public. provision_box
    cria um Box (modelo tenant do django-tenants) — proibido fora do public.
    Sem o marker, o conftest força schema_context('box_test') e o CI quebra com
    "Can't create tenant outside the public schema".
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
# L2 — reprovision_box NÃO reativa SUSPENDED/ARCHIVED (Onda 2, 2026-08-25)
#
# Antes: reprovision_box fazia `Box.objects.filter(pk=box.pk).update(status=ACTIVE)`
# incondicional — rodar o comando num box suspenso por inadimplência (ou por
# customer.subscription.deleted) devolvia acesso sem passar por pagamento.
# Estes testes são o gate de saída da onda: (1) SUSPENDED continua SUSPENDED
# e o attach/audit do superdev continuam rodando (não é um early-return que
# mataria a cura tardia do ADR-013); (2) activate_box reativa manualmente
# com reason obrigatório e audit.
# ---------------------------------------------------------------------------

@pytest.mark.public_schema
class ReprovisionBoxDoesNotBypassBillingTest(TestCase):
    """Gate de saída da Onda 2."""

    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.owner = User.objects.create_user(
            username='owner_reprov_billing_test',
            email='owner@reprov-billing.test',
        )

    @patch('control.services._run_step')
    def _active_box(self, mock_step, slug='billing-guard'):
        from control.services import provision_box
        mock_step.return_value = None
        return provision_box(owner_user=self.owner, display_name=slug, slug=slug)

    @patch('control.services._run_step')
    def test_reprovision_does_not_promote_suspended_box(self, mock_step):
        """Item (1) do gate: box SUSPENDED continua SUSPENDED após reprovision_box.

        Este é o teste que faltava e que teria pego a regressão original —
        `test_reprovision_skips_completed_steps` (pré-existente) só cobria
        idempotência de steps, nunca colocava o box em SUSPENDED antes de
        chamar reprovision_box.
        """
        from control.models import Box
        from control.services import reprovision_box
        mock_step.return_value = None

        box = self._active_box(slug='billing-guard-suspended')
        Box.objects.filter(pk=box.pk).update(status=Box.Status.SUSPENDED)
        box.refresh_from_db()
        self.assertEqual(box.status, Box.Status.SUSPENDED)
        provisioned_at_antes = box.provisioned_at  # já setado pelo provision_box inicial

        result = reprovision_box(box)

        result.refresh_from_db()
        self.assertEqual(
            result.status, Box.Status.SUSPENDED,
            'reprovision_box promoveu um box SUSPENDED para ACTIVE — '
            'o portão de billing foi contornado.',
        )
        self.assertEqual(
            result.provisioned_at, provisioned_at_antes,
            'provisioned_at foi re-carimbado mesmo sem promoção — o UPDATE condicional disparou.',
        )

    @patch('control.services._run_step')
    def test_reprovision_does_not_promote_archived_box(self, mock_step):
        from control.models import Box
        from control.services import reprovision_box
        mock_step.return_value = None

        box = self._active_box(slug='billing-guard-archived')
        Box.objects.filter(pk=box.pk).update(status=Box.Status.ARCHIVED)
        box.refresh_from_db()

        result = reprovision_box(box)

        result.refresh_from_db()
        self.assertEqual(result.status, Box.Status.ARCHIVED)

    @patch('control.services._run_step')
    def test_reprovision_still_cures_missing_superdev_membership_on_suspended_box(self, mock_step):
        """Item (2) do gate: a cura do ADR-013 (attach de superdev) não pode
        morrer como efeito colateral da guarda — early-return mataria isso.

        Cenário: box foi provisionado ANTES do superdev existir (Membership
        do superdev nunca foi criado — falha de proposito, ver ADR-013),
        depois foi suspenso por billing, depois o superdev passou a existir.
        reprovision_box deve anexar o superdev mesmo sem promover o status.
        """
        from django.conf import settings
        from django.contrib.auth import get_user_model
        from control.models import Box, Membership
        from control.services import reprovision_box
        mock_step.return_value = None

        box = self._active_box(slug='billing-guard-superdev-cure')
        Box.objects.filter(pk=box.pk).update(status=Box.Status.SUSPENDED)
        box.refresh_from_db()

        superdev_username = getattr(settings, 'SUPERDEV_USERNAME', 'superdev') or 'superdev'
        User = get_user_model()
        superdev = User.objects.create_user(
            username=superdev_username,
            email='superdev@octobox.test',
            is_active=True,
        )
        self.assertFalse(
            Membership.objects.filter(user=superdev, box=box).exists(),
            'setup invalido: superdev ja tinha Membership antes do reprovision',
        )

        reprovision_box(box)

        self.assertTrue(
            Membership.objects.filter(user=superdev, box=box, is_primary_box=False).exists(),
            'reprovision_box nao curou o Membership do superdev — a guarda de billing '
            'quebrou o chokepoint de cura que o ADR-013 exige.',
        )
        box.refresh_from_db()
        self.assertEqual(
            box.status, Box.Status.SUSPENDED,
            'a cura do superdev nao deveria, por si so, promover o box.',
        )


@pytest.mark.public_schema
class ActivateBoxTest(TestCase):
    """activate_box: reativação manual de SUSPENDED, reason obrigatório, audit."""

    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.owner = User.objects.create_user(
            username='owner_activate_test',
            email='owner@activate.test',
        )

    @patch('control.services._run_step')
    def _suspended_box(self, mock_step, slug='ativar-teste'):
        from control.models import Box
        from control.services import provision_box
        mock_step.return_value = None
        box = provision_box(owner_user=self.owner, display_name=slug, slug=slug)
        Box.objects.filter(pk=box.pk).update(status=Box.Status.SUSPENDED)
        box.refresh_from_db()
        return box

    def test_activates_suspended_box_with_reason(self):
        from control.models import Box, PlatformAuditEvent
        from control.services import activate_box

        box = self._suspended_box(slug='ativar-com-motivo')

        result = activate_box(box, reason='Cliente pagou por fora, confirmado com financeiro')

        result.refresh_from_db()
        self.assertEqual(result.status, Box.Status.ACTIVE)
        self.assertIsNone(result.suspended_at)
        self.assertTrue(
            PlatformAuditEvent.objects.filter(
                target_box=box, kind='box.activated_manual_support'
            ).exists()
        )

    def test_rejects_empty_reason(self):
        from control.models import Box
        from control.services import activate_box

        box = self._suspended_box(slug='ativar-sem-motivo')

        with self.assertRaises(ValueError) as ctx:
            activate_box(box, reason='')
        self.assertIn('reason', str(ctx.exception))

        box.refresh_from_db()
        self.assertEqual(box.status, Box.Status.SUSPENDED)

    def test_rejects_non_suspended_box(self):
        from control.models import Box
        from control.services import activate_box

        box = self._suspended_box(slug='ativar-ja-ativo')
        Box.objects.filter(pk=box.pk).update(status=Box.Status.ACTIVE)
        box.refresh_from_db()

        with self.assertRaises(ValueError) as ctx:
            activate_box(box, reason='motivo qualquer')
        self.assertIn('não SUSPENDED', str(ctx.exception))

    def test_rejects_archived_box(self):
        from control.models import Box
        from control.services import activate_box

        box = self._suspended_box(slug='ativar-arquivado')
        Box.objects.filter(pk=box.pk).update(status=Box.Status.ARCHIVED)
        box.refresh_from_db()

        with self.assertRaises(ValueError):
            activate_box(box, reason='motivo qualquer')


# ---------------------------------------------------------------------------
# L3 — archive_box (requer PostgreSQL — skip em SQLite)
# ---------------------------------------------------------------------------

@pytest.mark.public_schema
class ArchiveBoxTest(TestCase):
    """
    archive_box usa ALTER SCHEMA RENAME — DDL real que só existe em PostgreSQL.
    Em SQLite: testa apenas a lógica de short-circuit (box já ARCHIVED).
    Em PostgreSQL: testa o rename completo.

    @pytest.mark.public_schema (Sprint 9): cria Box via provision_box — public only.
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

        # _run_step está mockado em _make_active_box, então o schema físico
        # não foi criado. archive_box faz ALTER SCHEMA RENAME — o schema
        # precisa existir de verdade. Criamos só o schema (sem migrar tabelas).
        with connection.cursor() as cur:
            cur.execute(f'CREATE SCHEMA IF NOT EXISTS "{box.schema_name}"')

        # DDL de schema NÃO é transacional no Postgres — não é revertido pelo
        # rollback do TestCase. Limpamos explicitamente os schemas criados.
        def _drop_test_schemas():
            with connection.cursor() as c:
                c.execute(f'DROP SCHEMA IF EXISTS "{box.schema_name}" CASCADE')
                c.execute(
                    "SELECT schema_name FROM information_schema.schemata "
                    "WHERE schema_name LIKE 'archived_box_academia-arquivo%'"
                )
                for (name,) in c.fetchall():
                    c.execute(f'DROP SCHEMA IF EXISTS "{name}" CASCADE')
        self.addCleanup(_drop_test_schemas)

        result = archive_box(box, reason='ci-test')

        result.refresh_from_db()
        self.assertEqual(result.status, Box.Status.ARCHIVED)
        self.assertTrue(result.schema_name.startswith('archived_box_'))


# ---------------------------------------------------------------------------
# L2 — anexo automatico do superdev (conta de suporte) no provisionamento
# ---------------------------------------------------------------------------

@pytest.mark.public_schema
@override_settings(
    SUPERDEV_USERNAME='superdev',
    SUPERDEV_EMAIL='superdev@octoboxfit.com.br',
    SUPERDEV_AUTO_ATTACH=True,
)
class SuperdevAttachTest(TestCase):
    """Anexo automatico da conta de suporte (superdev) em provision/reprovision.

    @pytest.mark.public_schema: provision_box cria Box (modelo tenant) — so em public.
    _run_step mockado (sem DDL real); o foco e a orquestracao do Membership.
    """

    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.owner = User.objects.create_user(username='owner_sd_test', email='owner@sd.test')
        self.superdev = User.objects.create_user(
            username='superdev',
            email='superdev@octoboxfit.com.br',
            is_staff=True,
            is_superuser=True,
        )

    def _provision(self, slug='academia-sd', pending_signup=None, owner=None):
        from control.services import provision_box
        return provision_box(
            owner_user=owner or self.owner,
            display_name='Academia SD',
            slug=slug,
            pending_signup=pending_signup,
        )

    @patch('control.services._run_step')
    def test_superdev_attached_as_owner_non_primary(self, mock_step):
        from control.models import Membership
        mock_step.return_value = None

        box = self._provision()

        sd = Membership.objects.filter(user=self.superdev, box=box).first()
        self.assertIsNotNone(sd, 'Superdev nao foi anexado ao box')
        self.assertEqual(sd.role, Membership.Role.OWNER)
        self.assertFalse(sd.is_primary_box, 'Superdev NAO pode ter is_primary_box=True')
        # Owner permanece como primary
        owner_m = Membership.objects.get(user=self.owner, box=box)
        self.assertTrue(owner_m.is_primary_box)

    @patch('control.services._run_step')
    def test_support_granted_audit_event_recorded(self, mock_step):
        from control.models import PlatformAuditEvent
        mock_step.return_value = None

        box = self._provision()

        self.assertTrue(
            PlatformAuditEvent.objects.filter(
                target_box=box, kind='membership.support_granted'
            ).exists()
        )

    @patch('control.services._run_step')
    def test_attach_is_idempotent_across_reprovision(self, mock_step):
        from control.models import Membership
        from control.services import reprovision_box
        mock_step.return_value = None

        box = self._provision()
        reprovision_box(box)
        reprovision_box(box)

        count = Membership.objects.filter(user=self.superdev, box=box).count()
        self.assertEqual(count, 1)

    @override_settings(SUPERDEV_AUTO_ATTACH=False)
    @patch('control.services._run_step')
    def test_kill_switch_disables_attach(self, mock_step):
        from control.models import Box, Membership
        mock_step.return_value = None

        box = self._provision(slug='academia-sd-off')

        self.assertFalse(Membership.objects.filter(user=self.superdev, box=box).exists())
        box.refresh_from_db()
        self.assertEqual(box.status, Box.Status.ACTIVE)  # provisionamento nao quebra

    @override_settings(SUPERDEV_USERNAME='nao-existe')
    @patch('control.services._run_step')
    def test_provision_succeeds_when_superdev_missing(self, mock_step):
        from control.models import Box, Membership
        mock_step.return_value = None

        box = self._provision(slug='academia-sd-missing')

        self.assertEqual(Membership.objects.filter(box=box).count(), 1)  # so o owner
        box.refresh_from_db()
        self.assertEqual(box.status, Box.Status.ACTIVE)

    @patch('control.services._run_step')
    def test_no_duplicate_when_superdev_is_owner(self, mock_step):
        from control.models import Membership
        mock_step.return_value = None

        box = self._provision(slug='box-do-superdev', owner=self.superdev)

        # Apenas a membership de owner — sem segunda membership duplicada
        self.assertEqual(Membership.objects.filter(user=self.superdev, box=box).count(), 1)
        owner_m = Membership.objects.get(user=self.superdev, box=box)
        self.assertTrue(owner_m.is_primary_box)


if __name__ == '__main__':
    unittest.main()
