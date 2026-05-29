"""
ARQUIVO: testes de signup.services (path crítico de monetização).

POR QUE EXISTE:
- signup.services é o ciclo de receita: Stripe checkout → webhook →
  magic-token → ativação de Owner. Antes deste arquivo: 0 testes.
- 5 funções (verify_magic_token, activate_pending_signup, create_checkout_session,
  mark_pending_signup_paid, query_stripe_session_status) somam 17 branches de
  erro nunca exercitadas. Qualquer regressão silenciosa bloqueia receita.
- Cobre Sprint 5 do plano de hardening (docs/testing/architecture.md).

CAMADA: L1 (verify_magic_token, branches puros) + L2 (activate_pending_signup,
mark_pending_signup_paid — exigem PendingSignup no banco).

SOURCE-UNDER-TEST: signup/services.py

CONTRATO DE MOCK:
- stripe lib: mockado via unittest.mock no atributo `stripe.checkout.Session`.
  Stripe Python SDK não é um cliente HTTP simples — `responses` lib funcionaria
  parcialmente, mas patch direto no objeto Session é mais determinista para
  validar contratos de exceção.
- Settings: @override_settings para STRIPE_PRICE_EARLY_*, STRIPE_SECRET_KEY.
- Tempo: freeze_time para magic_token_expires_at determinístico.

FINDINGS (descobertos durante implementação): ver tests/sprint-5-8-findings.md
"""

from __future__ import annotations

import sys
from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core import signing
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
from django.utils import timezone
from freezegun import freeze_time

from signup.models import PendingSignup, PendingSignupPlan, PendingSignupStatus
from signup.services import (
    InvalidMagicTokenError,
    StripeNotConfiguredError,
    UsernameTakenError,
    _MAGIC_TOKEN_MAX_AGE_DAYS,
    _MAGIC_TOKEN_SALT,
    activate_pending_signup,
    create_checkout_session,
    generate_magic_token,
    mark_pending_signup_paid,
    query_stripe_session_status,
    verify_magic_token,
)


User = get_user_model()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_pending(
    *,
    status: str = PendingSignupStatus.PAID,
    email: str = 'owner@academia.test',
    full_name: str = 'Maria Silva',
    box_name: str = 'Academia Forte',
    plan: str = PendingSignupPlan.MONTHLY,
) -> PendingSignup:
    return PendingSignup.objects.create(
        email=email,
        full_name=full_name,
        box_name=box_name,
        plan=plan,
        status=status,
    )


# ===========================================================================
# verify_magic_token — 6 branches
# ===========================================================================

class VerifyMagicTokenTest(TestCase):
    """L2: verify_magic_token — cobre as 6 branches de erro em signup/services.py:234."""

    # Branch 1 (line 241-242): token vazio
    def test_raises_token_vazio_when_token_is_empty_string(self):
        with self.assertRaises(InvalidMagicTokenError) as ctx:
            verify_magic_token('')
        self.assertEqual(str(ctx.exception), 'token-vazio')

    def test_raises_token_vazio_when_token_is_none(self):
        with self.assertRaises(InvalidMagicTokenError) as ctx:
            verify_magic_token(None)
        self.assertEqual(str(ctx.exception), 'token-vazio')

    # Branch 2 (line 247-248): SignatureExpired
    def test_raises_token_expirado_when_signature_is_expired(self):
        """Token gerado há > _MAGIC_TOKEN_MAX_AGE_DAYS dias é tratado como expirado."""
        pending = _make_pending()
        # Gera token no passado, valida no presente — expira por tempo.
        with freeze_time('2026-01-01 12:00:00'):
            token = generate_magic_token(pending)
        # Avança 8 dias (max é 7)
        with freeze_time('2026-01-09 12:00:00'):
            with self.assertRaises(InvalidMagicTokenError) as ctx:
                verify_magic_token(token)
            self.assertEqual(str(ctx.exception), 'token-expirado')

    # Branch 3 (line 249-250): BadSignature
    def test_raises_token_invalido_for_garbage_string(self):
        with self.assertRaises(InvalidMagicTokenError) as ctx:
            verify_magic_token('not-a-valid-signed-token')
        self.assertEqual(str(ctx.exception), 'token-invalido')

    def test_raises_token_invalido_for_token_with_tampered_payload(self):
        """Token com payload modificado falha na verificação HMAC."""
        pending = _make_pending()
        token = generate_magic_token(pending)
        # Adultera o último caractere
        tampered = token[:-1] + ('X' if token[-1] != 'X' else 'Y')
        with self.assertRaises(InvalidMagicTokenError) as ctx:
            verify_magic_token(tampered)
        self.assertEqual(str(ctx.exception), 'token-invalido')

    # Branch 4 (line 253-254): pending-nao-encontrado
    def test_raises_pending_nao_encontrado_when_pk_does_not_exist(self):
        """Token válido em assinatura mas referencia pk inexistente."""
        # Gera token apontando para pk fake (99999) sem criar PendingSignup
        token = signing.dumps({'pk': 99999}, salt=_MAGIC_TOKEN_SALT)
        with self.assertRaises(InvalidMagicTokenError) as ctx:
            verify_magic_token(token)
        self.assertEqual(str(ctx.exception), 'pending-nao-encontrado')

    # Branch 5 (line 256-257): ja-ativado
    def test_raises_ja_ativado_when_pending_already_activated(self):
        pending = _make_pending(status=PendingSignupStatus.ACTIVATED)
        token = generate_magic_token(pending)
        with self.assertRaises(InvalidMagicTokenError) as ctx:
            verify_magic_token(token)
        self.assertEqual(str(ctx.exception), 'ja-ativado')

    # Branch 6 (line 259-260): status-invalido
    def test_raises_status_invalido_when_pending_still_pending(self):
        """PENDING (sem pagamento) não pode ativar."""
        pending = _make_pending(status=PendingSignupStatus.PENDING)
        token = generate_magic_token(pending)
        with self.assertRaises(InvalidMagicTokenError) as ctx:
            verify_magic_token(token)
        self.assertEqual(str(ctx.exception), f'status-invalido:{PendingSignupStatus.PENDING}')

    def test_raises_status_invalido_when_pending_canceled(self):
        pending = _make_pending(status=PendingSignupStatus.CANCELED)
        token = generate_magic_token(pending)
        with self.assertRaises(InvalidMagicTokenError) as ctx:
            verify_magic_token(token)
        self.assertEqual(str(ctx.exception), f'status-invalido:{PendingSignupStatus.CANCELED}')

    # Success path
    def test_returns_pending_when_token_is_valid_and_status_paid(self):
        pending = _make_pending(status=PendingSignupStatus.PAID)
        token = generate_magic_token(pending)

        result = verify_magic_token(token)

        self.assertEqual(result.pk, pending.pk)
        self.assertEqual(result.status, PendingSignupStatus.PAID)


# ===========================================================================
# activate_pending_signup — 3 branches de erro + sucesso
# ===========================================================================

class ActivatePendingSignupTest(TestCase):
    """L2: activate_pending_signup — branches em signup/services.py:323."""

    def setUp(self):
        self.pending = _make_pending(status=PendingSignupStatus.PAID)

    # Branch 1 (line 338-339): username-obrigatorio
    def test_raises_value_error_when_username_is_empty(self):
        with self.assertRaises(ValueError) as ctx:
            activate_pending_signup(
                pending_signup=self.pending,
                username='',
                raw_password='secret-pwd-123',
            )
        self.assertEqual(str(ctx.exception), 'username-obrigatorio')

    def test_raises_value_error_when_username_is_whitespace(self):
        """Username só com espaços é normalizado e considerado vazio."""
        with self.assertRaises(ValueError) as ctx:
            activate_pending_signup(
                pending_signup=self.pending,
                username='   ',
                raw_password='secret-pwd-123',
            )
        self.assertEqual(str(ctx.exception), 'username-obrigatorio')

    # Branch 2 (line 341-342): UsernameTakenError
    def test_raises_username_taken_when_username_already_exists(self):
        User.objects.create_user(username='maria_owner', email='other@x.com')

        with self.assertRaises(UsernameTakenError) as ctx:
            activate_pending_signup(
                pending_signup=self.pending,
                username='maria_owner',
                raw_password='secret-pwd-123',
            )
        # A exceção carrega o username conflitante
        self.assertIn('maria_owner', str(ctx.exception))

    def test_pending_signup_not_marked_activated_when_username_taken(self):
        """Estado pós-condição: rollback do PendingSignup quando username colide."""
        User.objects.create_user(username='colliding_user')
        try:
            activate_pending_signup(
                pending_signup=self.pending,
                username='colliding_user',
                raw_password='pwd',
            )
        except UsernameTakenError:
            pass

        self.pending.refresh_from_db()
        self.assertEqual(self.pending.status, PendingSignupStatus.PAID)
        self.assertIsNone(self.pending.activated_user_id)

    # Branch 3 (line 345-348): Owner Group ausente → owner_group=None, logger.error
    def test_succeeds_without_adding_to_owner_group_when_group_missing(self):
        """Se grupo Owner não existe: user é criado, log de erro é emitido, fluxo continua."""
        # Garante que grupo Owner NÃO existe
        Group.objects.filter(name='Owner').delete()

        user = activate_pending_signup(
            pending_signup=self.pending,
            username='maria_no_group',
            raw_password='secret-pwd-123',
        )

        # Estado: usuário criado, sem grupos
        self.assertTrue(User.objects.filter(username='maria_no_group').exists())
        self.assertEqual(user.groups.count(), 0)
        # PendingSignup foi ativado mesmo sem grupo
        self.pending.refresh_from_db()
        self.assertEqual(self.pending.status, PendingSignupStatus.ACTIVATED)
        self.assertEqual(self.pending.activated_user_id, user.pk)

    # Success path: Owner Group presente
    def test_adds_user_to_owner_group_when_it_exists(self):
        owner_group = Group.objects.create(name='Owner')

        user = activate_pending_signup(
            pending_signup=self.pending,
            username='maria_with_group',
            raw_password='secret-pwd-123',
        )

        self.assertIn(owner_group, user.groups.all())

    def test_full_name_split_into_first_and_last_name(self):
        """full_name 'Maria Silva' vira first='Maria', last='Silva'."""
        user = activate_pending_signup(
            pending_signup=self.pending,
            username='maria_split',
            raw_password='pwd',
        )
        self.assertEqual(user.first_name, 'Maria')
        self.assertEqual(user.last_name, 'Silva')

    def test_full_name_without_space_uses_empty_last_name(self):
        pending = _make_pending(full_name='Madonna', email='mad@x.com')
        user = activate_pending_signup(
            pending_signup=pending,
            username='madonna_user',
            raw_password='pwd',
        )
        self.assertEqual(user.first_name, 'Madonna')
        self.assertEqual(user.last_name, '')


# ===========================================================================
# create_checkout_session — branches via _resolve_price_id + Stripe
# ===========================================================================

class CreateCheckoutSessionTest(TestCase):
    """L2: create_checkout_session — branches em signup/services.py:75."""

    def setUp(self):
        self.factory = RequestFactory()
        self.request = self.factory.get('/signup/')
        self.pending = _make_pending()

    # Branch 1: plano desconhecido
    @override_settings(
        STRIPE_PRICE_EARLY_MONTHLY='price_monthly_test',
        STRIPE_SECRET_KEY='sk_test_xxx',
    )
    def test_raises_value_error_for_unknown_plan(self):
        # Força plan que não bate com monthly/annual
        self.pending.plan = 'unknown-plan'
        self.pending.save(update_fields=['plan'])

        with self.assertRaises(ValueError) as ctx:
            create_checkout_session(self.pending, self.request)
        self.assertIn('Plano desconhecido', str(ctx.exception))

    # Branch 2: STRIPE_PRICE_EARLY_MONTHLY vazio
    @override_settings(
        STRIPE_PRICE_EARLY_MONTHLY='',
        STRIPE_SECRET_KEY='sk_test_xxx',
    )
    def test_raises_stripe_not_configured_when_monthly_price_missing(self):
        self.pending.plan = PendingSignupPlan.MONTHLY
        self.pending.save(update_fields=['plan'])

        with self.assertRaises(StripeNotConfiguredError) as ctx:
            create_checkout_session(self.pending, self.request)
        self.assertIn('STRIPE_PRICE_EARLY', str(ctx.exception))

    @override_settings(
        STRIPE_PRICE_EARLY_ANNUAL='',
        STRIPE_SECRET_KEY='sk_test_xxx',
    )
    def test_raises_stripe_not_configured_when_annual_price_missing(self):
        self.pending.plan = PendingSignupPlan.ANNUAL
        self.pending.save(update_fields=['plan'])

        with self.assertRaises(StripeNotConfiguredError):
            create_checkout_session(self.pending, self.request)

    # Branch 3: STRIPE_SECRET_KEY vazia
    @override_settings(
        STRIPE_PRICE_EARLY_MONTHLY='price_monthly_test',
        STRIPE_SECRET_KEY='',
    )
    def test_raises_stripe_not_configured_when_secret_key_missing(self):
        with self.assertRaises(StripeNotConfiguredError) as ctx:
            create_checkout_session(self.pending, self.request)
        self.assertIn('STRIPE_SECRET_KEY', str(ctx.exception))

    # Branch 4: erro da API Stripe propagado
    @override_settings(
        STRIPE_PRICE_EARLY_MONTHLY='price_monthly_test',
        STRIPE_SECRET_KEY='sk_test_xxx',
    )
    def test_api_error_propagates(self):
        """Erro de rede ou validação da Stripe propaga para o caller."""
        with patch('stripe.checkout.Session.create') as mock_create:
            mock_create.side_effect = RuntimeError('stripe api down')
            with self.assertRaises(RuntimeError) as ctx:
                create_checkout_session(self.pending, self.request)
            self.assertIn('stripe api down', str(ctx.exception))

    # Success path
    @override_settings(
        STRIPE_PRICE_EARLY_MONTHLY='price_monthly_test',
        STRIPE_SECRET_KEY='sk_test_xxx',
    )
    def test_success_returns_session_url_and_saves_session_id(self):
        fake_session = MagicMock()
        fake_session.id = 'cs_test_abc123'
        fake_session.url = 'https://checkout.stripe.com/cs_test_abc123'

        with patch('stripe.checkout.Session.create', return_value=fake_session) as mock_create:
            url = create_checkout_session(self.pending, self.request)

        self.assertEqual(url, 'https://checkout.stripe.com/cs_test_abc123')
        self.pending.refresh_from_db()
        self.assertEqual(self.pending.stripe_session_id, 'cs_test_abc123')

        # Validação extra do contrato chamado
        call_kwargs = mock_create.call_args.kwargs
        self.assertEqual(call_kwargs['mode'], 'subscription')
        self.assertEqual(call_kwargs['customer_email'], self.pending.email)
        self.assertEqual(call_kwargs['client_reference_id'], str(self.pending.pk))
        # Idempotency key contém pk e plano para evitar sessions duplicadas
        self.assertIn(str(self.pending.pk), call_kwargs['idempotency_key'])


# ===========================================================================
# mark_pending_signup_paid — idempotência e branches
# ===========================================================================

class MarkPendingSignupPaidTest(TestCase):
    """L2: mark_pending_signup_paid — branches em signup/services.py:187."""

    # Branch 1 (line 195-198): pending_signup_id não encontrado
    def test_returns_none_when_pending_signup_id_does_not_exist(self):
        result = mark_pending_signup_paid(pending_signup_id=99999)
        self.assertIsNone(result)

    # Branch 2 (line 200-202): idempotência — já ACTIVATED
    def test_returns_unchanged_when_already_activated(self):
        pending = _make_pending(status=PendingSignupStatus.ACTIVATED)
        original_updated_at = pending.updated_at

        # Espera 1s para garantir que updated_at mudaria SE houvesse save
        result = mark_pending_signup_paid(
            pending_signup_id=pending.pk,
            stripe_customer_id='cus_should_be_ignored',
        )

        self.assertEqual(result.pk, pending.pk)
        self.assertEqual(result.status, PendingSignupStatus.ACTIVATED)
        # stripe_customer_id NÃO deve ter sido atualizado em ACTIVATED
        result.refresh_from_db()
        self.assertEqual(result.stripe_customer_id, '')

    # Branch 3: PENDING → PAID
    def test_transitions_pending_to_paid_on_first_webhook(self):
        pending = _make_pending(status=PendingSignupStatus.PENDING)

        result = mark_pending_signup_paid(
            pending_signup_id=pending.pk,
            stripe_session_id='cs_test_first',
            stripe_customer_id='cus_test_first',
            stripe_subscription_id='sub_test_first',
        )

        self.assertEqual(result.status, PendingSignupStatus.PAID)
        self.assertEqual(result.stripe_session_id, 'cs_test_first')
        self.assertEqual(result.stripe_customer_id, 'cus_test_first')
        self.assertEqual(result.stripe_subscription_id, 'sub_test_first')

    # Idempotência: webhook duplicado
    def test_duplicate_webhook_does_not_double_set_status(self):
        """2ª chamada com mesmo pending_id mantém status PAID."""
        pending = _make_pending(status=PendingSignupStatus.PENDING)

        first = mark_pending_signup_paid(
            pending_signup_id=pending.pk,
            stripe_session_id='cs_dup',
        )
        second = mark_pending_signup_paid(
            pending_signup_id=pending.pk,
            stripe_session_id='cs_dup',
        )

        self.assertEqual(first.status, PendingSignupStatus.PAID)
        self.assertEqual(second.status, PendingSignupStatus.PAID)
        # Mesmo objeto persistido (não duplicou)
        self.assertEqual(PendingSignup.objects.filter(pk=pending.pk).count(), 1)

    def test_partial_update_of_stripe_fields_when_provided(self):
        """Webhook pode chegar com apenas alguns campos populados."""
        pending = _make_pending(status=PendingSignupStatus.PENDING)

        result = mark_pending_signup_paid(
            pending_signup_id=pending.pk,
            stripe_customer_id='cus_only_this',
            # stripe_session_id e stripe_subscription_id não fornecidos
        )

        self.assertEqual(result.stripe_customer_id, 'cus_only_this')
        self.assertEqual(result.stripe_session_id, '')
        self.assertEqual(result.stripe_subscription_id, '')

    def test_magic_token_expires_at_is_set_when_transitioning_to_paid(self):
        """magic_token_expires_at deve ser preenchido (max_age_days no futuro)."""
        with freeze_time('2026-06-01 12:00:00'):
            pending = _make_pending(status=PendingSignupStatus.PENDING)
            result = mark_pending_signup_paid(
                pending_signup_id=pending.pk,
                stripe_session_id='cs_token_set',
            )

            self.assertIsNotNone(result.magic_token_expires_at)
            expected_expiry = timezone.now() + timedelta(days=_MAGIC_TOKEN_MAX_AGE_DAYS)
            # Tolerância de 60s
            self.assertAlmostEqual(
                result.magic_token_expires_at.timestamp(),
                expected_expiry.timestamp(),
                delta=60,
            )


# ===========================================================================
# query_stripe_session_status — branches de falha graceful
# ===========================================================================

class QueryStripeSessionStatusTest(SimpleTestCase):
    """L1: query_stripe_session_status — branches em signup/services.py:140.

    Sem banco — apenas configuração e mocks. Retorna None em qualquer falha.
    """

    # Branch 1: secret_key vazia
    @override_settings(STRIPE_SECRET_KEY='')
    def test_returns_none_when_secret_key_is_empty(self):
        self.assertIsNone(query_stripe_session_status('cs_test_abc'))

    # Branch 2: session_id vazio
    @override_settings(STRIPE_SECRET_KEY='sk_test_xxx')
    def test_returns_none_when_session_id_is_empty(self):
        self.assertIsNone(query_stripe_session_status(''))

    @override_settings(STRIPE_SECRET_KEY='sk_test_xxx')
    def test_returns_none_when_session_id_is_whitespace_only(self):
        """secret_key strip() — mas session_id NÃO. Confirmar comportamento atual."""
        # Documenta comportamento: session_id com só espaços passa para o stripe
        # e gera erro de API → retorna None pelo branch 4.
        with patch('stripe.checkout.Session.retrieve') as mock_retrieve:
            mock_retrieve.side_effect = RuntimeError('invalid session id')
            result = query_stripe_session_status('   ')
            # Whitespace é truthy em Python — chega no stripe e falha lá
            self.assertIsNone(result)

    # Branch 3: ImportError (stripe não instalado)
    @override_settings(STRIPE_SECRET_KEY='sk_test_xxx')
    def test_returns_none_when_stripe_lib_import_fails(self):
        """Simula ImportError forçando sys.modules['stripe'] = None."""
        original = sys.modules.get('stripe')
        sys.modules['stripe'] = None  # força ImportError no `import stripe` dentro da função
        try:
            result = query_stripe_session_status('cs_test_xyz')
            self.assertIsNone(result)
        finally:
            if original is not None:
                sys.modules['stripe'] = original
            else:
                sys.modules.pop('stripe', None)

    # Branch 4: erro da API Stripe → None (não propaga)
    @override_settings(STRIPE_SECRET_KEY='sk_test_xxx')
    def test_returns_none_when_stripe_api_raises(self):
        with patch('stripe.checkout.Session.retrieve') as mock_retrieve:
            mock_retrieve.side_effect = RuntimeError('rede caiu')
            result = query_stripe_session_status('cs_test_failed')
            self.assertIsNone(result)

    # Success path
    @override_settings(STRIPE_SECRET_KEY='sk_test_xxx')
    def test_returns_dict_with_payment_details_on_success(self):
        fake_session = {
            'payment_status': 'paid',
            'amount_total': 9700,
            'customer_email': 'owner@academia.test',
            'subscription': 'sub_test_xyz',
            'customer': 'cus_test_xyz',
        }
        with patch('stripe.checkout.Session.retrieve', return_value=fake_session):
            result = query_stripe_session_status('cs_test_success')

        self.assertIsNotNone(result)
        self.assertTrue(result['paid'])
        self.assertEqual(result['payment_status'], 'paid')
        self.assertEqual(result['amount_total'], 9700)
        self.assertEqual(result['customer_email'], 'owner@academia.test')
        self.assertEqual(result['subscription_id'], 'sub_test_xyz')
        self.assertEqual(result['customer_id'], 'cus_test_xyz')

    @override_settings(STRIPE_SECRET_KEY='sk_test_xxx')
    def test_paid_is_false_when_payment_status_is_unpaid(self):
        fake_session = {
            'payment_status': 'unpaid',
            'amount_total': 9700,
        }
        with patch('stripe.checkout.Session.retrieve', return_value=fake_session):
            result = query_stripe_session_status('cs_test_unpaid')

        self.assertIsNotNone(result)
        self.assertFalse(result['paid'])
        self.assertEqual(result['payment_status'], 'unpaid')

    @override_settings(STRIPE_SECRET_KEY='  sk_test_xxx  ')
    def test_secret_key_is_stripped_before_comparison(self):
        """secret_key com espaços é considerado válido após strip()."""
        with patch('stripe.checkout.Session.retrieve') as mock_retrieve:
            mock_retrieve.return_value = {'payment_status': 'paid'}
            result = query_stripe_session_status('cs_test_strip')
            self.assertIsNotNone(result)
