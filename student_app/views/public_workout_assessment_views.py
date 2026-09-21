"""
ARQUIVO: endpoint de leitura da aba Avaliacoes do corredor publico de treinos.

POR QUE ELE EXISTE:
- a aba busca o historico de avaliacoes via fetch() sem recarregar a pagina.
  So GET: a escrita ONLINE (autoavaliacao US Navy do proprio aluno) mora
  em PublicWorkoutRecordAssessmentView (POST /renan/<slug>/avaliacoes,
  exige sessao de login + gate de posse), nao aqui — este endpoint segue
  publico via cookie de posse do B0, e so leitura. A avaliacao PRESENCIAL
  (Jackson-Pollock, com o treinador e o adipometro) continua so via
  management command, nunca pela pagina.

PONTOS CRITICOS:
- roda no mesmo regime das outras views deste corredor (schema public, sem
  tenant) — ver o docstring de public_workout_views.py.
- B0 (CORDA): exige o cookie assinado que PublicWorkoutDetailView seta na
  primeira visita a /renan/<slug>. Isso prova posse do link, nao identidade
  de verdade — essa so chega na Onda B1 (PublicWorkoutAccount). Sem cookie,
  cookie de outro slug ou cookie adulterado: 404 sempre, nunca 403 (403
  confirmaria que o slug existe).
"""

from __future__ import annotations

from django.http import Http404, JsonResponse
from django.views.generic import View

from public_workouts.services import build_report

from .public_workout_views import _get_public_workout_entry, get_public_workout_owner_slug


class PublicWorkoutAssessmentsView(View):
    """GET /renan/<slug>/avaliacoes.json — exige cookie assinado do dono do slug.

    Sem cookie, cookie de outro slug ou assinatura invalida: 404 — o mesmo
    404 de slug inexistente, de proposito (ver B0 do CORDA: 403 vazaria que
    o slug existe). So leitura; a escrita online e' PublicWorkoutRecordAssessmentView.
    """

    def get(self, request, plan_slug, *args, **kwargs):
        plan = _get_public_workout_entry(plan_slug)

        if get_public_workout_owner_slug(request) != plan.slug:
            raise Http404('Treino publico nao encontrado.')

        report = build_report(plan_slug=plan.slug, sex=plan.assessment_sex, height_cm=plan.height_cm)
        return JsonResponse(report)
