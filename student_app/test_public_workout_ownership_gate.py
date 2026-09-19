"""
ARQUIVO: testes do gate de posse do slug (Onda B3 do CORDA, item 5 —
docs/plans/public-workouts-produtizacao-corda.md).

POR QUE ELE EXISTE:
- prova a garantia central do item 5: com sessao de login ativa
  (PublicWorkoutAccount), a view so mostra o treino se a conta for dona
  DAQUELE slug (via PublicWorkoutSubscription) — senao 404, nunca 403
  (403 confirmaria que o slug existe) e nunca o treino de outra pessoa.
  Sem sessao (visitante anonimo, fluxo B0 por cookie), nada muda.
"""

from django.test import TestCase

from public_workouts.models import PublicWorkoutAccount, PublicWorkoutSubscription, PublicWorkoutSubscriptionStatus
from student_identity.public_workout_session import (
    PUBLIC_WORKOUT_SESSION_COOKIE_NAME,
    build_public_workout_session_value,
)


def _make_account_with_subscription(*, email, plan_slug, status=None) -> PublicWorkoutAccount:
    account = PublicWorkoutAccount.objects.create(email=email)
    kwargs = {'account': account, 'plan_slug': plan_slug}
    if status is not None:
        kwargs['status'] = status
    PublicWorkoutSubscription.objects.create(**kwargs)
    return account


class PublicWorkoutOwnershipGateTests(TestCase):
    def test_anonymous_visitor_is_unaffected(self):
        # Fluxo B0 (cookie de posse por link) continua igual — fase B de
        # login obrigatorio (Onda B3) ainda nao esta ligada.
        response = self.client.get('/renan/bruno')

        self.assertEqual(response.status_code, 200)

    def test_logged_in_account_can_open_the_slug_it_owns(self):
        account = _make_account_with_subscription(email='bruno@example.com', plan_slug='bruno')
        self.client.cookies[PUBLIC_WORKOUT_SESSION_COOKIE_NAME] = build_public_workout_session_value(
            account_id=account.pk
        )

        response = self.client.get('/renan/bruno')

        self.assertEqual(response.status_code, 200)

    def test_logged_in_account_opening_someone_elses_slug_gets_404_not_403(self):
        # A garantia central do item 5: "aluno A logado abrindo o slug do
        # aluno B recebe 404" (nunca 403, nunca o treino de B).
        account_a = _make_account_with_subscription(email='a@example.com', plan_slug='bruno')
        self.client.cookies[PUBLIC_WORKOUT_SESSION_COOKIE_NAME] = build_public_workout_session_value(
            account_id=account_a.pk
        )

        response = self.client.get('/renan/juliana')

        self.assertEqual(response.status_code, 404)
        self.assertNotContains(response, 'Juliana', status_code=404)

    def test_logged_in_account_without_any_subscription_gets_404(self):
        account = PublicWorkoutAccount.objects.create(email='sem-assinatura@example.com')
        self.client.cookies[PUBLIC_WORKOUT_SESSION_COOKIE_NAME] = build_public_workout_session_value(
            account_id=account.pk
        )

        response = self.client.get('/renan/bruno')

        self.assertEqual(response.status_code, 404)

    def test_tampered_session_cookie_is_treated_as_anonymous(self):
        # Assinatura invalida: get_public_workout_account_id_from_request
        # ja devolve None (nunca levanta) -- mesmo comportamento do
        # visitante anonimo, nao um 404 por engano.
        self.client.cookies[PUBLIC_WORKOUT_SESSION_COOKIE_NAME] = 'valor-solto-sem-assinatura'

        response = self.client.get('/renan/bruno')

        self.assertEqual(response.status_code, 200)

    def test_session_cookie_is_scoped_broad_enough_to_reach_renan(self):
        # Regressao do bug achado ao implementar este gate: o cookie de
        # login nascia com path=/treinos/, que um navegador de verdade
        # NUNCA enviaria numa requisicao a /renan/<slug> (RFC 6265) --
        # o proprio gate ficaria sempre cego. O test client do Django nao
        # reproduz essa restricao de path (so mescla cookies), entao a
        # garantia certa de testar e o atributo Path que o servidor
        # declara no Set-Cookie, nao o reenvio simulado.
        from student_identity.public_workout_session import PUBLIC_WORKOUT_SESSION_PATH

        self.assertEqual(PUBLIC_WORKOUT_SESSION_PATH, '/')


class PublicWorkoutSubscriptionStatusGateTests(TestCase):
    """P0 do acesso pago (achado real: ate a Onda B2/Fase 4, nada checava
    status de pagamento pra servir /renan/<slug> — uma assinatura
    suspensa/em atraso/cancelada continuava vendo o treino inteiro).

    So' bloqueia quando existe uma PublicWorkoutSubscription pra este slug
    E ela nao esta ACTIVE — nunca quando nao existe assinatura nenhuma
    (os 10 clientes legados nunca passaram pelo checkout Stripe deste
    corredor, ver seed_legacy_workout_accounts.py, e continuam servidos
    pela PUBLIC_WORKOUT_LIBRARY sem nenhuma linha de assinatura)."""

    def test_active_subscription_is_not_blocked(self):
        _make_account_with_subscription(
            email='ativo@example.com', plan_slug='bruno', status=PublicWorkoutSubscriptionStatus.ACTIVE
        )

        response = self.client.get('/renan/bruno')

        self.assertEqual(response.status_code, 200)

    def test_suspended_subscription_blocks_access_even_anonymously(self):
        _make_account_with_subscription(
            email='suspenso@example.com', plan_slug='bruno', status=PublicWorkoutSubscriptionStatus.SUSPENDED
        )

        response = self.client.get('/renan/bruno')

        self.assertEqual(response.status_code, 404)

    def test_past_due_subscription_blocks_access(self):
        _make_account_with_subscription(
            email='atraso@example.com', plan_slug='bruno', status=PublicWorkoutSubscriptionStatus.PAST_DUE
        )

        response = self.client.get('/renan/bruno')

        self.assertEqual(response.status_code, 404)

    def test_canceled_subscription_blocks_access(self):
        _make_account_with_subscription(
            email='cancelado@example.com', plan_slug='bruno', status=PublicWorkoutSubscriptionStatus.CANCELED
        )

        response = self.client.get('/renan/bruno')

        self.assertEqual(response.status_code, 404)

    def test_blocked_slug_never_reveals_content_in_a_404(self):
        _make_account_with_subscription(
            email='suspenso2@example.com', plan_slug='bruno', status=PublicWorkoutSubscriptionStatus.SUSPENDED
        )

        response = self.client.get('/renan/bruno')

        self.assertNotContains(response, 'Bruno', status_code=404)

    def test_a_slug_with_no_subscription_row_at_all_is_never_blocked(self):
        # Legado: giovanna nao tem PublicWorkoutSubscription nenhuma neste
        # teste (mesma realidade dos 10 clientes reais antes da Onda B1/B2).
        response = self.client.get('/renan/giovanna')

        self.assertEqual(response.status_code, 200)

    def test_logged_in_owner_of_a_suspended_subscription_is_also_blocked(self):
        # O bloqueio nao e' so' pro visitante anonimo — o proprio dono
        # logado tambem fica de fora enquanto a assinatura nao voltar a
        # ACTIVE (reactivate_subscription, billing.py).
        account = _make_account_with_subscription(
            email='dono-suspenso@example.com', plan_slug='bruno', status=PublicWorkoutSubscriptionStatus.SUSPENDED
        )
        self.client.cookies[PUBLIC_WORKOUT_SESSION_COOKIE_NAME] = build_public_workout_session_value(
            account_id=account.pk
        )

        response = self.client.get('/renan/bruno')

        self.assertEqual(response.status_code, 404)
