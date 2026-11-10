"""
ARQUIVO: analytics do treinador (Curva) -- adesao, uso do app, execucao,
carga e horario de treino numa leitura so, com a DECISAO sugerida por aluno.

POR QUE ELE EXISTE:
- O roster (views.CoachStudentRosterView) responde "quem esta em risco";
  esta leitura responde "o que esta acontecendo com o treino" -- se o
  aluno abre o treino, se abre no celular, se termina a sessao, se a carga
  sobe, se o RIR mostra treino facil/dificil demais -- e transforma cada
  sinal numa acao concreta (chamar, subir carga, encurtar sessao...).

PONTOS CRITICOS:
- Deterministico de proposito (mesmo espirito de risk_signals.py): toda
  acao sugerida vem com o MOTIVO em texto, nunca um score misterioso.
- Thresholds abaixo sao palpite inicial -- constantes no topo pra ajustar
  num lugar so.
- Poucas queries em lote (uma por fonte), agregacao em Python: a escala
  real hoje e' dezenas de alunos, nao milhares.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, Max, Q
from django.utils import timezone

from .models import (
    PublicWorkoutLoadLog,
    PublicWorkoutMovement,
    PublicWorkoutProgramOpen,
    PublicWorkoutProgramOpenDevice,
    PublicWorkoutPushSubscription,
    PublicWorkoutSubscription,
    PublicWorkoutSubscriptionStatus,
    PublicWorkoutTrainingSession,
    PublicWorkoutTrainingSet,
)

WINDOW_CHOICES = (7, 30, 90)
DEFAULT_WINDOW_DAYS = 30
TREND_WEEKS = 8

OPEN_DEDUPE_MINUTES = 30
STALE_TRAINING_DAYS = 10
TARGET_DAYS_PER_WEEK = 2.0
OPENS_WITHOUT_TRAINING_MIN = 2
LOW_COMPLETION_PERCENT = 60
EASY_RIR = Decimal('3')
HARD_RIR = Decimal('0.5')
MIN_SETS_FOR_RIR = 6
VOLUME_DROP_PERCENT = 25
ABANDONED_AFTER_HOURS = 72
EXERCISE_STALL_MIN_STUDENTS = 2
TOP_GAINS = 5
SPARK_WIDTH = 100
SPARK_HEIGHT = 28

TREND_LABELS = {
    'improving': 'subindo', 'plateau': 'platô', 'declining': 'caindo', 'insufficient_data': 'poucos dados',
}
_TREND_ORDER = {'declining': 0, 'plateau': 1, 'improving': 2, 'insufficient_data': 3}

_WORKING_SET_EXCLUDED_ROLES = ('warmup', 'feeder')
_MOBILE_UA = re.compile(r'Mobi|Android|iPhone|iPod|Windows Phone', re.IGNORECASE)
_TABLET_UA = re.compile(r'iPad|Tablet|Android(?!.*Mobile)', re.IGNORECASE)

# Ordem = prioridade na tela de decisoes (o que aparece primeiro).
ACTIONS = {
    'reengage': {'tone': 'act', 'title': 'Sumiram do treino', 'cta': 'Chamar no WhatsApp'},
    'opens_no_train': {'tone': 'act', 'title': 'Abrem o treino, mas não treinam', 'cta': 'Perguntar o que trava'},
    'abandons': {'tone': 'act', 'title': 'Largam a sessão no meio', 'cta': 'Encurtar ou rever volume'},
    'too_easy': {'tone': 'adjust', 'title': 'Treino fácil demais (RIR alto)', 'cta': 'Subir carga'},
    'too_hard': {'tone': 'adjust', 'title': 'No limite (RIR perto de 0)', 'cta': 'Rever carga / fadiga'},
    'volume_drop': {'tone': 'adjust', 'title': 'Volume de carga caiu', 'cta': 'Checar rotina e dor'},
    'low_frequency': {'tone': 'adjust', 'title': 'Frequência abaixo da meta', 'cta': 'Combinar dias fixos'},
    'celebrate': {'tone': 'celebrate', 'title': 'Bateram recorde', 'cta': 'Parabenizar'},
    'no_push': {'tone': 'nudge', 'title': 'Sem lembrete no celular', 'cta': 'Pedir pra ativar notificação'},
}

_TIME_BUCKETS = (
    ('madrugada', 'Madrugada', range(0, 6)),
    ('manha', 'Manhã', range(6, 12)),
    ('tarde', 'Tarde', range(12, 18)),
    ('noite', 'Noite', range(18, 24)),
)
_WEEKDAYS = ('Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom')


def classify_device(user_agent: str) -> str:
    if not user_agent:
        return PublicWorkoutProgramOpenDevice.UNKNOWN
    if _TABLET_UA.search(user_agent):
        return PublicWorkoutProgramOpenDevice.TABLET
    if _MOBILE_UA.search(user_agent):
        return PublicWorkoutProgramOpenDevice.MOBILE
    return PublicWorkoutProgramOpenDevice.DESKTOP


def record_program_open(*, account, plan_slug: str, user_agent: str, at=None) -> PublicWorkoutProgramOpen | None:
    """Registra que o aluno abriu o treino. Recarregar a pagina dentro de
    OPEN_DEDUPE_MINUTES no mesmo dispositivo nao conta como abertura nova."""
    at = at or timezone.now()
    device = classify_device(user_agent)
    recent = PublicWorkoutProgramOpen.objects.filter(
        account=account, device=device, opened_at__gte=at - timedelta(minutes=OPEN_DEDUPE_MINUTES),
    ).exists()
    if recent:
        return None
    return PublicWorkoutProgramOpen.objects.create(
        account=account, plan_slug=plan_slug or '', device=device, opened_at=at,
    )


def _local_date(value):
    return timezone.localtime(value).date()


def _percent(part, whole):
    return round(part * 100 / whole) if whole else None


def _delta_percent(current, previous):
    if not previous:
        return None
    return round((current - previous) * 100 / previous)


def build_coach_analytics(*, window_days: int = DEFAULT_WINDOW_DAYS, today=None) -> dict:
    from student_app.views.public_workout_views import PUBLIC_WORKOUT_LIBRARY

    from .views import _build_checkin_whatsapp_url

    if window_days not in WINDOW_CHOICES:
        window_days = DEFAULT_WINDOW_DAYS
    today = today or timezone.localdate()
    start = today - timedelta(days=window_days - 1)
    prev_start = start - timedelta(days=window_days)
    trend_start = today - timedelta(days=today.weekday()) - timedelta(weeks=TREND_WEEKS - 1)
    fetch_from = min(prev_start, trend_start)
    now = timezone.now()

    subscriptions = list(
        PublicWorkoutSubscription.objects.exclude(status=PublicWorkoutSubscriptionStatus.CANCELED)
        .select_related('account')
    )
    account_ids = [sub.account_id for sub in subscriptions]

    # Treino por (aluno, dia) -- carga registrada OU sessao guiada com serie feita.
    training_days: dict[int, set] = defaultdict(set)
    first_touch_by_day: dict[tuple, object] = {}
    tonnage = defaultdict(lambda: {'current': Decimal('0'), 'previous': Decimal('0')})
    rir_values: dict[int, list] = defaultdict(list)
    records: Counter = Counter()

    load_logs = PublicWorkoutLoadLog.objects.filter(
        account_id__in=account_ids, is_active=True, performed_on__gte=fetch_from, performed_on__lte=today,
    ).values_list('account_id', 'performed_on', 'weight_kg', 'reps', 'rir', 'set_role', 'achievement_kind', 'created_at')
    for account_id, performed_on, weight, reps, rir, set_role, achievement, created_at in load_logs:
        training_days[account_id].add(performed_on)
        key = (account_id, performed_on)
        if key not in first_touch_by_day or created_at < first_touch_by_day[key]:
            first_touch_by_day[key] = created_at
        if set_role in _WORKING_SET_EXCLUDED_ROLES:
            continue
        bucket = 'current' if performed_on >= start else ('previous' if performed_on >= prev_start else None)
        if bucket and weight is not None and reps:
            tonnage[account_id][bucket] += weight * reps
        if bucket == 'current':
            if rir is not None:
                rir_values[account_id].append(rir)
            if achievement:
                records[account_id] += 1

    sessions_by_account: dict[int, list] = defaultdict(list)
    for row in PublicWorkoutTrainingSession.objects.filter(
        account_id__in=account_ids, started_at__date__gte=fetch_from,
    ).values('account_id', 'started_at', 'completed_at', 'ended_at', 'outcome', 'completed_set_count'):
        day = _local_date(row['started_at'])
        if row['completed_set_count'] or row['completed_at']:
            training_days[row['account_id']].add(day)
            key = (row['account_id'], day)
            if key not in first_touch_by_day or row['started_at'] < first_touch_by_day[key]:
                first_touch_by_day[key] = row['started_at']
        if day >= start:
            sessions_by_account[row['account_id']].append(row)

    set_status = defaultdict(Counter)
    for account_id, status, total in PublicWorkoutTrainingSet.objects.filter(
        session__account_id__in=account_ids, session__started_at__date__gte=start,
    ).values_list('session__account_id', 'status').annotate(total=Count('pk')):
        set_status[account_id][status] = total

    opens_by_account: dict[int, list] = defaultdict(list)
    for account_id, opened_at, device in PublicWorkoutProgramOpen.objects.filter(
        account_id__in=account_ids, opened_at__date__gte=fetch_from,
    ).values_list('account_id', 'opened_at', 'device'):
        opens_by_account[account_id].append((_local_date(opened_at), device))

    last_workout = dict(
        PublicWorkoutLoadLog.objects.filter(account_id__in=account_ids, is_active=True)
        .values('account_id').annotate(last=Max('performed_on')).values_list('account_id', 'last')
    )
    for account_id, days in training_days.items():
        if days:
            last_workout[account_id] = max(max(days), last_workout.get(account_id) or max(days))
    last_open = {
        account_id: _local_date(value) for account_id, value in
        PublicWorkoutProgramOpen.objects.filter(account_id__in=account_ids)
        .values('account_id').annotate(last=Max('opened_at')).values_list('account_id', 'last')
    }
    push_enabled = set(
        PublicWorkoutPushSubscription.objects.filter(account_id__in=account_ids, revoked_at__isnull=True)
        .values_list('account_id', flat=True)
    )

    weeks_in_window = window_days / 7
    students = []
    for sub in subscriptions:
        account_id = sub.account_id
        plan = PUBLIC_WORKOUT_LIBRARY.get(sub.plan_slug or '')
        label = plan.short_name if plan else sub.account.email
        days = training_days.get(account_id, set())
        current_days = {d for d in days if d >= start}
        previous_days = {d for d in days if prev_start <= d < start}
        opens = [(d, device) for d, device in opens_by_account.get(account_id, []) if d >= start]
        open_days = {d for d, _ in opens}
        mobile_opens = sum(1 for _, device in opens if device in ('mobile', 'tablet'))
        sessions = sessions_by_account.get(account_id, [])
        completed = [s for s in sessions if s['completed_at']]
        abandoned = [
            s for s in sessions
            if s['outcome'] in ('abandoned', 'partial')
            or (s['ended_at'] is None and s['completed_at'] is None
                and s['started_at'] <= now - timedelta(hours=ABANDONED_AFTER_HOURS))
        ]
        durations = [
            (s['completed_at'] - s['started_at']).total_seconds() / 60
            for s in completed if s['completed_at'] > s['started_at']
        ]
        rirs = rir_values.get(account_id, [])
        avg_rir = (sum(rirs) / len(rirs)).quantize(Decimal('0.1')) if rirs else None
        volume_now = tonnage[account_id]['current'] if account_id in tonnage else Decimal('0')
        volume_prev = tonnage[account_id]['previous'] if account_id in tonnage else Decimal('0')
        volume_delta = _delta_percent(volume_now, volume_prev)
        last_day = last_workout.get(account_id)
        days_since = (today - last_day).days if last_day else None
        sets_done = set_status[account_id]['performed']
        sets_skipped = set_status[account_id]['skipped']

        student = {
            'account_id': account_id,
            'label': label,
            'email': sub.account.email,
            'tier': sub.get_tier_display(),
            'days_trained': len(current_days),
            'days_trained_previous': len(previous_days),
            'days_per_week': round(len(current_days) / weeks_in_window, 1),
            'opens': len(opens),
            'open_days': len(open_days),
            'opens_without_training': len(open_days - current_days),
            'open_to_train_percent': _percent(len(open_days & current_days), len(open_days)),
            'mobile_opens': mobile_opens,
            'mobile_percent': _percent(mobile_opens, len(opens)),
            'sessions_started': len(sessions),
            'sessions_completed': len(completed),
            'sessions_abandoned': len(abandoned),
            'completion_percent': _percent(len(completed), len(sessions)),
            'avg_session_minutes': round(sum(durations) / len(durations)) if durations else None,
            'skipped_percent': _percent(sets_skipped, sets_done + sets_skipped),
            'avg_rir': avg_rir,
            'rir_sample': len(rirs),
            'volume_kg': int(volume_now),
            'volume_delta_percent': volume_delta,
            'records': records[account_id],
            'days_since_last_workout': days_since,
            'last_workout_on': last_day,
            'last_open_on': last_open.get(account_id),
            'push_enabled': account_id in push_enabled,
            'whatsapp_url': _build_checkin_whatsapp_url(phone=sub.account.whatsapp, student_label=label),
        }
        student['actions'] = _suggest_actions(student)
        student['tone'] = student['actions'][0]['tone'] if student['actions'] else 'ok'
        students.append(student)

    tone_order = {'act': 0, 'adjust': 1, 'celebrate': 2, 'nudge': 3, 'ok': 4}
    students.sort(key=lambda s: (
        tone_order[s['tone']], -(s['days_since_last_workout'] if s['days_since_last_workout'] is not None else 9999),
    ))

    return {
        'window_days': window_days,
        'window_choices': WINDOW_CHOICES,
        'start': start,
        'today': today,
        'students': students,
        'decisions': _group_decisions(students),
        'kpis': _build_kpis(students),
        'weekly_trend': _build_weekly_trend(training_days, opens_by_account, trend_start, today),
        'time_heatmap': _build_time_heatmap(first_touch_by_day, start),
        'device_split': _build_device_split(opens_by_account, start),
        'load_evolution': _build_load_evolution(
            [(s['account_id'], s['label']) for s in students], start=start, today=today,
        ),
    }


def _suggest_actions(s: dict) -> list[dict]:
    found = []

    def add(key, reason):
        found.append({'key': key, 'reason': reason, **ACTIONS[key]})

    if s['days_since_last_workout'] is None:
        add('reengage', 'nunca registrou treino')
    elif s['days_since_last_workout'] >= STALE_TRAINING_DAYS:
        add('reengage', f"{s['days_since_last_workout']} dias sem treinar")
    if s['opens_without_training'] >= OPENS_WITHOUT_TRAINING_MIN:
        add('opens_no_train', f"abriu em {s['opens_without_training']} dia(s) sem registrar treino")
    if s['sessions_abandoned'] >= 2 and (s['completion_percent'] or 0) < LOW_COMPLETION_PERCENT:
        add('abandons', f"{s['sessions_abandoned']} sessão(ões) sem terminar · conclusão {s['completion_percent']}%")
    if s['avg_rir'] is not None and s['rir_sample'] >= MIN_SETS_FOR_RIR:
        if s['avg_rir'] >= EASY_RIR:
            add('too_easy', f"RIR médio {s['avg_rir']}")
        elif s['avg_rir'] <= HARD_RIR:
            add('too_hard', f"RIR médio {s['avg_rir']}")
    if s['volume_delta_percent'] is not None and s['volume_delta_percent'] <= -VOLUME_DROP_PERCENT:
        add('volume_drop', f"{s['volume_delta_percent']}% vs período anterior")
    if s['days_trained'] and s['days_per_week'] < TARGET_DAYS_PER_WEEK:
        add('low_frequency', f"{s['days_per_week']} dia(s)/semana")
    if s['records']:
        add('celebrate', f"{s['records']} recorde(s) de carga")
    if not s['push_enabled']:
        add('no_push', 'notificações desativadas')
    order = list(ACTIONS)
    found.sort(key=lambda a: order.index(a['key']))
    return found


def _group_decisions(students: list[dict]) -> list[dict]:
    groups = {key: {'key': key, **meta, 'students': []} for key, meta in ACTIONS.items()}
    for student in students:
        for action in student['actions']:
            groups[action['key']]['students'].append({
                'account_id': student['account_id'], 'label': student['label'],
                'reason': action['reason'], 'whatsapp_url': student['whatsapp_url'],
            })
    return [group for group in groups.values() if group['students']]


def _build_kpis(students: list[dict]) -> list[dict]:
    total = len(students)
    active_now = sum(1 for s in students if s['days_trained'])
    active_prev = sum(1 for s in students if s['days_trained_previous'])
    days_now = sum(s['days_trained'] for s in students)
    days_prev = sum(s['days_trained_previous'] for s in students)
    avg_freq = round(sum(s['days_per_week'] for s in students) / total, 1) if total else 0
    open_days = sum(s['open_days'] for s in students)
    converted = sum(s['open_days'] - s['opens_without_training'] for s in students)
    opens = sum(s['opens'] for s in students)
    mobile = sum(s['mobile_opens'] for s in students)
    started = sum(s['sessions_started'] for s in students)
    completed = sum(s['sessions_completed'] for s in students)
    on_target = sum(1 for s in students if s['days_per_week'] >= TARGET_DAYS_PER_WEEK)
    return [
        {'key': 'active', 'label': 'Treinando', 'value': f'{active_now}/{total}',
         'hint': 'alunos com ao menos 1 treino', 'delta': _delta_percent(active_now, active_prev)},
        {'key': 'frequency', 'label': 'Frequência média', 'value': f'{avg_freq}x',
         'hint': 'dias de treino por semana', 'delta': _delta_percent(days_now, days_prev)},
        {'key': 'on_target', 'label': 'Na meta', 'value': f'{_percent(on_target, total) or 0}%',
         'hint': f'treinam {TARGET_DAYS_PER_WEEK:g}x+ por semana', 'delta': None},
        {'key': 'open_to_train', 'label': 'Abriu → treinou', 'value': _fmt_percent(_percent(converted, open_days)),
         'hint': 'dias que abriram o treino e treinaram', 'delta': None},
        {'key': 'mobile', 'label': 'Abrem no celular', 'value': _fmt_percent(_percent(mobile, opens)),
         'hint': f'{opens} abertura(s) no período', 'delta': None},
        {'key': 'completion', 'label': 'Sessões concluídas', 'value': _fmt_percent(_percent(completed, started)),
         'hint': f'{completed} de {started} sessão(ões) guiadas', 'delta': None},
        {'key': 'records', 'label': 'Recordes de carga', 'value': str(sum(s['records'] for s in students)),
         'hint': 'novas maiores cargas no período', 'delta': None},
        {'key': 'push', 'label': 'Lembrete ativo', 'value': _fmt_percent(_percent(sum(s['push_enabled'] for s in students), total)),
         'hint': 'alunos com notificação no celular', 'delta': None},
    ]


def _fmt_percent(value):
    return '—' if value is None else f'{value}%'


def _build_weekly_trend(training_days, opens_by_account, trend_start, today) -> list[dict]:
    weeks = []
    for index in range(TREND_WEEKS):
        week_start = trend_start + timedelta(weeks=index)
        week_end = week_start + timedelta(days=6)
        trained = [
            account_id for account_id, days in training_days.items()
            if any(week_start <= d <= week_end for d in days)
        ]
        sessions = sum(sum(1 for d in days if week_start <= d <= week_end) for days in training_days.values())
        opens = sum(sum(1 for d, _ in rows if week_start <= d <= week_end) for rows in opens_by_account.values())
        weeks.append({
            'label': week_start.strftime('%d/%m'), 'students': len(trained), 'training_days': sessions,
            'opens': opens, 'is_current': week_start <= today <= week_end,
        })
    peak = max([w['training_days'] for w in weeks] + [w['opens'] for w in weeks] + [1])
    for week in weeks:
        week['training_height'] = round(week['training_days'] * 100 / peak)
        week['opens_height'] = round(week['opens'] * 100 / peak)
    return weeks


def _build_time_heatmap(first_touch_by_day, start) -> dict:
    grid = Counter()
    for (_account_id, day), moment in first_touch_by_day.items():
        if day < start:
            continue
        hour = timezone.localtime(moment).hour
        bucket = next(key for key, _label, hours in _TIME_BUCKETS if hour in hours)
        grid[(day.weekday(), bucket)] += 1
    peak = max(grid.values(), default=0)
    rows = []
    for key, label, _hours in _TIME_BUCKETS:
        cells = []
        for weekday in range(7):
            value = grid[(weekday, key)]
            cells.append({'value': value, 'level': 0 if not peak or not value else min(4, 1 + value * 4 // (peak + 1))})
        rows.append({'label': label, 'cells': cells})
    best = max(grid.items(), key=lambda item: item[1], default=None)
    best_label = None
    if best:
        (weekday, bucket), _count = best
        best_label = f"{_WEEKDAYS[weekday]} · {next(label for key, label, _ in _TIME_BUCKETS if key == bucket)}"
    return {'weekdays': _WEEKDAYS, 'rows': rows, 'best_slot': best_label, 'total': sum(grid.values())}


def _sparkline_points(values: list) -> str:
    if len(values) < 2:
        return ''
    low, high = min(values), max(values)
    span = (high - low) or 1
    step = SPARK_WIDTH / (len(values) - 1)
    return ' '.join(
        f'{index * step:.1f},{SPARK_HEIGHT - 2 - (value - low) * (SPARK_HEIGHT - 4) / span:.1f}'
        for index, value in enumerate(values)
    )


def _movement_evolution(snapshot, *, start) -> dict | None:
    """Antes -> agora de UM exercicio no periodo. Base = ultima serie
    principal ANTES do periodo (se houver), senao a primeira dentro dele --
    assim 'evolucao' compara o aluno com ele mesmo no inicio do periodo."""
    points = [p for p in snapshot.curve_points if p.weight_kg is not None]
    latest = snapshot.latest_top_set
    if not points or latest is None or latest.weight_kg is None:
        return None
    before = [p for p in points if p.performed_on < start]
    inside = [p for p in points if p.performed_on >= start]
    if not inside:
        return None
    baseline = before[-1] if before else inside[0]
    delta_kg = latest.weight_kg - baseline.weight_kg
    estimates = list(snapshot.weekly_estimates_kg)
    spark_values = estimates if len(estimates) >= 2 else [float(p.weight_kg) for p in points]
    return {
        'baseline_kg': _kg(baseline.weight_kg),
        'current_kg': _kg(latest.weight_kg),
        'current_reps': latest.reps,
        'delta_kg': delta_kg,
        'delta_kg_label': _kg(delta_kg, signed=True),
        'delta_percent': _delta_percent(latest.weight_kg, baseline.weight_kg),
        'one_rep_max_kg': round(snapshot.one_rep_max.value_kg) if snapshot.one_rep_max else None,
        'trend': snapshot.trend_signal,
        'trend_label': TREND_LABELS.get(snapshot.trend_signal, TREND_LABELS['insufficient_data']),
        'sessions': len(inside),
        'last_on': latest.performed_on,
        'spark_points': _sparkline_points(spark_values),
    }


def _build_load_evolution(students: list[tuple], *, start, today) -> dict:
    from .progress_snapshot import build_progress_snapshots

    per_student = []
    by_movement: dict[str, list] = defaultdict(list)
    for account_id, label in students:
        movements = []
        for slug, snapshot in build_progress_snapshots(account_id=account_id, as_of=today).items():
            evolution = _movement_evolution(snapshot, start=start)
            if evolution is None:
                continue
            evolution['slug'] = slug
            movements.append(evolution)
            by_movement[slug].append({**evolution, 'account_id': account_id, 'student_label': label})
        if not movements:
            continue
        counts = Counter(m['trend'] for m in movements)
        movements.sort(key=lambda m: (_TREND_ORDER.get(m['trend'], 9), -(m['delta_percent'] or 0)))
        per_student.append({
            'account_id': account_id, 'label': label, 'movements': movements,
            'improving': counts['improving'], 'plateau': counts['plateau'], 'declining': counts['declining'],
            'avg_delta_percent': _average([m['delta_percent'] for m in movements]),
        })

    labels = dict(PublicWorkoutMovement.objects.filter(slug__in=by_movement).values_list('slug', 'label_pt'))
    for student in per_student:
        for movement in student['movements']:
            movement['label'] = labels.get(movement['slug'], movement['slug'])
    exercises = []
    for slug, rows in by_movement.items():
        counts = Counter(row['trend'] for row in rows)
        stalled = counts['plateau'] + counts['declining']
        exercises.append({
            'slug': slug, 'label': labels.get(slug, slug), 'students': len(rows),
            'improving': counts['improving'], 'plateau': counts['plateau'], 'declining': counts['declining'],
            'avg_delta_percent': _average([row['delta_percent'] for row in rows]),
            'is_stalled': len(rows) >= EXERCISE_STALL_MIN_STUDENTS and stalled * 2 >= len(rows),
        })
    exercises.sort(key=lambda e: (-e['students'], e['label']))
    gains = sorted(
        (row for rows in by_movement.values() for row in rows if row['delta_kg'] > 0),
        key=lambda row: (-(row['delta_percent'] or 0), -row['delta_kg']),
    )[:TOP_GAINS]
    for row in gains:
        row['label'] = labels.get(row['slug'], row['slug'])
    per_student.sort(key=lambda s: (-(s['declining'] + s['plateau']), s['label']))
    return {
        'students': per_student,
        'exercises': exercises,
        'stalled_exercises': [e for e in exercises if e['is_stalled']],
        'top_gains': gains,
        'spark_viewbox': f'0 0 {SPARK_WIDTH} {SPARK_HEIGHT}',
    }


def _kg(value: Decimal, *, signed: bool = False) -> str:
    text = format(value.normalize(), 'f').replace('.', ',')
    return f'+{text}' if signed and value > 0 else text


def _average(values: list):
    values = [v for v in values if v is not None]
    return round(sum(values) / len(values)) if values else None


def _build_device_split(opens_by_account, start) -> list[dict]:
    counts = Counter(device for rows in opens_by_account.values() for d, device in rows if d >= start)
    total = sum(counts.values())
    labels = dict(PublicWorkoutProgramOpenDevice.choices)
    return [
        {'key': key, 'label': labels[key], 'count': counts[key], 'percent': _percent(counts[key], total) or 0}
        for key in ('mobile', 'tablet', 'desktop', 'unknown') if counts[key]
    ]


__all__ = [
    'ACTIONS', 'DEFAULT_WINDOW_DAYS', 'WINDOW_CHOICES', 'build_coach_analytics', 'classify_device',
    'record_program_open',
]
