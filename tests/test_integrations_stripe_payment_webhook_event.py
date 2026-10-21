"""
ARQUIVO: teste de regressao do payload de PaymentWebhookEvent com Decimal
(fix #309 — integrations/stripe/models.py).

POR QUE ELE EXISTE:
- stripe.Event.to_dict() devolve Decimal em campos de eventos de invoice
  (unit_amount_decimal, quantity_decimal). Sem encoder=DjangoJSONEncoder no
  JSONField de `payload`, salvar esse payload levanta ValidationError (via
  full_clean) ou TypeError (via json.dumps direto no INSERT) — e esse erro
  acontecia ANTES de qualquer logica de negocio rodar, tanto no webhook do
  box (/financeiro/) quanto no do corredor Curva (/treinos/), porque os
  dois reusam este MESMO modelo (SHARED, app_label=integrations).
- Achado em producao: uma assinante pagou (Stripe confirmou), o evento
  invoice.payment_succeeded nunca foi persistido por causa deste bug, a
  assinatura nunca ativou e nenhum e-mail saiu. O fix (encoder=
  DjangoJSONEncoder) nao tinha teste nenhum — este arquivo cobre isso.
"""

from __future__ import annotations

from decimal import Decimal

from django.test import TestCase

from integrations.stripe.models import PaymentWebhookEvent


class PaymentWebhookEventDecimalPayloadTests(TestCase):
    def test_saves_a_payload_with_decimal_values_in_nested_fields(self):
        # Formato real de invoice.payment_succeeded (stripe-python 15.x):
        # lines.data[].pricing.unit_amount_decimal e quantity_decimal
        # chegam como Decimal, nao str/float, depois de .to_dict().
        payload = {
            'id': 'evt_decimal_1',
            'type': 'invoice.payment_succeeded',
            'data': {
                'object': {
                    'id': 'in_123',
                    'lines': {
                        'data': [
                            {
                                'pricing': {'unit_amount_decimal': Decimal('9700')},
                                'quantity_decimal': Decimal('1'),
                            },
                        ],
                    },
                },
            },
        }

        event = PaymentWebhookEvent.objects.create(
            event_id='evt_decimal_1', event_type='invoice.payment_succeeded', payload=payload,
        )

        event.refresh_from_db()
        line = event.payload['data']['object']['lines']['data'][0]
        # DjangoJSONEncoder serializa Decimal como string -- nunca float
        # (perderia precisao de centavos), nunca o objeto Decimal cru (JSON
        # nao tem esse tipo).
        self.assertEqual(line['pricing']['unit_amount_decimal'], '9700')
        self.assertEqual(line['quantity_decimal'], '1')

    def test_full_clean_accepts_decimal_in_payload(self):
        # O bug real acontecia tanto no INSERT quanto na validacao
        # (full_clean, chamada por algumas rotas de save) -- cobre as duas.
        event = PaymentWebhookEvent(
            event_id='evt_decimal_2',
            event_type='invoice.payment_succeeded',
            payload={'amount': Decimal('197.90')},
        )

        event.full_clean()
