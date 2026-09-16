"""
ARQUIVO: sugestão de carga (kg) pra exercícios SEM fase canônica de
periodização — "Caminho 4" do plano de periodização/carga (Onda B3+ do
CORDA, docs/plans/public-workouts-produtizacao-corda.md).

POR QUE ELE EXISTE:
- pros 9 clientes ainda não migrados pro modelo canônico
  (`periodization.PHASE_PROFILES`), a única fonte de "quanto pesar" é o
  que o próprio treinador já escreveu por exercício (`reps_spec`/
  `rir_spec`, texto livre) + o 1RM estimado do aluno
  (`one_rep_max.estimate_one_rep_max`). Este módulo extrai o alvo
  numérico de reps/RIR do "top set" desse texto e inverte a fórmula de
  1RM (`one_rep_max.estimate_working_weight_kg`) pra chegar num peso.
- separado de `periodization.py` de propósito: são dois problemas
  DIFERENTES. `periodization.suggest_progressive_load_kg` ancora na
  última carga REAL registrada e escala por progressão de fase (nunca
  recalcula do zero); este módulo faz uma estimativa PONTUAL de "quanto
  pesar hoje" a partir do que o exercício em si já pede, sem nenhuma
  noção de progressão multi-semana.

PONTOS CRÍTICOS — nunca "chuta" um número de um texto ambíguo:
- `extract_top_set_reps_target` só aceita reps entre PARÊNTESES
  (`"3× Top (6-8)"`) ou no formato `<sets>×<reps>` bem formado
  (`"3x8-10"`) — NUNCA "primeiro número da string". Armadilha real
  encontrada nos 10 HTMLs: `"1 preparatória + 1 feeder + 3 top sets ·
  6-10 reps"` (john.html) tem "1" antes do alvo de verdade (6-10); sem um
  parêntese ou `×` claro delimitando, devolve `None` em vez de errar.
  `"3× Top (crescente)"` (henrique.html, sem número — carga em rampa,
  cada set um peso diferente) também devolve `None` de propósito: não há
  um alvo fixo pra estimar.
- Multi-fase (`"2-3× Prep → 1× Feeder → 3× Top (6-8)"`): só o segmento
  com a palavra "Top" (case-insensitive) é considerado — Prep/Feeder/Max
  têm seus próprios alvos, mais leves ou abertos, nunca usados aqui.
- `extract_rir_target` nunca assume RIR=0 quando o texto não tem "RIR"
  reconhecível (`"Isometria"`, `""`) — isso na verdade sugeriria peso MAIS
  pesado (RIR baixo = mais perto da falha), a direção ERRADA pra "seguro
  por padrão". Sem RIR extraível, `suggest_movement_load` devolve `None`.
"""

from __future__ import annotations

import re

from .one_rep_max import estimate_working_weight_kg

_TOP_PHASE_RE = re.compile(r'\btop\b', re.IGNORECASE)
_PAREN_RANGE_RE = re.compile(r'\((\d+)\s*-\s*(\d+)\)')
_PAREN_SINGLE_RE = re.compile(r'\((\d+)\)')
_BARE_SETSX_RANGE_RE = re.compile(r'[×x]\s*(\d+)\s*-\s*(\d+)(?!\d)')
_BARE_SETSX_SINGLE_RE = re.compile(r'[×x]\s*(\d+)(?!\d)')

_RIR_RANGE_RE = re.compile(r'\bRIR\s*(\d+)\s*-\s*(\d+)', re.IGNORECASE)
_RIR_SINGLE_RE = re.compile(r'\bRIR\s*(\d+)', re.IGNORECASE)


def extract_top_set_reps_target(reps_spec: str) -> tuple[float, float] | None:
    """`"3× Top (6-8)"` -> `(6.0, 8.0)`. `None` quando o texto não tem um
    alvo numérico claramente delimitado (parênteses ou `<sets>×<reps>`) —
    ver PONTOS CRÍTICOS no topo do módulo pros casos reais que motivam
    nunca cair pra "primeiro número da string"."""
    if not reps_spec:
        return None

    segments = [segment.strip() for segment in reps_spec.split('→') if segment.strip()]
    if len(segments) >= 2:
        top_segments = [segment for segment in segments if _TOP_PHASE_RE.search(segment)]
        if not top_segments:
            return None
        segment = top_segments[-1]
    elif segments:
        segment = segments[0]
    else:
        return None

    match = _PAREN_RANGE_RE.search(segment)
    if match:
        return float(match.group(1)), float(match.group(2))

    match = _PAREN_SINGLE_RE.search(segment)
    if match:
        value = float(match.group(1))
        return value, value

    match = _BARE_SETSX_RANGE_RE.search(segment)
    if match:
        return float(match.group(1)), float(match.group(2))

    match = _BARE_SETSX_SINGLE_RE.search(segment)
    if match:
        value = float(match.group(1))
        return value, value

    return None


def extract_rir_target(rir_spec: str) -> float | None:
    """`"RIR 1-2"` -> `1.5` (média da faixa); `"RIR 2"` -> `2.0`. `None`
    sem um "RIR N" reconhecível (nunca assume RIR=0 — ver PONTOS
    CRÍTICOS)."""
    if not rir_spec:
        return None

    match = _RIR_RANGE_RE.search(rir_spec)
    if match:
        return (float(match.group(1)) + float(match.group(2))) / 2

    match = _RIR_SINGLE_RE.search(rir_spec)
    if match:
        return float(match.group(1))

    return None


def suggest_movement_load(*, movement: dict, one_rep_max_kg: float | None) -> dict | None:
    """Combina `extract_top_set_reps_target` + `extract_rir_target` +
    `one_rep_max.estimate_working_weight_kg`. `None` (cai pro fallback
    "Livre"/hint de registro) se faltar 1RM, se o texto não tiver um alvo
    de reps claro, se não tiver RIR reconhecível, ou se a estimativa
    resultante ficar fora da faixa válida (>15 reps efetivas)."""
    if one_rep_max_kg is None:
        return None

    reps_target = extract_top_set_reps_target(movement.get('reps_spec') or '')
    if reps_target is None:
        return None

    rir_target = extract_rir_target(movement.get('rir_spec') or '')
    if rir_target is None:
        return None

    target_reps_mid = sum(reps_target) / 2
    value_kg = estimate_working_weight_kg(
        one_rep_max_kg=one_rep_max_kg, target_reps=target_reps_mid, target_rir=rir_target,
    )
    if value_kg is None:
        return None

    return {'value_kg': value_kg}


__all__ = [
    'extract_rir_target',
    'extract_top_set_reps_target',
    'suggest_movement_load',
]
