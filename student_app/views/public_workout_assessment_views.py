"""
ARQUIVO: endpoint de leitura da aba Avaliacoes do corredor publico de treinos.

POR QUE ELE EXISTE:
- a aba busca o historico de avaliacoes via fetch() sem recarregar a pagina.
  So GET: nao existe escrita publica (decisao de produto — quem mede e
  registra e o treinador, via management command, nao o aluno pela pagina).

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

from django.core import signing
from django.http import Http404, JsonResponse
from django.views.generic import View

from public_workouts.services import build_report

from .public_workout_views import (
    PUBLIC_WORKOUT_OWNER_COOKIE,
    PUBLIC_WORKOUT_OWNER_COOKIE_SALT,
    _get_public_workout_entry,
)


class PublicWorkoutAssessmentsView(View):
    """GET /renan/<slug>/avaliacoes.json — exige cookie assinado do dono do slug.

    Sem cookie, cookie de outro slug ou assinatura invalida: 404 — o mesmo
    404 de slug inexistente, de proposito (ver B0 do CORDA: 403 vazaria que
    o slug existe). So leitura; escrita continua sendo so do treinador.
    """

    def get(self, request, plan_slug, *args, **kwargs):
        plan = _get_public_workout_entry(plan_slug)

        try:
            owner_slug = request.get_signed_cookie(
                PUBLIC_WORKOUT_OWNER_COOKIE, salt=PUBLIC_WORKOUT_OWNER_COOKIE_SALT, default=None
            )
        except signing.BadSignature:
            owner_slug = None

        if owner_slug != plan.slug:
            raise Http404('Treino publico nao encontrado.')

        report = build_report(plan_slug=plan.slug, sex=plan.assessment_sex, height_cm=plan.height_cm)
        return JsonResponse(report)
