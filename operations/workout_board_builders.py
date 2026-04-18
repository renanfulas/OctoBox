"""
ARQUIVO: builders puros da board de aprovacao e leitura operacional do WOD.

POR QUE ELE EXISTE:
- tira da borda HTTP a biblioteca de calculos e montagem de payload do corredor de WOD.

O QUE ESTE ARQUIVO FAZ:
1. normaliza snapshots de WOD.
2. monta diff estrutural e preview do aluno.
3. calcula assistencia de decisao e leitura executiva curta.
4. consolida sinais de tendencia, maturidade e recomendacao semanal.

PONTOS CRITICOS:
- manter estas funcoes sem acoplamento a request ou redirect.
- qualquer regressao aqui muda a leitura da board e do historico publicado.
"""

from datetime import timedelta

from django.utils import timezone

from student_app.application.use_cases import (
    build_student_prescription_label,
    build_student_recommendation_preview,
)
from student_app.models import (
    SessionWorkoutMovement,
    SessionWorkoutRevisionEvent,
    WorkoutOperationalMemoryKind,
    WorkoutWeeklyCheckpointClosure,
    WorkoutWeeklyCheckpointStatus,
)


def build_snapshot_blocks(snapshot):
    normalized_blocks = []
    for block in snapshot.get('blocks', []):
        normalized_movements = []
        for movement in block.get('movements', []):
            normalized_movements.append(
                {
                    'sort_order': movement.get('sort_order') or 0,
                    'movement_slug': movement.get('movement_slug', ''),
                    'movement_label': movement.get('movement_label', ''),
                    'sets': movement.get('sets'),
                    'reps': movement.get('reps'),
                    'load_type': movement.get('load_type', ''),
                    'load_value': movement.get('load_value', ''),
                    'notes': movement.get('notes', ''),
                }
            )
        normalized_blocks.append(
            {
                'sort_order': block.get('sort_order') or 0,
                'title': block.get('title', ''),
                'kind': block.get('kind', ''),
                'kind_label': block.get('kind_label') or block.get('kind', ''),
                'notes': block.get('notes', ''),
                'movements': normalized_movements,
            }
        )
    return normalized_blocks


def build_snapshot_presentation(snapshot):
    blocks = build_snapshot_blocks(snapshot)
    total_movements = sum(len(block['movements']) for block in blocks)
    return {
        'title': snapshot.get('title', ''),
        'coach_notes': snapshot.get('coach_notes', ''),
        'version': snapshot.get('version'),
        'status': snapshot.get('status', ''),
        'block_count': len(blocks),
        'movement_count': total_movements,
        'blocks': blocks,
    }


def normalize_load_type_label(load_type):
    return dict(SessionWorkoutMovement._meta.get_field('load_type').choices).get(load_type, load_type or '-')


def build_student_preview_payload(*, session_title, session_scheduled_label, coach_name, workout_title, coach_notes, blocks):
    preview_blocks = []
    for block in blocks:
        block_title = block.get('title') if isinstance(block, dict) else block.title
        block_kind_label = block.get('kind_label') if isinstance(block, dict) else block.get_kind_display()
        block_notes = block.get('notes', '') if isinstance(block, dict) else block.notes
        block_movements = block.get('movements', []) if isinstance(block, dict) else block.movements.all()
        preview_movements = []
        for movement in block_movements:
            load_context_label, recommended_load, recommendation_copy = build_student_recommendation_preview(movement=movement)
            load_type = movement.get('load_type') if isinstance(movement, dict) else movement.load_type
            recommendation_label = (
                f'{recommended_load} kg'
                if recommended_load is not None and load_type != 'fixed_kg'
                else (f'{recommended_load} kg' if recommended_load is not None else 'Sem carga automatica')
            )
            movement_label = movement.get('movement_label') if isinstance(movement, dict) else movement.movement_label
            movement_notes = movement.get('notes', '') if isinstance(movement, dict) else movement.notes
            preview_movements.append(
                {
                    'movement_label': movement_label,
                    'prescription_label': build_student_prescription_label(movement=movement),
                    'load_context_label': load_context_label,
                    'recommendation_label': recommendation_label,
                    'recommendation_copy': recommendation_copy,
                    'notes': movement_notes,
                }
            )
        preview_blocks.append(
            {
                'title': block_title,
                'kind_label': block_kind_label,
                'notes': block_notes,
                'movements': preview_movements,
            }
        )
    return {
        'session_title': session_title,
        'session_scheduled_label': session_scheduled_label,
        'coach_name': coach_name,
        'workout_title': workout_title,
        'coach_notes': coach_notes,
        'blocks': preview_blocks,
    }


def build_student_preview_diff(*, previous_preview, current_preview):
    if previous_preview is None:
        return {
            'has_previous_preview': False,
            'summary': 'Esse sera o primeiro preview oficial visto pelo aluno nesta aula.',
            'changed_cards': [],
            'added_blocks': [],
            'removed_blocks': [],
            'coach_notes_changed': False,
        }

    previous_blocks = {(block['title'], block['kind_label']): block for block in previous_preview['blocks']}
    current_blocks = {(block['title'], block['kind_label']): block for block in current_preview['blocks']}
    added_blocks = sorted(block[0] for block in current_blocks.keys() - previous_blocks.keys() if block[0])
    removed_blocks = sorted(block[0] for block in previous_blocks.keys() - current_blocks.keys() if block[0])
    changed_cards = []
    for block_key in sorted(previous_blocks.keys() & current_blocks.keys()):
        previous_block = previous_blocks[block_key]
        current_block = current_blocks[block_key]
        previous_movements = {movement['movement_label']: movement for movement in previous_block['movements']}
        current_movements = {movement['movement_label']: movement for movement in current_block['movements']}
        for movement_label in sorted(previous_movements.keys() & current_movements.keys()):
            previous_movement = previous_movements[movement_label]
            current_movement = current_movements[movement_label]
            changed_fields = []
            for field_key, field_label in (
                ('prescription_label', 'prescricao'),
                ('load_context_label', 'contexto de carga'),
                ('recommendation_label', 'carga recomendada'),
                ('recommendation_copy', 'texto de apoio'),
                ('notes', 'nota do movimento'),
            ):
                if previous_movement.get(field_key, '') != current_movement.get(field_key, ''):
                    changed_fields.append(field_label)
            if changed_fields:
                changed_cards.append(
                    {
                        'block_title': current_block['title'],
                        'movement_label': movement_label,
                        'changed_fields': changed_fields,
                        'previous_prescription_label': previous_movement.get('prescription_label', ''),
                        'current_prescription_label': current_movement.get('prescription_label', ''),
                        'previous_recommendation_label': previous_movement.get('recommendation_label', ''),
                        'current_recommendation_label': current_movement.get('recommendation_label', ''),
                    }
                )
    coach_notes_changed = previous_preview.get('coach_notes', '') != current_preview.get('coach_notes', '')
    summary_bits = []
    if coach_notes_changed:
        summary_bits.append('mensagem do coach mudou')
    if added_blocks:
        summary_bits.append(f'{len(added_blocks)} bloco(s) novo(s) no app do aluno')
    if removed_blocks:
        summary_bits.append(f'{len(removed_blocks)} bloco(s) sairam do app do aluno')
    if changed_cards:
        summary_bits.append(f'{len(changed_cards)} cartao(oes) de movimento mudaram para o aluno')
    return {
        'has_previous_preview': True,
        'summary': ', '.join(summary_bits) if summary_bits else 'A experiencia final do aluno continua equivalente a ultima versao publicada.',
        'changed_cards': changed_cards[:6],
        'added_blocks': added_blocks[:4],
        'removed_blocks': removed_blocks[:4],
        'coach_notes_changed': coach_notes_changed,
    }


def build_workout_decision_assist(*, workout, diff_snapshot, student_preview_diff):
    impact_score = 0
    reasons = []
    priority_flags = []

    if diff_snapshot['is_sensitive']:
        impact_score += 4
        reasons.append('Mudancas sensiveis na prescricao')
        priority_flags.append({'label': 'Mudanca sensivel', 'tone': 'danger'})
    if student_preview_diff['changed_cards']:
        impact_score += min(len(student_preview_diff['changed_cards']), 3)
        reasons.append(f"{len(student_preview_diff['changed_cards'])} cartao(oes) mudaram para o aluno")
    if student_preview_diff['added_blocks'] or student_preview_diff['removed_blocks']:
        impact_score += 2
        reasons.append('Estrutura visivel do treino mudou no app do aluno')
    if workout.revisions.filter(event=SessionWorkoutRevisionEvent.PUBLISHED).exists():
        impact_score += 1
        reasons.append('Republicacao de treino que ja teve versao oficial')
        priority_flags.append({'label': 'Republicacao', 'tone': 'warning'})
    else:
        priority_flags.append({'label': 'Primeira publicacao', 'tone': 'info'})

    now = timezone.localtime()
    starts_at = timezone.localtime(workout.session.scheduled_at)
    hours_until_session = (starts_at - now).total_seconds() / 3600
    if hours_until_session <= 6:
        impact_score += 2
        reasons.append('Aula comecando em breve')
        priority_flags.append({'label': 'Aula em breve', 'tone': 'accent'})

    if impact_score >= 6:
        impact_label = 'Alto impacto'
        impact_tone = 'danger'
    elif impact_score >= 3:
        impact_label = 'Medio impacto'
        impact_tone = 'warning'
    else:
        impact_label = 'Baixo impacto'
        impact_tone = 'success'

    summary_bits = []
    if diff_snapshot['added_blocks'] or diff_snapshot['removed_blocks']:
        summary_bits.append(
            f"{len(diff_snapshot['added_blocks']) + len(diff_snapshot['removed_blocks'])} bloco(s) mexidos"
        )
    if diff_snapshot['added_movements'] or diff_snapshot['removed_movements'] or diff_snapshot['changed_blocks']:
        movement_change_count = len(diff_snapshot['added_movements']) + len(diff_snapshot['removed_movements'])
        movement_change_count += sum(len(block['movement_changes']) for block in diff_snapshot['changed_blocks'])
        summary_bits.append(f'{movement_change_count} ajuste(s) de movimento')
    if student_preview_diff['changed_cards']:
        summary_bits.append(f"{len(student_preview_diff['changed_cards'])} cartao(oes) no app do aluno")
    if diff_snapshot['is_sensitive']:
        summary_bits.append('revisao sensivel')

    return {
        'impact_score': impact_score,
        'impact_label': impact_label,
        'impact_tone': impact_tone,
        'priority_flags': priority_flags[:4],
        'summary': ', '.join(summary_bits) if summary_bits else 'Mudanca pequena para leitura rapida.',
        'reasons': reasons[:5],
    }


def build_workout_diff_snapshot(*, published_snapshot, current_snapshot):
    if not published_snapshot:
        return {
            'has_previous_publication': False,
            'title_changed': False,
            'notes_changed': False,
            'added_blocks': [],
            'removed_blocks': [],
            'added_movements': [],
            'removed_movements': [],
            'changed_blocks': [],
            'risk_flags': [],
            'is_sensitive': False,
            'sensitive_reasons': [],
            'summary': 'Ainda nao existe versao publicada anterior para comparar.',
        }

    previous_blocks = build_snapshot_blocks(published_snapshot)
    current_blocks = build_snapshot_blocks(current_snapshot)
    previous_block_keys = {(block.get('title', ''), block.get('kind', '')) for block in previous_blocks}
    current_block_keys = {(block.get('title', ''), block.get('kind', '')) for block in current_blocks}

    def _flatten_movements(blocks):
        flattened = set()
        for block in blocks:
            for movement in block.get('movements', []):
                flattened.add((movement.get('movement_label', ''), movement.get('load_type', ''), movement.get('sets'), movement.get('reps')))
        return flattened

    previous_movements = _flatten_movements(previous_blocks)
    current_movements = _flatten_movements(current_blocks)

    added_blocks = sorted(key[0] for key in current_block_keys - previous_block_keys if key[0])
    removed_blocks = sorted(key[0] for key in previous_block_keys - current_block_keys if key[0])
    added_movements = sorted(key[0] for key in current_movements - previous_movements if key[0])
    removed_movements = sorted(key[0] for key in previous_movements - current_movements if key[0])
    title_changed = published_snapshot.get('title', '') != current_snapshot.get('title', '')
    notes_changed = published_snapshot.get('coach_notes', '') != current_snapshot.get('coach_notes', '')
    changed_blocks = []
    risk_flags = []
    sensitive_reasons = []

    previous_block_map = {
        (block.get('title', ''), block.get('kind', '')): block
        for block in previous_blocks
    }
    current_block_map = {
        (block.get('title', ''), block.get('kind', '')): block
        for block in current_blocks
    }
    for block_key in sorted(previous_block_map.keys() & current_block_map.keys()):
        previous_block = previous_block_map[block_key]
        current_block = current_block_map[block_key]
        movement_changes = []
        previous_movement_map = {
            movement.get('movement_slug') or movement.get('movement_label'): movement
            for movement in previous_block.get('movements', [])
        }
        current_movement_map = {
            movement.get('movement_slug') or movement.get('movement_label'): movement
            for movement in current_block.get('movements', [])
        }
        for movement_key in sorted(previous_movement_map.keys() & current_movement_map.keys()):
            previous_movement = previous_movement_map[movement_key]
            current_movement = current_movement_map[movement_key]
            changed_fields = []
            for field_key, field_label in (
                ('sets', 'sets'),
                ('reps', 'reps'),
                ('load_type', 'tipo de carga'),
                ('load_value', 'carga'),
                ('notes', 'notas'),
            ):
                if previous_movement.get(field_key) != current_movement.get(field_key):
                    changed_fields.append(field_label)
            if changed_fields:
                movement_label = current_movement.get('movement_label') or previous_movement.get('movement_label') or movement_key
                movement_changes.append(
                    {
                        'movement_label': movement_label,
                        'changed_fields': changed_fields,
                    }
                )
                if 'tipo de carga' in changed_fields or 'carga' in changed_fields:
                    risk_flags.append(f'Carga alterada em {movement_label}')
                    sensitive_reasons.append(f'Prescricao de carga mudou em {movement_label}')
        if previous_block.get('notes', '') != current_block.get('notes', ''):
            movement_changes.append(
                {
                    'movement_label': 'Notas do bloco',
                    'changed_fields': ['notas'],
                }
            )
        if movement_changes:
            changed_blocks.append(
                {
                    'title': current_block.get('title') or previous_block.get('title'),
                    'kind_label': current_block.get('kind_label') or previous_block.get('kind_label'),
                    'movement_changes': movement_changes,
                }
            )

    summary_bits = []
    if title_changed:
        summary_bits.append('titulo alterado')
    if notes_changed:
        summary_bits.append('notas do coach alteradas')
    if added_blocks:
        summary_bits.append(f'{len(added_blocks)} bloco(s) novo(s)')
    if removed_blocks:
        summary_bits.append(f'{len(removed_blocks)} bloco(s) removido(s)')
    if added_movements:
        summary_bits.append(f'{len(added_movements)} movimento(s) novo(s)')
    if removed_movements:
        summary_bits.append(f'{len(removed_movements)} movimento(s) removido(s)')
    if changed_blocks:
        summary_bits.append(f'{len(changed_blocks)} bloco(s) com ajuste interno')
    if notes_changed:
        risk_flags.append('Notas do coach alteradas')
    if removed_blocks:
        risk_flags.append(f'{len(removed_blocks)} bloco(s) removido(s)')
        sensitive_reasons.append(f'{len(removed_blocks)} bloco(s) foram removido(s)')
    if removed_movements:
        risk_flags.append(f'{len(removed_movements)} movimento(s) removido(s)')
        sensitive_reasons.append(f'{len(removed_movements)} movimento(s) foram removido(s)')
    movement_delta = len(current_movements) - len(previous_movements)
    if abs(movement_delta) >= 3:
        sensitive_reasons.append(f'Volume estrutural mudou em {abs(movement_delta)} movimento(s)')
    if title_changed and not sensitive_reasons:
        risk_flags.append('Titulo do treino foi alterado')

    return {
        'has_previous_publication': True,
        'title_changed': title_changed,
        'notes_changed': notes_changed,
        'added_blocks': added_blocks[:4],
        'removed_blocks': removed_blocks[:4],
        'added_movements': added_movements[:6],
        'removed_movements': removed_movements[:6],
        'changed_blocks': changed_blocks[:4],
        'risk_flags': risk_flags[:5],
        'is_sensitive': bool(sensitive_reasons),
        'sensitive_reasons': sensitive_reasons[:5],
        'summary': ', '.join(summary_bits) if summary_bits else 'Estrutura equivalente a ultima versao publicada.',
    }


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
            'label': 'Casos que precisaram de recepcao',
            'value': reception_case_count,
            'tone': 'info',
            'copy': 'Conta casos em que a recepcao ou operacao de balcao assumiu a bola em algum momento.',
        },
        {
            'label': 'Casos absorvidos com coach',
            'value': coach_resolved_case_count,
            'tone': 'success',
            'copy': 'Conta casos que tiveram coach alinhado e hoje ja aparecem como absorvidos na leitura executiva.',
        },
        {
            'label': 'Casos que dependeram de WhatsApp',
            'value': whatsapp_case_count,
            'tone': 'warning',
            'copy': 'Conta casos em que reforco de comunicacao entrou na historia operacional daquele WOD.',
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
            efficiency_label = 'Boa alavanca de absorcao'
        elif absorption_rate >= 40:
            efficiency_tone = 'accent'
            efficiency_label = 'Alavanca em observacao'
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
        if 'whatsapp' in label_lower:
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
            }
        )
    return recommendations[:3]


def build_weekly_executive_summary(*, history_items, management_priority, recommendations, trend_cards, now):
    week_floor = now - timedelta(days=7)
    weekly_items = [item for item in history_items if item.get('published_at') and item['published_at'] >= week_floor]
    if not weekly_items:
        weekly_items = history_items

    top_entry = management_priority.get('top_entry') if management_priority else None
    top_recommendation = recommendations[0] if recommendations else None
    positive_trend = next((card for card in trend_cards if card.get('trend_label') == 'Melhora recente'), None)

    adjustment_label = top_entry['label'] if top_entry else 'Nenhum corredor pediu ajuste forte acima da linha de ruido'
    improvement_label = positive_trend['label'] if positive_trend else 'Nenhuma melhora consistente ficou clara nesta janela'
    action_label = top_recommendation['label'] if top_recommendation else 'Manter observacao curta sem nova recomendacao principal'

    total_weekly = len(weekly_items)
    summary = (
        f'Nesta semana, o principal ponto de ajuste foi {adjustment_label.lower()}. '
        f'O melhor sinal de melhora veio de {improvement_label.lower()}. '
        f'A recomendacao principal virou {action_label.lower()}.'
    )
    return {
        'label': 'Resumo executivo semanal do box',
        'summary': summary,
        'weekly_total': total_weekly,
        'adjustment_label': adjustment_label,
        'improvement_label': improvement_label,
        'action_label': action_label,
    }


def build_weekly_checkpoint_rhythm(*, checkpoint_history):
    if not checkpoint_history:
        return []

    rhythm_cards = []
    current = checkpoint_history[0]
    previous = checkpoint_history[1] if len(checkpoint_history) > 1 else None

    if previous and current['execution_status'] != previous['execution_status']:
        rhythm_cards.append(
            {
                'tone': 'info' if current['execution_status'] == WorkoutWeeklyCheckpointStatus.COMPLETED else 'accent',
                'label': 'Virada de execucao',
                'summary': (
                    f"O checkpoint saiu de {previous['execution_status_label'].lower()} "
                    f"para {current['execution_status_label'].lower()} na semana de {current['week_label']}."
                ),
            }
        )

    recent_closures = [item['closure_status'] for item in checkpoint_history[:3] if item.get('closure_status')]
    if len(recent_closures) >= 2 and all(status == WorkoutWeeklyCheckpointClosure.PARTIAL for status in recent_closures):
        rhythm_cards.append(
            {
                'tone': 'warning',
                'label': 'Sequencia parcial',
                'summary': 'As ultimas semanas estao fechando como parcial. Vale revisar se a recomendacao esta grande demais ou sem dono forte.',
            }
        )

    if len(recent_closures) >= 2 and all(status == WorkoutWeeklyCheckpointClosure.WORKED for status in recent_closures):
        rhythm_cards.append(
            {
                'tone': 'success',
                'label': 'Sequencia funcionando',
                'summary': 'As ultimas semanas estao fechando com resultado positivo. Vale consolidar esse ritual como padrao de gestao.',
            }
        )

    return rhythm_cards[:3]


def build_weekly_checkpoint_maturity(*, checkpoint_history, rhythm_cards):
    if not checkpoint_history:
        return {
            'label': 'Maturidade operacional',
            'tone': 'accent',
            'state_label': 'Base curta',
            'summary': 'Ainda nao ha semanas suficientes para ler a maturidade do ritual com firmeza.',
        }

    recent_closures = [item['closure_status'] for item in checkpoint_history[:3] if item.get('closure_status')]
    recent_execution = [item['execution_status'] for item in checkpoint_history[:3] if item.get('execution_status')]
    rhythm_labels = {card['label'] for card in rhythm_cards}

    if len(recent_closures) >= 2 and all(status == WorkoutWeeklyCheckpointClosure.WORKED for status in recent_closures):
        return {
            'label': 'Maturidade operacional',
            'tone': 'success',
            'state_label': 'Saudavel',
            'summary': 'O ritual semanal esta fechando bem nas ultimas semanas e mostra cara de rotina madura, nao de improviso.',
        }

    if 'Sequencia parcial' in rhythm_labels or len({status for status in recent_execution[:2]}) > 1:
        return {
            'label': 'Maturidade operacional',
            'tone': 'warning',
            'state_label': 'Instavel',
            'summary': 'O ritual mostra oscilacao ou fechamento parcial repetido. Ele existe, mas ainda nao virou trilho confiavel.',
        }

    if len(recent_execution) >= 2 and all(status == WorkoutWeeklyCheckpointStatus.NOT_STARTED for status in recent_execution[:2]):
        return {
            'label': 'Maturidade operacional',
            'tone': 'danger',
            'state_label': 'Travado',
            'summary': 'O ritual semanal esta travando antes de ganhar corpo. Vale destravar dono, cadencia e fechamento.',
        }

    return {
        'label': 'Maturidade operacional',
        'tone': 'info',
        'state_label': 'Em formacao',
        'summary': 'O ritual esta ganhando forma, mas ainda precisa de repeticao consistente para virar padrao confiavel.',
    }


def build_weekly_governance_action(*, maturity):
    state = maturity.get('state_label')
    if state == 'Saudavel':
        return {
            'tone': 'success',
            'label': 'Formalizar ritual como padrao do box',
            'summary': 'O ritual ja mostra repeticao suficiente para sair do improviso e virar combinacao oficial da operacao.',
            'cadence': 'Levar para padrao nas proximas 2 semanas',
        }
    if state == 'Travado':
        return {
            'tone': 'danger',
            'label': 'Abrir destrave executivo do ritual',
            'summary': 'O ritual esta travando por semanas e precisa de dono forte, cadencia clara e fechamento obrigatorio.',
            'cadence': 'Atacar nas proximas 48h',
        }
    if state == 'Instavel':
        return {
            'tone': 'warning',
            'label': 'Rodar ajuste curto antes de formalizar',
            'summary': 'O ritual existe, mas ainda oscila. Vale reduzir variacao antes de transformar isso em regra da casa.',
            'cadence': 'Revisar ainda nesta semana',
        }
    if state == 'Base curta':
        return {
            'tone': 'accent',
            'label': 'Observar mais uma janela antes de governar',
            'summary': 'Ainda falta base para mexer em governanca com firmeza. Melhor completar mais uma rodada curta.',
            'cadence': 'Reavaliar na proxima semana',
        }
    return {
        'tone': 'info',
        'label': 'Manter ritual em formacao assistida',
        'summary': 'O ritual esta ganhando corpo. Vale acompanhar com dono claro antes de formalizar ou escalar.',
        'cadence': 'Acompanhar nos proximos 7 dias',
    }
