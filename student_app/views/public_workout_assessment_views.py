"""
ARQUIVO: endpoint de leitura da aba Avaliacoes do corredor publico de treinos.

POR QUE ELE EXISTE:
- a aba busca o historico de avaliacoes via fetch() sem recarregar a pagina.
  So GET: nao existe escrita publica (decisao de produto — quem mede e
  registra e o treinador, via management command, nao o aluno pela pagina).

PONTOS CRITICOS:
- roda no mesmo regime das outras views deste corredor (schema public, sem
  tenant) — ver o docstring de public_workout_views.py.
"""

from __future__ import annotations

from django.http import JsonResponse
from django.views.generic import View

from public_workouts.services import build_report

from .public_workout_views import _get_public_workout_entry


class PublicWorkoutAssessmentsView(View):
    def get(self, request, plan_slug, *args, **kwargs):
        plan = _get_public_workout_entry(plan_slug)
        report = build_report(plan_slug=plan.slug, sex=plan.assessment_sex, height_cm=plan.height_cm)
        return JsonResponse(report)
