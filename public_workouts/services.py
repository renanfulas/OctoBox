"""
ARQUIVO: regra de negocio da avaliacao fisica publica (sem HTTP/CLI).

POR QUE ELE EXISTE:
- tanto a view JSON (student_app/views) quanto o management command
  precisam do mesmo calculo de relatorio — fica num so lugar, testavel
  sem subir servidor nem Django admin.

PONTOS CRITICOS:
- `_validate_plan_slug` importa PUBLIC_WORKOUT_LIBRARY de dentro da funcao
  (nao no topo do arquivo) de proposito: student_app/views/public_workout_views.py
  vai importar `public_workouts.services` para servir o JSON, e um import
  de modulo no topo aqui criaria import circular.
"""

from __future__ import annotations

from .formulas import (
    classify_bmi,
    classify_body_fat,
    classify_whr,
    compute_bmi,
    compute_whr,
    estimate_body_fat_navy,
)
from .models import PublicWorkoutAssessment


class UnknownPlanSlugError(ValueError):
    pass


def _validate_plan_slug(plan_slug: str) -> None:
    from student_app.views.public_workout_views import PUBLIC_WORKOUT_LIBRARY

    if plan_slug not in PUBLIC_WORKOUT_LIBRARY:
        raise UnknownPlanSlugError(f'Plano publico desconhecido: {plan_slug!r}')


def record_assessment(
    *,
    plan_slug: str,
    measured_at,
    weight_kg=None,
    body_fat_percent=None,
    body_fat_source: str = '',
    measurements: dict | None = None,
    notes: str = '',
) -> PublicWorkoutAssessment:
    _validate_plan_slug(plan_slug)
    return PublicWorkoutAssessment.objects.create(
        plan_slug=plan_slug,
        measured_at=measured_at,
        weight_kg=weight_kg,
        body_fat_percent=body_fat_percent,
        body_fat_source=body_fat_source,
        measurements=measurements or {},
        notes=notes,
    )


def list_assessments(*, plan_slug: str):
    return list(PublicWorkoutAssessment.objects.filter(plan_slug=plan_slug).order_by('measured_at'))


def _num(value) -> float | None:
    if value is None:
        return None
    return float(value)


def _serialize(assessment: PublicWorkoutAssessment) -> dict:
    return {
        'measured_at': assessment.measured_at.isoformat(),
        'weight_kg': _num(assessment.weight_kg),
        'body_fat_percent': _num(assessment.body_fat_percent),
        'measurements': assessment.measurements,
        'notes': assessment.notes,
    }


def _delta(first: float | None, last: float | None) -> float | None:
    if first is None or last is None:
        return None
    return round(last - first, 2)


def build_report(*, plan_slug: str, sex: str | None, height_cm: float | None) -> dict:
    """Monta o payload completo consumido pela aba Avaliacoes e pelo relatorio.

    `sex`/`height_cm` vem da config do plano (PublicWorkoutPlan), nao do
    banco — sao constantes do aluno, nao variam por avaliacao.
    """
    assessments = list_assessments(plan_slug=plan_slug)
    serialized = [_serialize(a) for a in assessments]

    if not assessments:
        return {'assessments': [], 'summary': None, 'indicators': None}

    first, last = assessments[0], assessments[-1]

    measurement_keys = sorted({key for a in assessments for key in a.measurements})
    measurement_deltas = {}
    for key in measurement_keys:
        first_val = _num(first.measurements.get(key))
        last_val = _num(last.measurements.get(key))
        if last_val is None:
            continue
        measurement_deltas[key] = {
            'current': last_val,
            'first': first_val,
            'delta': _delta(first_val, last_val),
        }

    summary = {
        'weight_kg': {
            'current': _num(last.weight_kg),
            'first': _num(first.weight_kg),
            'delta': _delta(_num(first.weight_kg), _num(last.weight_kg)),
        },
        'measurements': measurement_deltas,
        'first_date': first.measured_at.isoformat(),
        'last_date': last.measured_at.isoformat(),
        'count': len(assessments),
    }

    indicators = _build_indicators(last=last, sex=sex, height_cm=height_cm)

    return {'assessments': serialized, 'summary': summary, 'indicators': indicators}


def _classification_dict(classification) -> dict:
    return {'label': classification.label, 'level': classification.level}


def _build_indicators(*, last: PublicWorkoutAssessment, sex: str | None, height_cm: float | None) -> dict:
    measurements = last.measurements or {}
    waist = _num(measurements.get('cintura'))
    hip = _num(measurements.get('quadril'))
    neck = _num(measurements.get('pescoco'))
    weight = _num(last.weight_kg)

    indicators: dict = {'bmi': None, 'whr': None, 'body_fat_percent': None}

    bmi = compute_bmi(weight_kg=weight, height_cm=height_cm)
    if bmi is not None:
        indicators['bmi'] = {'value': bmi, 'classification': _classification_dict(classify_bmi(bmi))}

    whr = compute_whr(waist_cm=waist, hip_cm=hip)
    if whr is not None and sex:
        indicators['whr'] = {'value': whr, 'classification': _classification_dict(classify_whr(sex=sex, whr=whr))}

    bf_percent = _num(last.body_fat_percent)
    bf_source = last.body_fat_source or 'manual'
    if bf_percent is None and sex and height_cm:
        bf_percent = estimate_body_fat_navy(sex=sex, height_cm=height_cm, waist_cm=waist, neck_cm=neck, hip_cm=hip)
        bf_source = 'navy_estimate'
    if bf_percent is not None and sex:
        indicators['body_fat_percent'] = {
            'value': bf_percent,
            'source': bf_source,
            'classification': _classification_dict(classify_body_fat(sex=sex, bf_percent=bf_percent)),
        }

    return indicators
