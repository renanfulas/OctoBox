"""
ARQUIVO: testes de GET /renan/<slug>/treino.pdf (Entrega 4.6 — exportacao
do programa em PDF, docs/plans/public-workouts-produtizacao-corda.md).

POR QUE ELE EXISTE:
- mesma regra de auth de PublicWorkoutAssessmentsView (avaliacoes.json):
  cookie de posse do B0, 404 sempre que ausente/errado/adulterado, nunca
  403. Sem login (B1) — baixar o PDF do MESMO conteudo que a pagina ja
  mostra nao e' operacao de conta.
- prova o 404 explicito quando ainda nao ha programa publicado
  (get_active_program devolve None) — hoje e' o caso de todos os 10 slugs
  reais, ate a Onda A2 migrar os programas de verdade.
"""

from django.test import TestCase

from public_workouts.schema import build_example_payload
from public_workouts.services import publish_program


class PublicWorkoutDownloadPdfEndpointTests(TestCase):
    def _url(self, slug='giovanna'):
        return f'/renan/{slug}/treino.pdf'

    def test_returns_404_without_owner_cookie(self):
        response = self.client.get(self._url())

        self.assertEqual(response.status_code, 404)

    def test_returns_404_for_cookie_of_another_slug(self):
        self.client.get('/renan/giovanna')  # seta o cookie de giovanna

        response = self.client.get(self._url('rafael'))

        self.assertEqual(response.status_code, 404)

    def test_returns_404_for_tampered_cookie(self):
        self.client.cookies['renan_slug'] = 'giovanna'

        response = self.client.get(self._url('giovanna'))

        self.assertEqual(response.status_code, 404)

    def test_returns_404_for_unknown_plan_slug(self):
        response = self.client.get(self._url('nao-existe'))

        self.assertEqual(response.status_code, 404)

    def test_returns_404_when_no_program_published_yet(self):
        # Estado real de hoje pra todos os 10 slugs — sem programa
        # migrado pela Onda A2, get_active_program devolve None.
        self.client.get('/renan/giovanna')  # seta o cookie do dono

        response = self.client.get(self._url('giovanna'))

        self.assertEqual(response.status_code, 404)

    def test_owner_with_published_program_downloads_pdf(self):
        publish_program(slug='giovanna', payload=build_example_payload())
        self.client.get('/renan/giovanna')  # seta o cookie do dono

        response = self.client.get(self._url('giovanna'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn('attachment', response['Content-Disposition'])
        self.assertIn('treino-giovanna.pdf', response['Content-Disposition'])
        self.assertTrue(response.content.startswith(b'%PDF'))
        self.assertIn(b'Programa de exemplo', response.content)
