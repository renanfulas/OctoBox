"""
ARQUIVO: testes da landing page do corredor (Entrega 5, Fase 3 —
docs/plans/public-workouts-escala-e-nutricao-corda.md, D.7).

POR QUE ELE EXISTE:
- e' a unica rota vazia (`/treinos/`) do arquivo — hoje e' 404, esta view
  fecha esse gap. Sem logica de negocio (TemplateView puro), mas vale
  garantir que os 3 CTAs de preco apontam pro endpoint certo (Fase 2) e
  que o CSRF cookie sai emitido (a landing nunca teve sessao previa pra
  emitir um).
"""

from django.test import TestCase
from django.urls import reverse

from public_workouts.models import PublicWorkoutTier


class PublicWorkoutLandingViewTests(TestCase):
    def test_returns_200(self):
        response = self.client.get(reverse('public-workout-landing'))

        self.assertEqual(response.status_code, 200)

    def test_root_of_treinos_no_longer_404s(self):
        response = self.client.get('/treinos/')

        self.assertEqual(response.status_code, 200)

    def test_shows_all_three_tiers_with_signup_forms(self):
        response = self.client.get(reverse('public-workout-landing'))
        content = response.content.decode('utf-8')

        cold_signup_url = reverse('public-workout-cold-signup')
        for tier in (PublicWorkoutTier.ESSENCIAL, PublicWorkoutTier.COMPLETO, PublicWorkoutTier.PREMIUM):
            self.assertIn(f'data-tier="{tier}"', content)
        self.assertEqual(content.count(f'action="{cold_signup_url}"'), 3)

    def test_emits_csrf_cookie_for_the_signup_forms(self):
        response = self.client.get(reverse('public-workout-landing'))

        self.assertIn('csrfmiddlewaretoken', response.content.decode('utf-8'))

    def test_does_not_register_a_service_worker_or_pwa_install_banner(self):
        # D.7 revisado: a landing NAO estende _base.html (banner de
        # instalacao + service worker fazem sentido pra aluno com treino,
        # nao pra visitante anonimo decidindo se compra).
        response = self.client.get(reverse('public-workout-landing'))
        content = response.content.decode('utf-8')

        self.assertNotIn('serviceWorker', content)
        self.assertNotIn('public-workout-install', content)
