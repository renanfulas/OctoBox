"""
ARQUIVO: testes do guardrail de valor de cobranca do corredor de treinos
(Onda B2 do CORDA — P8, critério de entrada da onda).

POR QUE ELE EXISTE:
- P8: "amount fora de faixa e recusado no SERVICO, nao so no form." Testa
  a funcao de servico direto, sem passar por nenhum form/view.
"""

from decimal import Decimal

from django.test import TestCase, override_settings

from public_workouts.billing import PublicWorkoutPaymentAmountError, validate_payment_amount


class PaymentAmountGuardrailTests(TestCase):
    def test_amount_within_default_range_is_accepted(self):
        validate_payment_amount(Decimal('89.90'))  # nao levanta

    def test_zero_amount_is_rejected(self):
        with self.assertRaises(PublicWorkoutPaymentAmountError):
            validate_payment_amount(Decimal('0.00'))

    def test_negative_amount_is_rejected(self):
        with self.assertRaises(PublicWorkoutPaymentAmountError):
            validate_payment_amount(Decimal('-10.00'))

    def test_absurdly_high_amount_is_rejected(self):
        with self.assertRaises(PublicWorkoutPaymentAmountError):
            validate_payment_amount(Decimal('999999.00'))

    def test_none_amount_is_rejected(self):
        with self.assertRaises(PublicWorkoutPaymentAmountError):
            validate_payment_amount(None)

    @override_settings(PUBLIC_WORKOUT_PAYMENT_MIN_AMOUNT='50.00', PUBLIC_WORKOUT_PAYMENT_MAX_AMOUNT='150.00')
    def test_range_is_configurable_via_settings(self):
        validate_payment_amount(Decimal('100.00'))  # nao levanta
        with self.assertRaises(PublicWorkoutPaymentAmountError):
            validate_payment_amount(Decimal('40.00'))
        with self.assertRaises(PublicWorkoutPaymentAmountError):
            validate_payment_amount(Decimal('160.00'))
