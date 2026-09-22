"""
ARQUIVO: teste de PublicWorkoutSignOutView (POST /renan/<slug>/sair).

POR QUE ELE EXISTE:
- achado ao vivo verificando o corredor: a view so apagava o cookie de
  posse (B0), nunca o cookie de login por e-mail (octobox_treinos_session,
  Onda B1) — a docstring original foi escrita antes do B1 existir e nunca
  foi atualizada. Resultado real: quem clicava "Sair da conta" continuava
  logado por baixo, e ao abrir o link de OUTRO aluno recebia 404
  (_confirm_login_session_owns_slug_or_404 nunca deixa uma sessao logada
  ver o slug de outra conta) — parecendo bug de acesso quando na verdade
  era sessao nunca encerrada de verdade.
"""

from django.test import TestCase
from django.urls import reverse

from public_workouts.models import PublicWorkoutAccount
from student_identity.public_workout_session import (
    PUBLIC_WORKOUT_SESSION_COOKIE_NAME,
    build_public_workout_session_value,
    get_public_workout_account_id_from_request,
)


class PublicWorkoutSignOutViewTests(TestCase):
    def setUp(self):
        self.account = PublicWorkoutAccount.objects.create(email='aluno@example.com')

    def test_signout_clears_the_login_session_cookie_not_just_the_ownership_cookie(self):
        self.client.cookies[PUBLIC_WORKOUT_SESSION_COOKIE_NAME] = build_public_workout_session_value(
            account_id=self.account.pk
        )

        response = self.client.post(reverse('public-workout-signout', kwargs={'plan_slug': 'qualquer-slug'}))

        self.assertEqual(response.status_code, 302)
        session_cookie = response.cookies.get(PUBLIC_WORKOUT_SESSION_COOKIE_NAME)
        self.assertIsNotNone(session_cookie)
        self.assertEqual(session_cookie.value, '')

    def test_signout_also_clears_the_ownership_cookie(self):
        response = self.client.post(reverse('public-workout-signout', kwargs={'plan_slug': 'qualquer-slug'}))

        owner_cookie = response.cookies.get('renan_slug')
        self.assertIsNotNone(owner_cookie)
        self.assertEqual(owner_cookie.value, '')

    def test_after_signout_a_new_request_no_longer_resolves_the_old_account(self):
        self.client.cookies[PUBLIC_WORKOUT_SESSION_COOKIE_NAME] = build_public_workout_session_value(
            account_id=self.account.pk
        )

        self.client.post(reverse('public-workout-signout', kwargs={'plan_slug': 'qualquer-slug'}))

        # O client de teste do Django ja aplica o Set-Cookie da resposta
        # anterior no proprio jar (cookie "apagado" = chave presente, valor
        # vazio — mesmo formato que um navegador real recebe) — mesma
        # verificacao de nivel HTTP que um navegador real experimentaria.
        self.assertEqual(self.client.cookies[PUBLIC_WORKOUT_SESSION_COOKIE_NAME].value, '')

        # E a proxima requisicao (com o jar ja atualizado) de fato nao
        # resolve mais a conta antiga — prova fim-a-fim, nao so o cookie.
        response = self.client.get(reverse('public-workout-login'))
        self.assertIsNone(get_public_workout_account_id_from_request(response.wsgi_request))
