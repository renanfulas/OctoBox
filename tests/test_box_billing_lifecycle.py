"""
ARQUIVO: testes do ciclo de vida de billing do Box e do unarchive.

POR QUE EXISTE:
Cobre os dois buracos fechados nesta mudanca e as guardas que os fecham:

1. customer.subscription.deleted nao tinha handler — cliente cancelava no Stripe
   e seguia usando o box de graca, indefinidamente.
2. archive_box nao tinha volta — offboarding era porta de mao unica.

E, sobretudo, as guardas que impedem que o remedio vire brecha nova:
- evento fora de ordem nao ressuscita box cancelado (o cenario mais perigoso:
  a Stripe nao garante ordem e o nosso retry sweep reentrega por design);
- customer_id ambiguo nao suspende box arbitrario;
- ARCHIVED e intocavel por webhook;
- unarchive nunca sobrescreve schema vivo e nunca devolve ACTIVE.

@pytest.mark.public_schema: Box/Membership/PlatformAuditEvent vivem em public,
que e onde o webhook roda de verdade.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone as dt_timezone

import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase

from control.models import Box, PlatformAuditEvent
from integrations.stripe.models import PaymentWebhookEvent, PaymentWebhookStatus
from integrations.stripe.router import route_payment_webhook_event

BASE_TS = 1_760_000_000  # relogio de referencia da Stripe nestes testes


def _billing_event(*, event_id, event_type, obj, created=BASE_TS):
    """Cria o envelope como a Stripe entrega: `created` no topo, objeto em data."""
    return PaymentWebhookEvent.objects.create(
        event_id=event_id,
        event_type=event_type,
        payload={
            'id': event_id,
            'type': event_type,
            'created': created,
            'data': {'object': obj},
        },
    )


def _as_utc(ts: int):
    return datetime.fromtimestamp(ts, tz=dt_timezone.utc)


@pytest.mark.public_schema
class BoxBillingLifecycleTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(
            username='owner-billing', email='owner@example.com', password='x'
        )

    def _box(self, *, slug='billing-box', status=Box.Status.ACTIVE, subscription='sub_live',
             customer='cus_live', billing_event_at=None):
        return Box.objects.create(
            slug=slug,
            schema_name=f'box_{slug}',
            display_name=slug,
            status=status,
            owner_user=self.owner,
            stripe_subscription_id=subscription,
            stripe_customer_id=customer,
            billing_event_at=billing_event_at,
        )

    # ── cancelamento ────────────────────────────────────────────────────────

    def test_subscription_deleted_suspends_active_box(self):
        box = self._box()

        event = _billing_event(
            event_id='evt_cancel',
            event_type='customer.subscription.deleted',
            obj={'id': 'sub_live', 'customer': 'cus_live'},
        )
        route_payment_webhook_event(event)

        box.refresh_from_db()
        event.refresh_from_db()
        self.assertEqual(box.status, Box.Status.SUSPENDED)
        self.assertIsNotNone(box.suspended_at)
        self.assertEqual(event.status, PaymentWebhookStatus.PROCESSED)
        self.assertTrue(
            PlatformAuditEvent.objects.filter(
                target_box=box, kind='box.suspended_subscription_canceled'
            ).exists()
        )

    def test_invoice_payment_failed_suspends_active_box(self):
        """Inadimplencia suspende o box — com banco real, sem mock de queryset.

        Existe uma versao com mock em tests/test_tenant_boundary.py (B12). Esta
        aqui e a contraparte comportamental: se a forma da query mudar de novo,
        este teste continua valendo e o outro quebra — e e este que diz a verdade.
        """
        box = self._box()

        event = _billing_event(
            event_id='evt_inadimplencia',
            event_type='invoice.payment_failed',
            obj={'subscription': 'sub_live', 'customer': 'cus_live'},
        )
        route_payment_webhook_event(event)

        box.refresh_from_db()
        self.assertEqual(box.status, Box.Status.SUSPENDED)
        self.assertIsNotNone(box.suspended_at)
        self.assertTrue(
            PlatformAuditEvent.objects.filter(
                target_box=box, kind='box.suspended_payment_failed'
            ).exists()
        )

    def test_subscription_deleted_resolves_by_id_not_by_subscription_field(self):
        """Em customer.subscription.*, o id da assinatura e object.id (nao object.subscription)."""
        box = self._box(subscription='sub_only_here', customer='')

        event = _billing_event(
            event_id='evt_cancel_by_id',
            event_type='customer.subscription.deleted',
            obj={'id': 'sub_only_here'},
        )
        route_payment_webhook_event(event)

        box.refresh_from_db()
        self.assertEqual(box.status, Box.Status.SUSPENDED)

    def test_subscription_deleted_never_touches_archived_box(self):
        box = self._box(status=Box.Status.ARCHIVED)
        box.schema_name = 'archived_box_billing-box_20260101000000'
        box.save(update_fields=['schema_name'])

        event = _billing_event(
            event_id='evt_cancel_archived',
            event_type='customer.subscription.deleted',
            obj={'id': 'sub_live', 'customer': 'cus_live'},
        )
        route_payment_webhook_event(event)

        box.refresh_from_db()
        self.assertEqual(box.status, Box.Status.ARCHIVED)
        self.assertEqual(box.schema_name, 'archived_box_billing-box_20260101000000')

    # ── guarda de ordenacao: o cenario da ressurreicao ──────────────────────

    def test_late_payment_succeeded_does_not_resurrect_canceled_box(self):
        """O bug que a guarda existe para impedir.

        Ordem real: pagamento OK (T0) -> cancelamento (T1). Se o payment_succeeded
        de T0 for reentregue DEPOIS do cancelamento — retry da Stripe ou nosso
        proprio sweep — sem guarda ele reativa um box que nao paga mais.
        """
        box = self._box()

        cancel = _billing_event(
            event_id='evt_cancel_first',
            event_type='customer.subscription.deleted',
            obj={'id': 'sub_live', 'customer': 'cus_live'},
            created=BASE_TS + 100,
        )
        route_payment_webhook_event(cancel)
        box.refresh_from_db()
        self.assertEqual(box.status, Box.Status.SUSPENDED)

        # Evento ANTERIOR chegando atrasado.
        stale = _billing_event(
            event_id='evt_paid_stale',
            event_type='invoice.payment_succeeded',
            obj={'subscription': 'sub_live', 'customer': 'cus_live'},
            created=BASE_TS,
        )
        route_payment_webhook_event(stale)

        box.refresh_from_db()
        self.assertEqual(
            box.status, Box.Status.SUSPENDED,
            'evento fora de ordem reativou box cancelado — guarda de ordenacao falhou',
        )

    def test_newer_payment_succeeded_does_reactivate(self):
        """Contraprova: um pagamento POSTERIOR ao cancelamento reativa normalmente."""
        box = self._box(status=Box.Status.SUSPENDED, billing_event_at=_as_utc(BASE_TS + 100))

        event = _billing_event(
            event_id='evt_paid_fresh',
            event_type='invoice.payment_succeeded',
            obj={'subscription': 'sub_live', 'customer': 'cus_live'},
            created=BASE_TS + 200,
        )
        route_payment_webhook_event(event)

        box.refresh_from_db()
        self.assertEqual(box.status, Box.Status.ACTIVE)
        self.assertIsNone(box.suspended_at)

    # ── reconexao inteligente ───────────────────────────────────────────────

    def test_resubscribe_rebinds_new_subscription_id(self):
        """Cliente cancela e assina DE NOVO: a assinatura nova tem outro id.

        O box e resolvido pelo customer_id e o ponteiro precisa religar, senao
        no ciclo seguinte o box fica orfao apontando para assinatura morta.
        """
        box = self._box(status=Box.Status.SUSPENDED, subscription='sub_antiga')

        event = _billing_event(
            event_id='evt_resubscribe',
            event_type='invoice.payment_succeeded',
            obj={'subscription': 'sub_nova', 'customer': 'cus_live'},
            created=BASE_TS + 500,
        )
        route_payment_webhook_event(event)

        box.refresh_from_db()
        self.assertEqual(box.stripe_subscription_id, 'sub_nova')
        self.assertEqual(box.status, Box.Status.ACTIVE)
        self.assertTrue(
            PlatformAuditEvent.objects.filter(
                target_box=box, kind='billing.subscription_rebound'
            ).exists()
        )

    def test_active_box_does_not_get_pointer_hijacked(self):
        """Box ACTIVE recebendo cobranca de outra assinatura do mesmo customer.

        Nao pode religar o ponteiro: se o cliente tiver duas assinaturas na
        Stripe, isso deixaria a errada mandando no box. Registra e nao altera.
        """
        box = self._box(status=Box.Status.ACTIVE, subscription='sub_do_box')

        event = _billing_event(
            event_id='evt_outra_assinatura',
            event_type='invoice.payment_succeeded',
            obj={'subscription': 'sub_de_outra_coisa', 'customer': 'cus_live'},
            created=BASE_TS + 300,
        )
        route_payment_webhook_event(event)

        box.refresh_from_db()
        self.assertEqual(box.stripe_subscription_id, 'sub_do_box')
        self.assertEqual(box.status, Box.Status.ACTIVE)
        self.assertTrue(
            PlatformAuditEvent.objects.filter(
                target_box=box, kind='billing.subscription_mismatch'
            ).exists()
        )

    def test_payment_on_archived_box_is_audited_not_silent(self):
        """Dinheiro entrando para box arquivado nao pode sumir sem registro."""
        box = self._box(status=Box.Status.ARCHIVED)

        event = _billing_event(
            event_id='evt_paid_archived',
            event_type='invoice.payment_succeeded',
            obj={'subscription': 'sub_live', 'customer': 'cus_live'},
        )
        route_payment_webhook_event(event)

        box.refresh_from_db()
        self.assertEqual(box.status, Box.Status.ARCHIVED)
        self.assertTrue(
            PlatformAuditEvent.objects.filter(
                target_box=box, kind='billing.payment_on_archived_box'
            ).exists()
        )

    # ── ambiguidade falha fechado ───────────────────────────────────────────

    def test_ambiguous_customer_suspends_nothing(self):
        """Mesmo customer_id em dois boxes: recusar agir e melhor que chutar."""
        box_a = self._box(slug='box-a', subscription='sub_a')
        box_b = self._box(slug='box-b', subscription='sub_b')

        event = _billing_event(
            event_id='evt_ambiguo',
            event_type='customer.subscription.deleted',
            obj={'id': 'sub_desconhecida', 'customer': 'cus_live'},
        )
        route_payment_webhook_event(event)

        box_a.refresh_from_db()
        box_b.refresh_from_db()
        self.assertEqual(box_a.status, Box.Status.ACTIVE)
        self.assertEqual(box_b.status, Box.Status.ACTIVE)

    def test_unknown_subscription_is_noop_and_processed(self):
        """Assinatura que nao e nossa: no-op, mas o evento fecha como processado."""
        event = _billing_event(
            event_id='evt_desconhecida',
            event_type='customer.subscription.deleted',
            obj={'id': 'sub_de_outra_conta', 'customer': 'cus_de_outra_conta'},
        )
        route_payment_webhook_event(event)

        event.refresh_from_db()
        self.assertEqual(event.status, PaymentWebhookStatus.PROCESSED)


@pytest.mark.public_schema
class UnarchiveBoxGuardTests(TestCase):
    """Guardas do unarchive_box que nao dependem de DDL real."""

    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(
            username='owner-unarchive', email='unarchive@example.com', password='x'
        )

    def _box(self, **kwargs):
        defaults = {
            'slug': 'restaurar',
            'schema_name': 'box_restaurar',
            'display_name': 'Restaurar',
            'status': Box.Status.ARCHIVED,
            'owner_user': self.owner,
        }
        defaults.update(kwargs)
        return Box.objects.create(**defaults)

    def test_rejects_box_that_is_not_archived(self):
        from control.services import unarchive_box

        box = self._box(status=Box.Status.ACTIVE)
        with self.assertRaises(ValueError) as ctx:
            unarchive_box(box)
        self.assertIn('não ARCHIVED', str(ctx.exception))

    def test_rejects_schema_name_that_is_not_an_archived_name(self):
        """Box ARCHIVED cujo schema_name nao tem forma de arquivado: nao renomear.

        Renomear as cegas aqui poderia mover um schema vivo.
        """
        from control.services import unarchive_box

        box = self._box(schema_name='box_restaurar')
        with self.assertRaises(ValueError) as ctx:
            unarchive_box(box)
        self.assertIn('forma de schema', str(ctx.exception))

    def test_rejects_hostile_schema_name(self):
        from control.services import unarchive_box

        box = self._box(schema_name='archived_box_x"; DROP SCHEMA public; --_20260101000000')
        with self.assertRaises(ValueError):
            unarchive_box(box)

    def test_validate_schema_ident_rejects_injection_shapes(self):
        from control.services import _validate_schema_ident

        for hostil in [
            'box_a"; DROP SCHEMA public; --',
            'box a',
            'BOX_MAIUSCULO',
            'public.box_a',
            '',
            None,
            'x' * 64,
        ]:
            with self.assertRaises(ValueError):
                _validate_schema_ident(hostil)

    def test_validate_schema_ident_accepts_real_names(self):
        from control.services import _validate_schema_ident

        for ok in ['box_pilot', 'box_cross-fit-sp', 'archived_box_pilot_20260101000000']:
            self.assertEqual(_validate_schema_ident(ok), ok)


@pytest.mark.public_schema
@pytest.mark.requires_postgres
class UnarchiveBoxRoundTripTests(TestCase):
    """Ida e volta real: provisiona schema, arquiva, restaura."""

    def setUp(self):
        from django.db import connection

        if connection.vendor != 'postgresql':
            self.skipTest('Requer PostgreSQL com django-tenants')

        user_model = get_user_model()
        self.owner = user_model.objects.create_user(
            username='owner-roundtrip', email='roundtrip@example.com', password='x'
        )

    def _schema_exists(self, name):
        from django.db import connections
        from django_tenants.utils import get_tenant_database_alias

        with connections[get_tenant_database_alias()].cursor() as cursor:
            cursor.execute(
                'SELECT 1 FROM information_schema.schemata WHERE schema_name = %s', [name]
            )
            return cursor.fetchone() is not None

    def test_archive_then_unarchive_restores_schema_and_suspends(self):
        from django.db import connections
        from django_tenants.utils import get_tenant_database_alias

        from control.services import archive_box, unarchive_box

        slug = 'roundtrip'
        box = Box.objects.create(
            slug=slug,
            schema_name=f'box_{slug}',
            display_name='Round Trip',
            status=Box.Status.ACTIVE,
            owner_user=self.owner,
        )
        with connections[get_tenant_database_alias()].cursor() as cursor:
            cursor.execute(f'CREATE SCHEMA IF NOT EXISTS "box_{slug}"')
        self.addCleanup(self._drop_schemas, slug)

        box = archive_box(box, reason='teste')
        self.assertEqual(box.status, Box.Status.ARCHIVED)
        self.assertTrue(box.schema_name.startswith('archived_box_'))
        self.assertFalse(self._schema_exists(f'box_{slug}'))
        archived_name = box.schema_name

        box = unarchive_box(box, reason='cliente voltou')

        self.assertEqual(box.schema_name, f'box_{slug}')
        self.assertTrue(self._schema_exists(f'box_{slug}'))
        self.assertFalse(self._schema_exists(archived_name))
        self.assertIsNone(box.archived_at)
        # SUSPENDED, nao ACTIVE: restaurar dados nao e liberar acesso.
        self.assertEqual(box.status, Box.Status.SUSPENDED)
        self.assertTrue(
            PlatformAuditEvent.objects.filter(target_box=box, kind='box.unarchived').exists()
        )

    def test_unarchive_refuses_when_destination_schema_already_exists(self):
        from django.db import connections
        from django_tenants.utils import get_tenant_database_alias

        from control.services import archive_box, unarchive_box

        slug = 'colisao'
        box = Box.objects.create(
            slug=slug,
            schema_name=f'box_{slug}',
            display_name='Colisao',
            status=Box.Status.ACTIVE,
            owner_user=self.owner,
        )
        alias = get_tenant_database_alias()
        with connections[alias].cursor() as cursor:
            cursor.execute(f'CREATE SCHEMA IF NOT EXISTS "box_{slug}"')
        self.addCleanup(self._drop_schemas, slug)

        box = archive_box(box, reason='teste')
        archived_name = box.schema_name

        # Alguem recriou box_<slug> enquanto o original estava arquivado.
        with connections[alias].cursor() as cursor:
            cursor.execute(f'CREATE SCHEMA "box_{slug}"')

        with self.assertRaises(ValueError) as ctx:
            unarchive_box(box)
        self.assertIn('JÁ EXISTE', str(ctx.exception))

        # Nenhum dos dois lados foi tocado.
        self.assertTrue(self._schema_exists(archived_name))
        self.assertTrue(self._schema_exists(f'box_{slug}'))
        box.refresh_from_db()
        self.assertEqual(box.status, Box.Status.ARCHIVED)

    def _drop_schemas(self, slug):
        from django.db import connections
        from django_tenants.utils import get_tenant_database_alias

        alias = get_tenant_database_alias()
        with connections[alias].cursor() as cursor:
            cursor.execute(
                "SELECT schema_name FROM information_schema.schemata "
                "WHERE schema_name = %s OR schema_name LIKE %s",
                [f'box_{slug}', f'archived_box_{slug}_%'],
            )
            names = [row[0] for row in cursor.fetchall()]
            for name in names:
                cursor.execute(f'DROP SCHEMA IF EXISTS "{name}" CASCADE')
