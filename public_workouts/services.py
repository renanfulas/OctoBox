"""
ARQUIVO: regra de negocio do corredor sem HTTP/CLI — avaliacao fisica,
leitura/publicacao de programa (S1, Onda A1 Fatia A) e, a partir da Onda A1
Fatia B, pacote do aluno (S2) e registro de carga (S3).

POR QUE ELE EXISTE:
- tanto a view JSON (student_app/views) quanto o management command
  precisam do mesmo calculo de relatorio — fica num so lugar, testavel
  sem subir servidor nem Django admin.
- S1/S2/S3 sao as assinaturas CONGELADAS na Onda S0 (D.5) — Frente B ja
  programava contra elas desde o dia 1, primeiro via o stub em
  services_stub.py (removido nesta onda: as tres ja sao reais), agora
  contra esta implementacao de verdade.

PONTOS CRITICOS:
- `_validate_plan_slug` importa PUBLIC_WORKOUT_LIBRARY de dentro da funcao
  (nao no topo do arquivo) de proposito: student_app/views/public_workout_views.py
  vai importar `public_workouts.services` para servir o JSON, e um import
  de modulo no topo aqui criaria import circular.
- get_active_program/publish_program/build_student_package/record_load
  rodam no schema `public`, SEM tenant (mesmo motivo do resto do app — ver
  models.py). Nunca importam nada de TENANT_APPS: quem monta o payload a
  partir de dado de tenant (a Onda A2, via parser de IA) resolve isso ANTES
  de chamar publish_program.
- S2/S3 identificam a pessoa por `account_id` (PublicWorkoutAccount.pk),
  NUNCA `student_identity_id` — decisao escrita entre as duas frentes na
  Onda A1 Fatia B (D.5): a maioria dos clientes do corredor nao e aluna de
  box. Quem tambem for aluno de box ja carrega essa referencia fraca em
  `account.student_identity_id` (Onda B1) — nao duplicada aqui.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.conf import settings
from django.db import IntegrityError
from django.db import models as django_models
from django.db import transaction

from .formulas import (
    classify_bmi,
    classify_body_fat,
    classify_whr,
    compute_bmi,
    compute_whr,
    estimate_body_fat_navy,
)
from .models import (
    PublicWorkoutAssessment,
    PublicWorkoutLoadLog,
    PublicWorkoutMovement,
    PublicWorkoutMovementModality,
    PublicWorkoutProgram,
)
from .one_rep_max import detect_one_rep_max_trend, estimate_one_rep_max
from .schema import assert_valid_payload


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


# ---------------------------------------------------------------------------
# S1 — Leitura do programa ativo (Onda A1 do CORDA). Assinatura congelada em
# D.5 desde a Onda S0 — Frente B ja consome isso contra services_stub.py.
# ---------------------------------------------------------------------------


def get_active_program(*, slug: str) -> dict | None:
    """Payload do programa ativo, ja resolvido. None se nao existe.
    Roda no schema public. Nunca toca TENANT_APPS."""
    program = PublicWorkoutProgram.objects.filter(slug=slug, is_active=True).first()
    if program is None:
        return None
    return program.payload


def _iter_movement_slugs(payload: dict):
    for day in payload.get('days', ()):
        for block in day.get('blocks', ()):
            for movement in block.get('movements', ()):
                slug = movement.get('movement_slug')
                if slug:
                    yield slug, movement.get('reference_url')


def _ensure_movements_exist(payload: dict) -> None:
    """Movimento desconhecido entra `pending` e nao bloqueia a publicacao
    (Onda A1, item 6). `modality` fica como 'strength' — melhor palpite
    disponivel aqui dentro (a maioria dos programas publicados por este
    corredor e musculacao, nao CrossFit — ver Onda A0), nao uma
    classificacao definitiva; `status=pending` sinaliza que precisa de
    revisao, igual ao extrator da Onda A0."""
    seen: dict[str, str | None] = {}
    for slug, reference_url in _iter_movement_slugs(payload):
        # payload pode repetir o mesmo movimento em blocos diferentes — fica
        # so com a primeira reference_url no-vazia encontrada.
        if slug not in seen or (not seen[slug] and reference_url):
            seen[slug] = reference_url

    existing_slugs = set(
        PublicWorkoutMovement.objects.filter(slug__in=seen.keys()).values_list('slug', flat=True)
    )
    to_create = [
        PublicWorkoutMovement(
            slug=slug,
            label_pt=slug.replace('-', ' ').capitalize(),
            reference_url=reference_url or '',
            modality=PublicWorkoutMovementModality.STRENGTH,
        )
        for slug, reference_url in seen.items()
        if slug not in existing_slugs
    ]
    if to_create:
        PublicWorkoutMovement.objects.bulk_create(to_create, ignore_conflicts=True)


def publish_program(*, slug: str, payload: dict) -> PublicWorkoutProgram:
    """Publica um novo snapshot de `slug` e ativa (D.2: o payload publicado
    e imutavel — nunca reescreve uma versao ja existente).

    Quem monta `payload` a partir de dado de TENANT_APPS (WeeklyWodPlan/
    WorkoutTemplate do box, ou o parser de IA da Onda A2) resolve isso
    ANTES de chamar esta funcao — publish_program em si roda so no schema
    public (mesma regra de get_active_program).
    """
    assert_valid_payload(payload)
    program_id = payload['program_id']

    _ensure_movements_exist(payload)

    with transaction.atomic():
        last_version = PublicWorkoutProgram.objects.filter(program_id=program_id).aggregate(
            django_models.Max('version')
        )['version__max']
        next_version = (last_version or 0) + 1

        PublicWorkoutProgram.objects.filter(slug=slug, is_active=True).update(is_active=False)

        return PublicWorkoutProgram.objects.create(
            slug=slug,
            program_id=program_id,
            program_label=payload['program_label'],
            started_on=date.fromisoformat(payload['started_on']),
            weeks=payload['weeks'],
            version=next_version,
            is_active=True,
            payload=payload,
        )


def activate_program_version(*, slug: str, program_id: str, version: int) -> PublicWorkoutProgram:
    """Ativa uma versao ja publicada (ex.: reverter v2 -> v1). Nunca cria
    linha nova — so troca qual `is_active=True` (Pronto quando #1 da A1:
    'publicar v2 e voltar pra v1 e UPDATE de uma coluna')."""
    with transaction.atomic():
        target = PublicWorkoutProgram.objects.select_for_update().get(
            slug=slug, program_id=program_id, version=version
        )
        PublicWorkoutProgram.objects.filter(slug=slug, is_active=True).exclude(pk=target.pk).update(is_active=False)
        target.is_active = True
        target.save(update_fields=['is_active'])
    return target


# ---------------------------------------------------------------------------
# S2/S3 — Pacote do aluno e escrita de carga (Onda A1, Fatia B). Assinaturas
# re-congeladas em D.5 nesta mesma onda: `account_id` no lugar de
# `student_identity_id` (ver docstring do modulo e nota de decisao na
# secao A1 do CORDA).
# ---------------------------------------------------------------------------


_DEFAULT_MAX_WEIGHT_KG = Decimal('1000')  # decisao do Renan — teto de 1 tonelada.


class LoadValueError(ValueError):
    """Levantada quando weight_kg/rir esta fora da faixa aceita — erro de
    digitacao ou dado absurdo, nao julgamento de treino. Deteccao
    estatistica de outlier de verdade (comparar com o historico do proprio
    atleta) e trabalho da Onda A3 (mesmo escopo de
    estimate_one_rep_max/deteccao de plato), nao esta faixa ampla aqui."""


def _validate_load_values(*, weight_kg, rir) -> None:
    if weight_kg is not None:
        if weight_kg < 0:
            raise LoadValueError(f'weight_kg nao pode ser negativo: {weight_kg!r}')
        max_weight_kg = Decimal(str(getattr(settings, 'PUBLIC_WORKOUT_MAX_WEIGHT_KG', _DEFAULT_MAX_WEIGHT_KG)))
        if weight_kg > max_weight_kg:
            raise LoadValueError(f'weight_kg {weight_kg!r} acima do teto aceito ({max_weight_kg} kg)')
    if rir is not None and rir < 0:
        raise LoadValueError(f'rir nao pode ser negativo: {rir!r}')


def _serialize_load_log(log: PublicWorkoutLoadLog) -> dict:
    return {
        'movement_slug': log.movement_slug,
        'weight_kg': float(log.weight_kg) if log.weight_kg is not None else None,
        'reps': log.reps,
        'rir': float(log.rir) if log.rir is not None else None,
        'performed_on': log.performed_on.isoformat(),
        'program_id': log.program_id or None,
        'week_in_program': log.week_in_program,
        'idempotency_key': log.idempotency_key,
    }


def _serialize_one_rep_max_estimate(estimate) -> dict:
    return {
        'value_kg': estimate.value_kg,
        'formula': estimate.formula,
        'confidence': estimate.confidence,
        'effective_reps': estimate.effective_reps,
    }


def build_student_package(*, account_id: int, slug: str) -> dict:
    """S2 — ultima carga por movimento + 1RM + substituicoes + access_until.
    Sem HTTP, sem request.

    `one_rep_max_by_movement`: estimativa (Onda A3, `one_rep_max.py`) a
    partir do ULTIMO set valido de cada movimento — mesmo recorte de
    "mais recente" que `last_load_by_movement` ja usa. Movimento cujo
    ultimo set passou de 15 reps efetivas fica sem entrada (a formula
    recusa estimar, nao inventa numero — ver one_rep_max.py).

    `substitutions` continua vazio de proposito: e trabalho de
    `movement_pattern` (Onda A0) revisado por quem treina, nao uma
    versao "provisoria" que arriscaria sugerir troca de exercicio errada.
    `access_until` fica `None` ate a Onda B3 (fase B) ligar a trava de
    acesso de verdade.
    """
    logs = list(
        PublicWorkoutLoadLog.objects.filter(account_id=account_id)
        .order_by('movement_slug', '-performed_on', '-created_at')
        .distinct('movement_slug')
    )

    last_load_by_movement = {log.movement_slug: _serialize_load_log(log) for log in logs}

    one_rep_max_by_movement = {}
    for log in logs:
        estimate = estimate_one_rep_max(weight_kg=log.weight_kg, reps=log.reps, rir=log.rir)
        if estimate is not None:
            one_rep_max_by_movement[log.movement_slug] = _serialize_one_rep_max_estimate(estimate)

    return {
        'last_load_by_movement': last_load_by_movement,
        'one_rep_max_by_movement': one_rep_max_by_movement,
        'substitutions': {},
        'access_until': None,
    }


def build_weekly_review(*, account_id: int) -> dict:
    """Onda A3 — agrega os SINAIS calculados (tendencia de 1RM por
    movimento) pra alimentar o review semanal (Onda 4.5 do plano de
    produto). So a parte deterministica: NAO chama IA, NAO gera texto,
    NAO le check-in/anamnese (nenhum dos dois tem coleta ainda — D4 do
    plano: "tudo que alimenta a IA comeca a coletar antes da IA existir").
    O job assincrono que junta isso com Haiku pra virar frase e prescricao
    sugerida fica pra quando esses dados existirem — aqui so preparamos o
    sinal, no formato "platô de 3 semanas", nao a tabela crua de sets.
    """
    movement_slugs = (
        PublicWorkoutLoadLog.objects.filter(account_id=account_id)
        .order_by('movement_slug')
        .values_list('movement_slug', flat=True)
        .distinct()
    )

    trends = {}
    for movement_slug in movement_slugs:
        trend = detect_one_rep_max_trend(account_id=account_id, movement_slug=movement_slug)
        if trend.label == 'insufficient_data':
            continue
        trends[movement_slug] = {
            'label': trend.label,
            'weekly_estimates_kg': list(trend.weekly_estimates_kg),
        }

    declining = sorted(slug for slug, t in trends.items() if t['label'] == 'declining')
    plateaued = sorted(slug for slug, t in trends.items() if t['label'] == 'plateau')

    return {
        'trends_by_movement': trends,
        'declining_movements': declining,
        'plateaued_movements': plateaued,
    }


def record_load(
    *,
    account_id: int,
    movement_slug: str,
    weight_kg,
    reps=None,
    rir=None,
    performed_on,
    program_id=None,
    week_in_program=None,
    idempotency_key: str,
) -> dict:
    """S3 — registra uma carga. Idempotente por `idempotency_key`: reenvio
    (outbox offline da Onda B3) resolve pro registro ja existente, nunca
    duplica linha — o banco (`unique=True`) e a trava, mesmo padrao do
    dedup de `PaymentWebhookEvent` na Onda B2, nao um SELECT antes do
    INSERT (janela de corrida entre checar e criar).

    O `create()` roda dentro do proprio `transaction.atomic()` (savepoint):
    um IntegrityError "envenena" a transacao corrente ate o rollback —
    sem o savepoint, o SELECT de recuperacao logo abaixo levantaria
    TransactionManagementError em vez de achar a linha (mesma pegadinha
    que o dedup do webhook em stripe_handlers.py evita nunca re-consultando
    na mesma transacao; aqui precisamos do valor de volta, entao isolamos
    o INSERT em vez disso)."""
    _validate_load_values(weight_kg=weight_kg, rir=rir)

    if isinstance(performed_on, str):
        performed_on = date.fromisoformat(performed_on)

    try:
        with transaction.atomic():
            log = PublicWorkoutLoadLog.objects.create(
                account_id=account_id,
                movement_slug=movement_slug,
                weight_kg=weight_kg,
                reps=reps,
                rir=rir,
                performed_on=performed_on,
                program_id=program_id or '',
                week_in_program=week_in_program,
                idempotency_key=idempotency_key,
            )
    except IntegrityError:
        log = PublicWorkoutLoadLog.objects.get(idempotency_key=idempotency_key)

    return _serialize_load_log(log)
