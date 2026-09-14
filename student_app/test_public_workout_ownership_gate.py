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

from public_workouts.models import PublicWorkoutAccount, PublicWorkoutSubscription
from student_identity.public_workout_session import (
    PUBLIC_WORKOUT_SESSION_COOKIE_NAME,
    build_public_workout_session_value,
)


def _make_account_with_subscription(*, email, plan_slug) -> PublicWorkoutAccount:
    account = PublicWorkoutAccount.objects.create(email=email)
    PublicWorkoutSubscription.objects.create(account=account, plan_slug=plan_slug)
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
