"""
ARQUIVO: modelo canônico de periodização + progressão de carga (Onda B3+
do CORDA — docs/plans/public-workouts-produtizacao-corda.md, "Periodização
canônica").

POR QUE ELE EXISTE:
- `templates/public_workouts/workout.html` deixou de ser só o layout que
  substitui os 10 HTMLs legados — é o template UNIVERSAL de treino do app,
  todo programa futuro nasce nele. Isso exige um vocabulário de fase
  FECHADO (`PHASE_PROFILES`), ao contrário do texto livre que os 10
  clientes legados usam hoje (`periodization.chart`/`weeks_table` —
  13 rótulos diferentes encontrados: Adaptação, Manutenção, Teste, Deload,
  Volume, Força-Hiper, Intensidade, Pico, Pico Máx, Vol. Alto, Peak, Base,
  Progressão). Os números por fase (%RM, RIR, reps) têm fonte real —
  NSCA/Prilepin/Bompa/Helms, ver plano — não são achismo; ajustar um
  número aqui é mudar CONSTANTE, não arquitetura (mesmo espírito de
  `_LOW_REP_CEILING`/`_PLATEAU_BAND_PCT` em `one_rep_max.py`).
- `current_week_number`/`current_phase_profile` seguem o MESMO padrão de
  função pura com `today` injetável de `dashboard.py::build_week_overview`
  (testável sem mockar `date.today()`, mesmo motivo).

PONTOS CRÍTICOS:
- **`suggest_progressive_load_kg` NÃO recalcula `%RM_da_fase × 1RM_estimado`
  do zero a cada semana.** Essa primeira versão do design quebrava contra
  o dado real da própria Juliana (a prova de conceito escolhida): o
  `vnote` dela diz literalmente "a carga é o que progride semana a
  semana" e a `weeks_table` real usa incrementos pequenos e relativos
  ("+2,5 kg vs. Semana 1", nunca um número novo desconectado) sobre uma
  "carga base" == o que o aluno REALMENTE levantou. Recalcular do zero
  contra um 1RM estimado (que tem ruído set a set) produziria saltos
  bruscos entre fases (ex.: Volume 67% → Intensidade 85% seria +27%
  relativo numa semana só) — uma sugestão errada e potencialmente
  perigosa pra uma aluna de verdade. A correção: ancorar na ÚLTIMA carga
  real registrada NESTE programa pra aquele movimento, escalado pela
  RAZÃO entre o %RM-meio da fase de agora e o %RM-meio da fase de quando
  aquela carga foi registrada — nunca um número solto. O 1RM estimado
  (quando existe) só entra como TETO de segurança, nunca como fonte
  principal do número.
- `current_week_number` cicla em `len(weeks)` (nunca em `payload['weeks']`,
  que é uma decisão de negócio separada e — confirmado nos 10 clientes
  reais — não bate com a contagem real de semanas do gráfico) — mesmo
  espírito de `dashboard.py`: "o programa se repete toda semana até o
  treinador publicar uma versão nova".
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class PhaseProfile:
    key: str
    label: str
    intensity_pct_range: tuple[float, float]
    rir_target: float
    reps_target_range: tuple[int, int]
    sets_multiplier: float  # 1.0 = volume normal; <1 reduz, >1 aumenta -- fundação (ver plano), ainda não aplicado na UI
    color: str


# Fontes (ver docs/plans/public-workouts-produtizacao-corda.md, "O modelo
# canônico"): NSCA (zonas por %1RM), Prilepin (reps/série por faixa),
# Bompa (fases clássicas de periodização), Helms/RPE-RIR (ondulação
# semanal), consenso geral de deload (~50-70% intensidade e/ou 40-60%
# menos volume).
PHASE_PROFILES: dict[str, PhaseProfile] = {
    'adaptation': PhaseProfile('adaptation', 'Adaptação', (50, 62), 3.5, (12, 15), 1.0, '#FB7185'),
    'volume': PhaseProfile('volume', 'Volume', (62, 72), 2.5, (8, 12), 1.15, '#F43F5E'),
    'strength_hypertrophy': PhaseProfile('strength_hypertrophy', 'Força-Hipertrofia', (72, 80), 1.5, (6, 8), 1.0, '#E11D48'),
    'intensity': PhaseProfile('intensity', 'Intensidade', (80, 90), 0.5, (3, 6), 0.85, '#BE123C'),
    'peak': PhaseProfile('peak', 'Pico', (90, 97), 0.0, (1, 3), 0.7, '#9F1239'),
    'deload': PhaseProfile('deload', 'Deload', (50, 65), 4.5, (8, 10), 0.5, '#10B981'),
}

PHASE_TYPE_KEYS = tuple(PHASE_PROFILES.keys())

_LOAD_ROUNDING_KG = 2.5


def _phase_midpoint(phase: PhaseProfile) -> float:
    return sum(phase.intensity_pct_range) / 2


def _round_to_nearest_load(value: float) -> float:
    return round(value / _LOAD_ROUNDING_KG) * _LOAD_ROUNDING_KG


def current_week_number(payload: dict, *, today: date | None = None) -> int | None:
    """1-based, cicla em `len(weeks)` -- mesmo espírito de dashboard.py
    (o mesociclo se repete a cada volta até o treinador publicar uma
    versão nova). `None` sem `periodization.weeks`, sem `started_on`, ou
    se `today` for antes do início do programa."""
    weeks = ((payload.get('periodization') or {}).get('weeks')) or []
    started_on_raw = payload.get('started_on')
    if not weeks or not started_on_raw:
        return None

    started_on = date.fromisoformat(started_on_raw)
    today = today or date.today()
    if today < started_on:
        return None

    elapsed_weeks = (today - started_on).days // 7
    return (elapsed_weeks % len(weeks)) + 1


def current_phase_profile(payload: dict, *, today: date | None = None) -> PhaseProfile | None:
    """`current_week_number` -> acha a `phase_type` daquela semana em
    `periodization.weeks` -> devolve o `PhaseProfile` correspondente.
    `None` se a semana não tiver linha correspondente (lista com buraco)
    ou sem `weeks`/`started_on`."""
    week_number = current_week_number(payload, today=today)
    if week_number is None:
        return None

    weeks = (payload.get('periodization') or {}).get('weeks') or []
    for row in weeks:
        if row.get('week_number') == week_number:
            return PHASE_PROFILES.get(row.get('phase_type'))
    return None


def build_chart_points_from_weeks(weeks: list[dict]) -> list[dict]:
    """`periodization.weeks` (canônico) -> pontos do gráfico no MESMO
    formato que `periodization.chart` (legado) já usa -- o markup do
    gráfico em `workout.html` não muda, só a fonte do dado muda.

    `h` (altura da barra, 0-100): %RM-meio da fase normalizado pelo maior
    %RM-meio entre TODAS as fases do vocabulário canônico (Pico = 100%,
    resto proporcional) -- não pelo maior só entre as fases presentes
    NESTE `weeks`, pra barras de mesociclos diferentes ficarem
    comparáveis entre si na mesma escala visual."""
    max_mid = max(_phase_midpoint(phase) for phase in PHASE_PROFILES.values())

    points = []
    for row in weeks:
        phase = PHASE_PROFILES.get(row.get('phase_type'))
        if phase is None:
            continue
        points.append({
            'label': f"S{row.get('week_number')}",
            'focus': phase.label,
            'reps': f"{phase.reps_target_range[0]}-{phase.reps_target_range[1]}",
            'color': phase.color,
            'bg': phase.color,
            'fg': phase.color,
            'h': round((_phase_midpoint(phase) / max_mid) * 100),
            'week_number': row.get('week_number'),
        })
    return points


def suggest_progressive_load_kg(
    *,
    payload: dict,
    current_phase: PhaseProfile,
    last_log: dict | None,
    one_rep_max_kg: float | None = None,
) -> float | None:
    """kg sugerido pra ESTA semana = última carga REAL registrada nesse
    movimento dentro do PROGRAMA ATUAL, escalada pela razão entre o
    %RM-meio da fase de agora e o %RM-meio da fase de quando aquela carga
    foi registrada. Nunca recalcula do zero contra um 1RM estimado (ver
    docstring do módulo) -- `one_rep_max_kg`, quando fornecido, só limita
    o teto (nunca deixa a razão sugerir acima do %RM máximo da fase atual
    contra o 1RM estimado, protege contra um log anômalo se propagando).

    `None` (cai pro fallback/hint) quando: não há log ainda pra esse
    movimento (bootstrap -- primeira vez neste programa); o log é de um
    programa ANTERIOR (`program_id` não bate -- carga de outro ciclo não é
    uma base de comparação válida); ou a fase de quando o log foi feito
    não é resolvível (log de antes de existir periodização canônica)."""
    if last_log is None or last_log.get('weight_kg') is None:
        return None

    program_id = payload.get('program_id')
    if program_id and last_log.get('program_id') != program_id:
        return None

    logged_on_raw = last_log.get('performed_on')
    if not logged_on_raw:
        return None
    phase_when_logged = current_phase_profile(payload, today=date.fromisoformat(logged_on_raw))
    if phase_when_logged is None:
        return None

    ratio = _phase_midpoint(current_phase) / _phase_midpoint(phase_when_logged)
    suggested = float(last_log['weight_kg']) * ratio

    if one_rep_max_kg:
        ceiling = (current_phase.intensity_pct_range[1] / 100) * one_rep_max_kg
        suggested = min(suggested, ceiling)

    return _round_to_nearest_load(suggested)


__all__ = [
    'PHASE_PROFILES',
    'PHASE_TYPE_KEYS',
    'PhaseProfile',
    'build_chart_points_from_weeks',
    'current_phase_profile',
    'current_week_number',
    'suggest_progressive_load_kg',
]
