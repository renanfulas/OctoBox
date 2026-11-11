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

import re
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
    # Achado real ao propor phase_type novo pro bloco de corte do Bruno:
    # `suggest_progressive_load_kg` ESCALA a carga pela razão entre
    # %RM-meio das duas fases -- correto pras 6 fases originais (todas
    # "suba a intensidade"), mas ERRADO pra uma fase cujo objetivo
    # EXPLÍCITO é "não progredir carga, segurar a carga" (vnote real do
    # Bruno). `hold_load=True` faz a fase ecoar o ÚLTIMO peso registrado
    # sem escalar nada -- o %RM/reps/RIR da fase continuam servindo só
    # pro banner (o que realmente acontece fisiologicamente: mesmo peso
    # absoluto vira % relativa mais alta com a capacidade de recuperação
    # reduzida em déficit, não uma inconsistência de dado).
    hold_load: bool = False


# Fontes (ver docs/plans/public-workouts-produtizacao-corda.md, "O modelo
# canônico"): NSCA (zonas por %1RM), Prilepin (reps/série por faixa),
# Bompa (fases clássicas de periodização), Helms/RPE-RIR (ondulação
# semanal), consenso geral de deload (~50-70% intensidade e/ou 40-60%
# menos volume). `maintenance`/`test` (bloco de corte do Bruno, ver
# docstring de `hold_load` acima): %RM/reps/RIR pra `maintenance` batem
# com o zoneamento de força-hipertrofia de Prilepin/NSCA (75-85%/6-10
# reps) — é o que Bruno de fato mostra (RIR 1-2, reps caindo de 8-10 pra
# 6-8 ao longo do bloco); `test` é o teste de retenção com AMRAP único
# (RIR 0, zona de teste quase-máximo 85-95% de Prilepin/NSCA). Volume
# reduzido nos dois (sets_multiplier <1) segue o mesmo consenso de
# manter intensidade e cortar volume em déficit calórico (Garthe et al.,
# treino de força durante perda de gordura).
PHASE_PROFILES: dict[str, PhaseProfile] = {
    'adaptation': PhaseProfile('adaptation', 'Adaptação', (50, 62), 3.5, (12, 15), 1.0, '#FB7185'),
    'volume': PhaseProfile('volume', 'Volume', (62, 72), 2.5, (8, 12), 1.15, '#F43F5E'),
    'strength_hypertrophy': PhaseProfile('strength_hypertrophy', 'Força-Hipertrofia', (72, 80), 1.5, (6, 8), 1.0, '#E11D48'),
    'intensity': PhaseProfile('intensity', 'Intensidade', (80, 90), 0.5, (3, 6), 0.85, '#BE123C'),
    'peak': PhaseProfile('peak', 'Pico', (90, 97), 0.0, (1, 3), 0.7, '#9F1239'),
    'deload': PhaseProfile('deload', 'Deload', (50, 65), 4.5, (8, 10), 0.5, '#10B981'),
    'maintenance': PhaseProfile('maintenance', 'Manutenção', (67, 80), 1.5, (6, 10), 0.85, '#F59E0B', hold_load=True),
    'test': PhaseProfile('test', 'Teste', (85, 95), 0.0, (1, 5), 0.6, '#0EA5E9', hold_load=True),
}

PHASE_TYPE_KEYS = tuple(PHASE_PROFILES.keys())

_LOAD_ROUNDING_KG = 2.5

# Progressão dupla dentro da mesma fase: bateu o teto de reps com o RIR alvo
# (ou mais folga) -> sobe ~2,5% (mínimo um passo de 2,5 kg).
_DOUBLE_PROGRESSION_PCT = 0.025
# Troca de fase: a razão de %RM entre fases pode passar de +19% (Adaptação ->
# Volume). Limita cada virada a -15%/+10% — reentrada conservadora; a
# progressão dupla faz o resto nas semanas seguintes.
_PHASE_SHIFT_MIN_RATIO = 0.85
_PHASE_SHIFT_MAX_RATIO = 1.10
# Saindo do deload a carga só VOLTA ao nível de antes (a entrada cortou até
# 15%); o teto de +10% ali faria o aluno recomeçar abaixo do pré-deload.
_DELOAD_EXIT_MAX_RATIO = 1 / _PHASE_SHIFT_MIN_RATIO


def _intensity_fraction(reps: float, rir: float) -> float:
    """%1RM (fração) para `reps` com `rir` em reserva — Epley invertido, o
    mesmo `1 + reps_efetivas/30` de `one_rep_max.py`."""
    return 1 / (1 + (reps + rir) / 30)


def _program_week_index(payload: dict, day: date) -> int | None:
    """Semana do PROGRAMA (conta a partir de `started_on`, sem ciclar) — não a
    semana ISO: um programa que começa na quarta vira a semana na quarta."""
    started_on_raw = payload.get('started_on')
    if not started_on_raw:
        return None
    return (day - date.fromisoformat(started_on_raw)).days // 7


def _phase_midpoint(phase: PhaseProfile) -> float:
    return sum(phase.intensity_pct_range) / 2


def _round_to_nearest_load(value: float) -> float:
    return round(value / _LOAD_ROUNDING_KG) * _LOAD_ROUNDING_KG


def _hit_double_progression(last_log: dict, phase: PhaseProfile, reps_max_target: int | None) -> bool:
    """Teto de reps atingido com RIR >= alvo da fase (meio ponto de
    tolerância). Sem RIR registrado, basta o teto de reps."""
    reps = last_log.get('reps')
    if reps is None or reps_max_target is None:
        return False
    try:
        if int(reps) < int(reps_max_target):
            return False
    except (TypeError, ValueError):
        return False
    rir = last_log.get('rir')
    if rir is None:
        return True
    try:
        return float(rir) >= phase.rir_target - 0.5
    except (TypeError, ValueError):
        return False


def _phase_shift_ratio(*, last_log: dict, phase_when_logged: PhaseProfile, current_phase: PhaseProfile,
                       target_reps: float | None, target_rir: float | None) -> float:
    """Fator de carga na virada de fase.

    - Saindo do deload: razão de %RM-meio (desfaz o corte da entrada); o
      registro do deload subestima a capacidade (o aluno segurou de propósito).
    - Entrando no deload: o menor entre %RM-meio e reps/RIR — garante a queda
      de intensidade clássica.
    - Demais viradas: o que o aluno FEZ (reps/RIR do registro) contra o que a
      semana pede (reps/RIR prescritos), para carga e reps andarem juntas; sem
      reps no registro, %RM-meio das fases.
    Limitado a -15%/+10% (saída do deload: só até voltar ao pré-deload)."""
    midpoint_ratio = _phase_midpoint(current_phase) / _phase_midpoint(phase_when_logged)
    if phase_when_logged.key == 'deload':
        return min(max(midpoint_ratio, _PHASE_SHIFT_MIN_RATIO), _DELOAD_EXIT_MAX_RATIO)

    ratio = midpoint_ratio
    logged_reps = last_log.get('reps')
    if logged_reps is not None and target_reps is not None:
        try:
            logged_rir = last_log.get('rir')
            logged_rir = float(logged_rir) if logged_rir is not None else phase_when_logged.rir_target
            wanted_rir = float(target_rir) if target_rir is not None else current_phase.rir_target
            ratio = (_intensity_fraction(float(target_reps), wanted_rir)
                     / _intensity_fraction(float(logged_reps), logged_rir))
        except (TypeError, ValueError):
            ratio = midpoint_ratio
    if current_phase.key == 'deload':
        ratio = min(ratio, midpoint_ratio)
    return min(max(ratio, _PHASE_SHIFT_MIN_RATIO), _PHASE_SHIFT_MAX_RATIO)


_COACH_WEEK_REPS = re.compile(r'^\s*(\d{1,2})\s*[-–]\s*(\d{1,2})\s*(?:reps?|repetições)?\s*$', re.I)


def coach_week_reps(payload: dict | None, week_number: int | None) -> tuple[int, int] | None:
    """Faixa de reps que o treinador escreveu para a semana na planilha
    (`periodization.weeks_table[semana-1].reps`). Só texto que é SÓ uma faixa
    ("8-12 reps"); "Livre", "Faixas de cada exercício" ou "RIR 4-5" não contam.
    Achado real: o "Peak" da Milene é 8-12 reps (o perfil canônico diria 1-3)."""
    table = ((payload or {}).get('periodization') or {}).get('weeks_table') or []
    if week_number is None or not 1 <= week_number <= len(table):
        return None
    row = table[week_number - 1]
    match = _COACH_WEEK_REPS.match(str(row.get('reps') or '')) if isinstance(row, dict) else None
    if match is None:
        return None
    low, high = int(match.group(1)), int(match.group(2))
    return (low, high) if 1 <= low <= high else None


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


def build_chart_points_from_weeks(weeks: list[dict], payload: dict | None = None) -> list[dict]:
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
            'reps': '{}-{}'.format(*(coach_week_reps(payload, row.get('week_number')) or phase.reps_target_range)),
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
    reps_max_target: int | None = None,
    target_reps: float | None = None,
    target_rir: float | None = None,
    today: date | None = None,
) -> float | None:
    """kg sugerido pra ESTA semana = última carga REAL registrada nesse
    movimento dentro do PROGRAMA ATUAL, escalada pela razão entre o
    %RM-meio da fase de agora e o %RM-meio da fase de quando aquela carga
    foi registrada. Nunca recalcula do zero contra um 1RM estimado (ver
    docstring do módulo) -- `one_rep_max_kg`, quando fornecido, só limita
    o teto (nunca deixa a razão sugerir acima do %RM máximo da fase atual
    contra o 1RM estimado, protege contra um log anômalo se propagando).

    Mesma fase de quando o log foi feito (mesma `key`, inclusive na volta
    do mesociclo): devolve a última carga real tal e qual, SEM o teto do
    1RM — decisão de produto: o aluno acabou de fazer aquele peso nesta
    fase, e o teto sugeria menos (100 kg x 8 RIR 2 em Volume virava 95).

    `current_phase.hold_load=True` (ex.: `maintenance`/`test`, bloco de
    corte -- ver docstring de `PhaseProfile.hold_load`) pula a escala por
    razão inteiramente: devolve a ÚLTIMA carga registrada tal e qual,
    porque o objetivo dessas fases é EXPLICITAMENTE não progredir peso —
    escalar pela razão de %RM aqui produziria o mesmo salto perigoso que
    o "achado crítico" original deste módulo já corrigiu pras fases de
    progressão. Nesse caso nem precisa resolver a fase de quando o log
    foi feito (irrelevante — o alvo é sempre "repete o último peso").

    `None` (cai pro fallback/hint) quando: não há log ainda pra esse
    movimento (bootstrap -- primeira vez neste programa); o log é de um
    programa ANTERIOR (`program_id` não bate -- carga de outro ciclo não é
    uma base de comparação válida); ou (fases sem `hold_load`) a fase de
    quando o log foi feito não é resolvível (log de antes de existir
    periodização canônica)."""
    if last_log is None or last_log.get('weight_kg') is None:
        return None

    program_id = payload.get('program_id')
    if program_id and last_log.get('program_id') != program_id:
        return None

    logged_on_raw = last_log.get('performed_on')
    phase_when_logged = (
        current_phase_profile(payload, today=date.fromisoformat(logged_on_raw)) if logged_on_raw else None
    )
    # Mesma fase de quando a carga foi feita: repete a última carga real, sem
    # passar pelo teto do 1RM. O aluno acabou de mostrar que aguenta esse peso
    # nesta fase; cortar pelo teto sugeria menos do que ele tinha feito.
    if phase_when_logged is not None and phase_when_logged.key == current_phase.key:
        weight = float(last_log['weight_kg'])
        # Só de uma semana DO PROGRAMA para a outra: no mesmo microciclo repete.
        logged_week = _program_week_index(payload, date.fromisoformat(logged_on_raw))
        this_week = _program_week_index(payload, today or date.today())
        same_week = logged_week is None or logged_week == this_week
        # Deload não progride: é semana de recuperação.
        if (not current_phase.hold_load and current_phase.key != 'deload' and not same_week
                and _hit_double_progression(last_log, current_phase, reps_max_target)):
            return max(
                _round_to_nearest_load(weight * (1 + _DOUBLE_PROGRESSION_PCT)),
                _round_to_nearest_load(weight) + _LOAD_ROUNDING_KG,
            )
        return _round_to_nearest_load(weight)

    if current_phase.hold_load:
        suggested = float(last_log['weight_kg'])
    else:
        if phase_when_logged is None:
            return None

        ratio = _phase_shift_ratio(
            last_log=last_log, phase_when_logged=phase_when_logged, current_phase=current_phase,
            target_reps=target_reps, target_rir=target_rir,
        )
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
    'coach_week_reps',
    'current_phase_profile',
    'current_week_number',
    'suggest_progressive_load_kg',
]
