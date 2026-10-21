"""
ARQUIVO: predicados puros de elegibilidade de progresso (plano
docs/plans/curva-grafico-hierarquia-e-set-role.md, Revisao 8, §7.4).

POR QUE ELE EXISTE:
- `load_chart_points` e `personal_record` (public_workouts_extras.py)
  recebem DICTS serializados (services.py::_serialize_load_log), nao
  objetos ORM; `one_rep_max.py` e `progress_snapshot.py` consultam o ORM
  direto. Uma regra de elegibilidade que lesse `log.set_role` direto
  quebraria silenciosamente se chamada a partir de um dict (retornaria
  sempre False, ou levantaria AttributeError, dependendo de como fosse
  escrita) -- por isso os predicados aqui aceitam OS DOIS formatos.
- E' o UNICO lugar do dominio que decide "isso conta como progresso" --
  nenhum consumidor reimplementa essa regra por conta propria.

PONTOS CRITICOS:
- `legacy_unknown` nunca satisfaz nenhuma das tres funcoes de
  elegibilidade -- historico anterior ao campo `set_role` fica visivel
  (tabela/pontos discretos), nunca contribui pra curva/tendencia/recorde.
- `effective_top_sets_by_day` mora aqui (nao em progress_snapshot.py)
  porque e' sobre "o que conta", nao sobre leitura de banco -- e' chamada
  tanto por progress_snapshot.py (curva) quanto por one_rep_max.py
  (tendencia semanal), que precisam da MESMA dedup pra nunca discordar
  sobre qual registro do dia vale.
"""

from __future__ import annotations

from .models import PublicWorkoutLoadLogSetRole as SetRole

_CURVE_AND_TREND_ROLES = frozenset({SetRole.TOP_SET})
_PERSONAL_RECORD_ROLES = frozenset({SetRole.TOP_SET, SetRole.MAX_SET})


def _role_of(entry) -> str | None:
    return entry.get('set_role') if isinstance(entry, dict) else getattr(entry, 'set_role', None)


def eligible_for_progress_curve(entry) -> bool:
    return _role_of(entry) in _CURVE_AND_TREND_ROLES


def eligible_for_weekly_trend(entry) -> bool:
    return _role_of(entry) in _CURVE_AND_TREND_ROLES


def eligible_for_personal_record(entry) -> bool:
    return _role_of(entry) in _PERSONAL_RECORD_ROLES


def effective_top_sets_by_day(logs: list) -> list:
    """`logs` já filtrados (ORM, com `set_role` real), em qualquer ordem.
    Devolve 1 log por dia -- o mais recente por `created_at`, NUNCA o de
    maior peso (preservaria um erro que o aluno tentou corrigir no mesmo
    dia). `progress_snapshot.py` (curva) e `one_rep_max.py` (tendência
    semanal) chamam ESTA função -- nunca duas implementações do "qual
    registro do dia vale" podendo divergir."""
    by_day = {}
    for log in logs:
        existing = by_day.get(log.performed_on)
        newer = existing is None or log.created_at > existing.created_at
        # Server timestamps can tie at database precision under concurrent
        # writes. Resolve that rare case deterministically by primary key.
        if existing is not None and log.created_at == existing.created_at:
            newer = getattr(log, 'pk', 0) > getattr(existing, 'pk', 0)
        if newer:
            by_day[log.performed_on] = log
    return sorted(by_day.values(), key=lambda log: log.performed_on)


__all__ = [
    'eligible_for_progress_curve',
    'eligible_for_weekly_trend',
    'eligible_for_personal_record',
    'effective_top_sets_by_day',
]
