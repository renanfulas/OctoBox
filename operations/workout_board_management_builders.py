"""
ARQUIVO: builders de management da board de aprovacao do WOD.

POR QUE ELE EXISTE:
- tira de `workout_board_builders.py` a leitura de alavancas, alertas e fila de RM.
"""

from django.utils import timezone

from student_app.models import WorkoutOperationalMemoryKind, WorkoutRmGapActionStatus


def build_operational_memory_patterns(*, history_items):
    reception_case_count = 0
    coach_case_count = 0
    coach_resolved_case_count = 0
    whatsapp_case_count = 0
    monitoring_case_count = 0
    custom_case_count = 0

    for item in history_items:
        memory_kinds = set(item.get('operational_memory_kinds') or [])
        closure_status = (item.get('executive_closure') or {}).get('status')
        if WorkoutOperationalMemoryKind.RECEPTION_OWNED in memory_kinds:
            reception_case_count += 1
        if WorkoutOperationalMemoryKind.COACH_ALIGNED in memory_kinds:
            coach_case_count += 1
            if closure_status == 'absorbed':
                coach_resolved_case_count += 1
        if WorkoutOperationalMemoryKind.WHATSAPP_SENT in memory_kinds:
            whatsapp_case_count += 1
        if WorkoutOperationalMemoryKind.MONITORING_NOTE in memory_kinds:
            monitoring_case_count += 1
        if WorkoutOperationalMemoryKind.CUSTOM in memory_kinds:
            custom_case_count += 1

    patterns = [
        {
            'label': 'Casos que precisaram de recepção',
            'value': reception_case_count,
            'tone': 'info',
            'copy': 'Conta casos em que a recepção ou operação de balcão assumiu a bola em algum momento.',
        },
        {
            'label': 'Casos absorvidos com coach',
            'value': coach_resolved_case_count,
            'tone': 'success',
            'copy': 'Conta casos que tiveram coach alinhado e hoje já aparecem como absorvidos na leitura executiva.',
        },
        {
            'label': 'Casos que dependeram de WhatsApp',
            'value': whatsapp_case_count,
            'tone': 'warning',
            'copy': 'Conta casos em que reforço de comunicação entrou na história operacional daquele WOD.',
        },
    ]
    return {
        'reception_case_count': reception_case_count,
        'coach_case_count': coach_case_count,
        'coach_resolved_case_count': coach_resolved_case_count,
        'whatsapp_case_count': whatsapp_case_count,
        'monitoring_case_count': monitoring_case_count,
        'custom_case_count': custom_case_count,
        'patterns': patterns,
    }


def build_operational_leverage_summary(*, history_items):
    leverage_specs = (
        (WorkoutOperationalMemoryKind.RECEPTION_OWNED, 'Recepcao assumiu', 'info'),
        (WorkoutOperationalMemoryKind.COACH_ALIGNED, 'Coach alinhado', 'success'),
        (WorkoutOperationalMemoryKind.WHATSAPP_SENT, 'WhatsApp disparado', 'warning'),
        (WorkoutOperationalMemoryKind.MONITORING_NOTE, 'Nota de monitoramento', 'accent'),
        (WorkoutOperationalMemoryKind.CUSTOM, 'Marco livre', 'info'),
    )
    cards = []
    for memory_kind, label, tone in leverage_specs:
        total = 0
        absorbed = 0
        monitoring = 0
        awaiting_action = 0
        strong_intervention = 0
        for item in history_items:
            memory_kinds = set(item.get('operational_memory_kinds') or [])
            if memory_kind not in memory_kinds:
                continue
            total += 1
            closure_status = (item.get('executive_closure') or {}).get('status')
            if closure_status == 'absorbed':
                absorbed += 1
            elif closure_status == 'monitoring':
                monitoring += 1
            elif closure_status == 'awaiting_action':
                awaiting_action += 1
            elif closure_status == 'strong_intervention':
                strong_intervention += 1
        if total == 0:
            continue
        absorption_rate = round((absorbed / total) * 100)
        if absorption_rate >= 70:
            efficiency_tone = 'success'
            efficiency_label = 'Boa alavanca de absorção'
        elif absorption_rate >= 40:
            efficiency_tone = 'accent'
            efficiency_label = 'Alavanca em observação'
        else:
            efficiency_tone = 'warning'
            efficiency_label = 'Alavanca ainda pesada'
        cards.append(
            {
                'label': label,
                'tone': tone,
                'total': total,
                'absorbed': absorbed,
                'monitoring': monitoring,
                'awaiting_action': awaiting_action,
                'strong_intervention': strong_intervention,
                'absorption_rate_label': f'{absorption_rate}%',
                'efficiency_tone': efficiency_tone,
                'efficiency_label': efficiency_label,
                'summary': f'{label} absorveu {absorbed} de {total} caso(s) observados nesta janela.',
            }
        )
    cards.sort(key=lambda card: (-card['absorbed'], -card['total'], card['label']))
    return {
        'cards': cards[:4],
        'total_tracked_levers': len(cards),
    }


def _calculate_leverage_window_metrics(history_items, memory_kind):
    total = 0
    absorbed = 0
    for item in history_items:
        memory_kinds = set(item.get('operational_memory_kinds') or [])
        if memory_kind not in memory_kinds:
            continue
        total += 1
        closure_status = (item.get('executive_closure') or {}).get('status')
        if closure_status == 'absorbed':
            absorbed += 1
    rate = round((absorbed / total) * 100) if total else None
    return {
        'total': total,
        'absorbed': absorbed,
        'rate': rate,
    }


def build_operational_leverage_trends(*, history_items):
    if len(history_items) < 2:
        return {'cards': []}

    split_index = max(1, len(history_items) // 2)
    recent_items = history_items[:split_index]
    previous_items = history_items[split_index:]
    leverage_specs = (
        (WorkoutOperationalMemoryKind.RECEPTION_OWNED, 'Recepcao assumiu', 'info'),
        (WorkoutOperationalMemoryKind.COACH_ALIGNED, 'Coach alinhado', 'success'),
        (WorkoutOperationalMemoryKind.WHATSAPP_SENT, 'WhatsApp disparado', 'warning'),
        (WorkoutOperationalMemoryKind.MONITORING_NOTE, 'Nota de monitoramento', 'accent'),
        (WorkoutOperationalMemoryKind.CUSTOM, 'Marco livre', 'info'),
    )
    cards = []
    for memory_kind, label, tone in leverage_specs:
        recent_metrics = _calculate_leverage_window_metrics(recent_items, memory_kind)
        previous_metrics = _calculate_leverage_window_metrics(previous_items, memory_kind)
        if not recent_metrics['total'] and not previous_metrics['total']:
            continue

        recent_rate = recent_metrics['rate']
        previous_rate = previous_metrics['rate']
        if recent_rate is None or previous_rate is None:
            trend_tone = 'accent'
            trend_label = 'Base curta'
            trend_summary = 'Ainda nao ha massa suficiente nas duas metades da janela para chamar tendencia com firmeza.'
        else:
            delta = recent_rate - previous_rate
            if delta >= 20:
                trend_tone = 'success'
                trend_label = 'Melhora recente'
                trend_summary = f'A taxa de absorcao subiu de {previous_rate}% para {recent_rate}% na metade mais recente.'
            elif delta <= -20:
                trend_tone = 'warning'
                trend_label = 'Sinal de desgaste'
                trend_summary = f'A taxa de absorcao caiu de {previous_rate}% para {recent_rate}% na metade mais recente.'
            else:
                trend_tone = 'info'
                trend_label = 'Estavel'
                trend_summary = f'A taxa de absorcao ficou perto de estavel, saindo de {previous_rate}% para {recent_rate}% na metade mais recente.'

        cards.append(
            {
                'label': label,
                'tone': tone,
                'trend_tone': trend_tone,
                'trend_label': trend_label,
                'trend_summary': trend_summary,
                'recent_total': recent_metrics['total'],
                'recent_rate_label': f"{recent_rate}%" if recent_rate is not None else 'Sem base',
                'previous_total': previous_metrics['total'],
                'previous_rate_label': f"{previous_rate}%" if previous_rate is not None else 'Sem base',
            }
        )
    return {
        'cards': cards[:4],
    }


def build_operational_management_alerts(*, trend_cards):
    alerts = []
    for card in trend_cards:
        if card['trend_label'] == 'Sinal de desgaste':
            alerts.append(
                {
                    'tone': 'warning',
                    'label': f"{card['label']} em desgaste recorrente",
                    'summary': card['trend_summary'],
                    'recommendation': 'Vale revisar processo, treinamento ou reforco operacional antes que esse corredor fique caro demais.',
                    'trend_label': card['trend_label'],
                    'recent_total': card['recent_total'],
                }
            )
        elif card['trend_label'] == 'Melhora recente':
            alerts.append(
                {
                    'tone': 'success',
                    'label': f"{card['label']} em melhora consistente",
                    'summary': card['trend_summary'],
                    'recommendation': 'Vale consolidar esse corredor como boa pratica curta do box enquanto o sinal continua forte.',
                    'trend_label': card['trend_label'],
                    'recent_total': card['recent_total'],
                }
            )
    return alerts[:4]


def build_rm_readiness_management_alerts(*, history_items):
    rm_items = [item for item in history_items if (item.get('rm_readiness') or {}).get('has_percentage_rm')]
    if not rm_items:
        return []

    low_coverage_items = [
        item for item in rm_items if (item.get('rm_readiness') or {}).get('alert_level') in {'warning', 'danger'}
    ]
    viewer_gap_total = sum((item.get('rm_readiness') or {}).get('viewer_without_full_rm_count') or 0 for item in rm_items)
    if not low_coverage_items and not viewer_gap_total:
        return []

    tracked_cases = len(rm_items)
    low_coverage_count = len(low_coverage_items)
    if low_coverage_count == tracked_cases:
        trend_label = 'Sinal de desgaste'
        tone = 'warning'
        label = 'Cobertura de RM baixa nas publicacoes com %RM'
        summary = (
            f'Todas as {tracked_cases} publicacao(oes) recentes com %RM mostraram prontidao curta da turma para consumir a prescricao.'
        )
        recommendation = 'Vale coletar RM antes da proxima aula semelhante ou evitar %RM em turma com cobertura baixa.'
    elif low_coverage_count:
        trend_label = 'Sinal de desgaste'
        tone = 'warning'
        label = 'Cobertura de RM oscilando nas publicacoes com %RM'
        summary = (
            f'{low_coverage_count} de {tracked_cases} publicacao(oes) com %RM sairam com cobertura curta de RM na turma.'
        )
        recommendation = 'Vale revisar quais movimentos dependem de RM e preparar coleta curta antes de repetir esse desenho.'
    else:
        trend_label = 'Melhora recente'
        tone = 'success'
        label = 'Cobertura de RM sustentando o desenho com %RM'
        summary = 'As publicacoes recentes com %RM estao encontrando turma pronta para consumir a prescricao.'
        recommendation = 'Vale consolidar esse corredor e manter a coleta de RM viva antes das proximas aulas semelhantes.'

    return [
        {
            'tone': tone,
            'label': label,
            'summary': summary,
            'recommendation': recommendation,
            'trend_label': trend_label,
            'recent_total': tracked_cases + viewer_gap_total,
            'action_href': '#rm-gap-queue',
        }
    ]


def build_rm_gap_queue(*, history_items):
    status_tones = {
        WorkoutRmGapActionStatus.REQUESTED: 'warning',
        WorkoutRmGapActionStatus.COLLECTED: 'success',
        WorkoutRmGapActionStatus.FREE_LOAD: 'accent',
    }
    queue_entries = []
    for item in history_items:
        rm_readiness = item.get('rm_readiness') or {}
        if not rm_readiness.get('has_percentage_rm') or not rm_readiness.get('missing_student_entries'):
            continue
        action_map = {
            (action.student_id, action.exercise_slug): action
            for action in item.get('rm_gap_action_records') or ()
        }
        student_rows = []
        for student_entry in rm_readiness.get('missing_student_entries') or ():
            for exercise in student_entry.get('missing_exercises') or ():
                action = action_map.get((student_entry['student_id'], exercise['slug']))
                student_rows.append(
                    {
                        'student_id': student_entry['student_id'],
                        'student_name': student_entry['student_name'],
                        'exercise_slug': exercise['slug'],
                        'exercise_label': exercise['label'],
                        'status': action.status if action else WorkoutRmGapActionStatus.REQUESTED,
                        'status_label': action.get_status_display() if action else 'RM solicitado',
                        'status_tone': status_tones.get(action.status if action else WorkoutRmGapActionStatus.REQUESTED, 'warning'),
                        'note': action.note if action else '',
                        'updated_by_label': (
                            action.updated_by.get_full_name() or action.updated_by.username
                            if action and action.updated_by is not None
                            else ''
                        ),
                        'updated_at_label': (
                            timezone.localtime(action.updated_at).strftime('%d/%m %H:%M')
                            if action is not None
                            else ''
                        ),
                    }
                )
        queue_entries.append(
            {
                'workout_id': item.get('workout_id'),
                'session_title': item.get('session_title', ''),
                'workout_title': item.get('workout_title', ''),
                'session_scheduled_label': item.get('session_scheduled_label', ''),
                'published_at_label': item.get('published_at_label', ''),
                'required_movements_label': rm_readiness.get('required_movements_label', ''),
                'required_movements': tuple(rm_readiness.get('required_movements') or ()),
                'missing_students': tuple(rm_readiness.get('missing_students') or ()),
                'missing_count': len(rm_readiness.get('missing_students') or ()),
                'coverage_label': rm_readiness.get('coverage_label', ''),
                'viewer_ready_label': rm_readiness.get('viewer_ready_label', ''),
                'tone': rm_readiness.get('alert_level') or 'warning',
                'student_rows': tuple(student_rows),
            }
        )
    queue_entries.sort(key=lambda entry: (-entry['missing_count'], entry['session_title'], entry['workout_title']))
    return {
        'entries': queue_entries[:6],
        'total_students': sum(entry['missing_count'] for entry in queue_entries),
        'total_cases': len(queue_entries),
    }


def build_management_alert_priority(alerts):
    priority_entries = []
    for alert in alerts:
        if alert['trend_label'] == 'Sinal de desgaste':
            priority_score = 200 + int(alert.get('recent_total') or 0)
            priority_tone = 'warning'
            priority_label = 'Olhar primeiro'
            priority_summary = 'Esse alerta aponta desgaste recorrente e merece leitura executiva antes dos sinais positivos.'
        else:
            priority_score = 100 + int(alert.get('recent_total') or 0)
            priority_tone = 'success'
            priority_label = 'Olhar em seguida'
            priority_summary = 'Esse alerta e positivo, mas pode esperar depois do que estiver mostrando cansaco operacional.'
        priority_entries.append(
            {
                **alert,
                'priority_score': priority_score,
                'priority_tone': priority_tone,
                'priority_label': priority_label,
                'priority_summary': priority_summary,
            }
        )
    priority_entries.sort(key=lambda entry: (-entry['priority_score'], entry['label']))
    top_entry = priority_entries[0] if priority_entries else None
    return {
        'entries': priority_entries[:4],
        'top_entry': top_entry,
    }


def build_management_recommendations(priority_entries):
    recommendations = []
    for entry in priority_entries:
        label_lower = entry['label'].lower()
        if 'rm' in label_lower:
            action = 'Coletar RM antes da proxima aula semelhante'
            why = 'O sinal mostra que o treino pediu uma chave que parte da turma ainda nao tinha; melhor medir antes ou simplificar a prescricao.'
        elif 'whatsapp' in label_lower:
            action = 'Revisar processo de WhatsApp esta semana'
            why = 'O sinal mostra que a comunicacao pode estar cansando e merece ajuste curto de cadencia, mensagem ou gatilho.'
        elif 'coach alinhado' in label_lower:
            action = 'Formalizar coach alinhado como boa pratica do box'
            why = 'O corredor esta mostrando valor e vale virar combinacao operacional repetivel entre coach, manager e recepcao.'
        elif 'recepcao' in label_lower:
            action = 'Reforcar protocolo curto da recepcao nesta semana'
            why = 'A recepcao entrou na jogada e vale alinhar script, timing e criterio de resposta para nao carregar peso demais no improviso.'
        else:
            action = 'Rodar revisao curta da alavanca ainda nesta semana'
            why = 'O sinal executivo pede ajuste leve antes que o corredor vire custo operacional escondido.'

        if entry['trend_label'] == 'Melhora recente':
            cadence = 'Consolidar nos proximos 7 dias'
        else:
            cadence = 'Atacar nas proximas 48h'

        recommendations.append(
            {
                'tone': entry['priority_tone'],
                'label': action,
                'cadence': cadence,
                'summary': why,
                'source_label': entry['label'],
                'href': entry.get('action_href', ''),
            }
        )
    return recommendations[:3]
