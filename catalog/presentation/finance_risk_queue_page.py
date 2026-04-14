"""
ARQUIVO: apresentacao da fila de risco financeiro.

POR QUE ELE EXISTE:
- separa a traducao visual da fila semiassistida do presenter principal do financeiro.

O QUE ESTE ARQUIVO FAZ:
1. converte o data product de churn financeiro em linhas prontas para o template.
2. monta labels, playbooks, badges, notas e agrupamentos da fila.
3. preserva o contrato sem alterar score, sinal, recomendacao ou verdade operacional.

PONTOS CRITICOS:
- este arquivo e apresentacao; regra de ML e churn continua em catalog/finance_snapshot.
- nao transformar score ou recomendacao em verdade transacional.
"""

from collections import Counter

from communications.application.message_templates import build_operational_message_body
from django.urls import reverse
from shared_support.whatsapp_links import build_whatsapp_message_href


def _resolve_turn_priority_dominant_signal(group):
    count = group.get('count', 0)
    high_contextual_conviction_count = group.get('high_contextual_conviction_count', 0)
    high_confidence_count = group.get('high_confidence_count', 0)

    signal_scores = [
        (
            'volume',
            float(count),
            f"volume da faixa ({count} caso(s))",
        ),
        (
            'contextual_conviction',
            round(high_contextual_conviction_count * 1.4, 1),
            f"conviccao contextual ({high_contextual_conviction_count} caso(s) com leitura alta)",
        ),
        (
            'high_confidence',
            round(high_confidence_count * 1.2, 1),
            f"confianca alta ({high_confidence_count} caso(s) com leitura forte)",
        ),
    ]
    dominant_key, dominant_score, dominant_label = max(signal_scores, key=lambda item: item[1])
    return {
        'key': dominant_key,
        'score': dominant_score,
        'label': dominant_label,
    }


def _resolve_group_dominant_action(rows):
    action_counts = Counter(row.get('recommended_action_label') for row in rows if row.get('recommended_action_label'))
    if not action_counts:
        return {
            'label': 'Sem acao dominante',
            'count': 0,
            'note': 'Ainda sem massa suficiente para uma acao dominante neste bloco.',
        }

    label, count = action_counts.most_common(1)[0]
    return {
        'label': label,
        'count': count,
        'note': f"A acao mais presente neste bloco e {label}, aparecendo em {count} caso(s).",
    }


def build_finance_risk_queue(financial_churn_foundation, *, follow_up_analytics_board=None):
    foundation = financial_churn_foundation or {}
    follow_up_analytics_board = follow_up_analytics_board or {}
    queue_preview = foundation.get('queue_preview') or []
    summary = foundation.get('summary') or {}
    queue_focus = foundation.get('queue_focus') or ''
    rows = []

    bucket_map = {
        'already_inactive': ('Ja inativo', 'warning'),
        'high_signal': ('Alto risco', 'warning'),
        'watch': ('Observacao', 'info'),
        'recovered': ('Recuperado', 'success'),
        'stable': ('Estavel', 'accent'),
    }
    reason_map = {
        'student_inactive': 'Aluno ja esta inativo',
        'recurring_overdue_60d': 'Atraso recorrente em 60 dias',
        'overdue_60d': 'Atraso financeiro recente',
        'open_amount_active': 'Existe valor em aberto',
        'enrollment_canceled': 'Matricula cancelada',
        'enrollment_expired': 'Matricula expirada',
        'recent_finance_touch': 'Recebeu toque financeiro recente',
        'reactivated_after_inactive': 'Voltou depois de uma saida',
        'stable_base': 'Base financeira estavel',
    }
    action_map = {
        'review_winback': 'Revisar winback',
        'monitor_recent_reactivation': 'Acompanhar reativacao',
        'escalate_manual_retention': 'Escalar retencao manual',
        'send_financial_followup': 'Enviar follow-up financeiro',
        'monitor_and_nudge': 'Monitorar e lembrar',
        'observe_payment_resolution': 'Observar regularizacao',
        'maintain_relationship': 'Manter relacionamento',
    }
    confidence_map = {
        'high': 'Alta confianca',
        'medium': 'Confianca media',
        'low': 'Baixa confianca',
    }
    student_status_map = {
        'active': 'ativo',
        'inactive': 'inativo',
        'paused': 'pausado',
    }
    enrollment_status_map = {
        'active': 'Matricula ativa',
        'canceled': 'Matricula cancelada',
        'expired': 'Matricula expirada',
        'paused': 'Matricula pausada',
        'pending': 'Matricula pendente',
    }
    touch_label_map = {
        'overdue': 'Toque de cobranca',
        'reactivation': 'Toque de reativacao',
    }
    prediction_window_map = {
        'next_7_days': 'Resposta em 7 dias',
        'next_15_days': 'Resposta em 15 dias',
        'next_30_days': 'Resposta em 30 dias',
        '7d': 'Janela 7d',
        '15d': 'Janela 15d',
        '30d': 'Janela 30d',
    }
    momentum_class_map = {
        'fresh': 'success',
        'cooling': 'warning',
        'stale': 'accent',
    }
    focus_map = {
        '': 'Todas as missoes',
        'high_signal': 'Alto risco',
        'already_inactive': 'Ja inativo',
        'watch': 'Observacao',
        'recovered': 'Recuperado',
    }
    operational_band_map = {
        'act_now': {
            'label': 'Agir agora',
            'description': 'Casos onde a leitura pede movimento imediato.',
        },
        'act_with_caution': {
            'label': 'Agir com cautela',
            'description': 'Casos com sinal de acao, mas que pedem leitura fina.',
        },
        'observe_first': {
            'label': 'Observar primeiro',
            'description': 'Casos que merecem monitoramento antes de empurrar a acao.',
        },
    }

    def _build_playbook(item):
        student_url = f"{reverse('student-quick-update', args=[item['student_id']])}#student-financial-overview"
        first_name = item['student_name'].split()[0]
        due_date = item['financial_signal'].get('oldest_open_due_date')
        open_amount = item['financial_signal'].get('total_open_amount')
        plan_name = item['operational_state'].get('latest_plan_name') or 'do box'
        turn_priority_tension_guidance = item.get('turn_priority_tension_guidance') or {}
        message = ''
        if item['recommended_action'] in {'send_financial_followup', 'escalate_manual_retention', 'monitor_and_nudge'} and due_date:
            message = build_operational_message_body(
                action_kind='overdue',
                first_name=first_name,
                payment_due_date=due_date,
                payment_amount=open_amount,
            )
        elif item['recommended_action'] in {'review_winback', 'monitor_recent_reactivation'}:
            message = build_operational_message_body(
                action_kind='reactivation',
                first_name=first_name,
                plan_name=plan_name,
            )
        whatsapp_href = build_whatsapp_message_href(phone=item.get('student_phone', ''), message=message)

        if item['recommended_action'] == 'review_winback':
            playbook = {
                'playbook_label': 'Acionar winback',
                'playbook_note': 'Reabrir conversa com acolhimento e oferta de retorno.',
                'primary_label': 'Abrir WhatsApp',
                'primary_href': whatsapp_href or student_url,
                'primary_mode': 'finance_whatsapp',
                'primary_action_kind': 'reactivation',
                'secondary_label': 'Ver ficha',
                'secondary_href': student_url,
            }
        elif item['recommended_action'] in {'send_financial_followup', 'escalate_manual_retention'}:
            playbook = {
                'playbook_label': 'Cobrar e reter',
                'playbook_note': 'Resolver aberto financeiro sem perder o aluno no caminho.',
                'primary_label': 'Abrir WhatsApp',
                'primary_href': whatsapp_href or student_url,
                'primary_mode': 'finance_whatsapp',
                'primary_action_kind': 'overdue',
                'secondary_label': 'Ver ficha',
                'secondary_href': student_url,
            }
        elif item['recommended_action'] == 'monitor_and_nudge':
            playbook = {
                'playbook_label': 'Lembrete com contexto',
                'playbook_note': 'Fazer toque leve e observar resposta antes de escalar.',
                'primary_label': 'Abrir WhatsApp',
                'primary_href': whatsapp_href or student_url,
                'primary_mode': 'finance_whatsapp',
                'primary_action_kind': 'overdue',
                'secondary_label': 'Ver caso',
                'secondary_href': student_url,
            }
        elif item['recommended_action'] == 'monitor_recent_reactivation':
            playbook = {
                'playbook_label': 'Segurar retorno',
                'playbook_note': 'Acompanhar o aluno que voltou para evitar recaida imediata.',
                'primary_label': 'Monitorar por 7 dias',
                'primary_href': student_url,
                'primary_mode': 'link',
                'primary_action_kind': '',
                'secondary_label': 'Ver ficha',
                'secondary_href': student_url,
            }
        elif item['recommended_action'] == 'observe_payment_resolution':
            playbook = {
                'playbook_label': 'Observar regularizacao',
                'playbook_note': 'Ver se o sinal financeiro some antes de puxar escalada.',
                'primary_label': 'Abrir ficha',
                'primary_href': student_url,
                'primary_mode': 'link',
                'primary_action_kind': '',
                'secondary_label': 'Ver caso',
                'secondary_href': student_url,
            }
        else:
            playbook = {
                'playbook_label': 'Base sob controle',
                'playbook_note': 'Sem acao agressiva agora; manter proximidade e leitura.',
                'primary_label': 'Abrir ficha',
                'primary_href': student_url,
                'primary_mode': 'link',
                'primary_action_kind': '',
                'secondary_label': '',
                'secondary_href': '',
            }

        tendency = turn_priority_tension_guidance.get('tendency') or 'unknown'
        if tendency == 'healthy':
            playbook['playbook_note'] = (
                f"{playbook['playbook_note']} Contexto com espaco para ajuste humano."
            )
            if playbook.get('secondary_href'):
                playbook['secondary_label'] = 'Ver ficha'
                playbook['secondary_variant'] = 'finance-risk-action-healthy'
        elif tendency == 'dangerous':
            playbook['playbook_note'] = (
                f"{playbook['playbook_note']} Melhor seguir o plano base."
            )
            if playbook.get('secondary_href'):
                playbook['secondary_label'] = 'Ver ficha'
                playbook['secondary_variant'] = 'finance-risk-action-dangerous'
        elif tendency == 'mixed':
            playbook['playbook_note'] = (
                f"{playbook['playbook_note']} Melhor agir com prudencia."
            )
            if playbook.get('secondary_href'):
                playbook['secondary_label'] = 'Ver caso'
                playbook['secondary_variant'] = 'finance-risk-action-mixed'
        elif playbook.get('secondary_href'):
            playbook['secondary_variant'] = 'finance-risk-action-neutral'
        return playbook

    for item in queue_preview:
        bucket_label, bucket_class = bucket_map.get(item['signal_bucket'], ('Estavel', 'accent'))
        open_amount = item['financial_signal']['total_open_amount']
        open_amount_text = f'R$ {open_amount:.2f}' if open_amount else 'Sem aberto'
        playbook = _build_playbook(item)
        timing_guidance = item.get('timing_guidance') or {}
        best_action_key = timing_guidance.get('best_action_for_stage', '')
        best_action_label = action_map.get(best_action_key, best_action_key.replace('_', ' ')) if best_action_key else ''
        recommendation_adjustment = item.get('recommendation_adjustment') or {}
        confidence_adjustment = item.get('confidence_adjustment') or {}
        prediction_window_adjustment = item.get('prediction_window_adjustment') or {}
        contextual_guidance = item.get('contextual_guidance') or {}
        adjusted_from_key = item.get('recommended_action_base', '')
        adjusted_from_label = action_map.get(adjusted_from_key, adjusted_from_key.replace('_', ' ')) if adjusted_from_key else ''
        adjustment_note = ''
        if recommendation_adjustment.get('applied'):
            adjustment_note = (
                f"Ajuste automatico por timing: saiu de {adjusted_from_label} para "
                f"{action_map.get(item['recommended_action'], item['recommended_action'].replace('_', ' '))} "
                f"porque essa jogada entregou {recommendation_adjustment.get('candidate_window_success_rate', 0.0):.1f}% "
                f"dentro da janela {recommendation_adjustment.get('candidate_preferred_outcome_window', '').replace('d', 'd')} "
                f"em {recommendation_adjustment.get('candidate_window_realized_count', 0)} caso(s), "
                f"com ganho de {recommendation_adjustment.get('windowed_success_rate_lift', 0.0):.1f} ponto(s) sobre a base."
            )
        confidence_adjustment_note = ''
        if confidence_adjustment.get('applied'):
            confidence_adjustment_note = (
                f"Confianca ajustada de {confidence_map.get(item.get('confidence_base', ''), item.get('confidence_base', ''))} para "
                f"{confidence_map.get(item.get('confidence', ''), item.get('confidence', ''))} "
                f"pela regra {confidence_adjustment.get('rule_name', '')}, "
                f"com score historico {confidence_adjustment.get('evidence_historical_score', 0.0):.1f} "
                f"e score de fila {confidence_adjustment.get('evidence_queue_assist_score', 0.0):.1f}."
            )
        prediction_window_adjustment_note = ''
        if prediction_window_adjustment.get('applied'):
            prediction_window_adjustment_note = (
                f"Janela prevista ajustada de {prediction_window_adjustment.get('from_prediction_window_label', item.get('prediction_window_base', ''))} para "
                f"{prediction_window_adjustment.get('to_prediction_window_label', item.get('prediction_window', ''))} "
                f"porque essa acao respondeu melhor em {prediction_window_adjustment.get('evidence_realized_count', 0)} caso(s) "
                f"com {prediction_window_adjustment.get('evidence_success_rate', 0.0):.1f}% de sucesso."
            )
        contextual_action_key = contextual_guidance.get('suggested_recommended_action', '')
        contextual_action_label = action_map.get(
            contextual_action_key,
            contextual_action_key.replace('_', ' '),
        ) if contextual_action_key else ''
        turn_priority_tension_guidance = item.get('turn_priority_tension_guidance') or {}
        contextual_guidance_note = ''
        if contextual_guidance.get('available'):
            contextual_guidance_note = (
                f"Jogada contextual sugerida: {contextual_action_label} "
                f"neste timing {item['recommendation_momentum']['decay_label'].lower()} "
                f"e na gravidade {bucket_label.lower()}, com {contextual_guidance.get('success_rate', 0.0):.1f}% "
                f"de sucesso em {contextual_guidance.get('realized_count', 0)} caso(s)."
                if contextual_action_label else
                ''
            )
        tension_guidance_note = turn_priority_tension_guidance.get(
            'note',
            'Ainda sem amostra suficiente para dizer se a tensao neste contexto costuma ajudar ou dispersar.',
        )
        assist_flags = []
        if timing_guidance.get('is_aligned_with_best_action', False):
            assist_flags.append({'label': 'Timing alinhado', 'tone': 'success'})
        if recommendation_adjustment.get('applied', False):
            assist_flags.append({'label': 'Ajuste por timing', 'tone': 'warning'})
        if confidence_adjustment.get('applied', False):
            assist_flags.append({'label': 'Confianca ajustada', 'tone': 'info'})
        if prediction_window_adjustment.get('applied', False):
            assist_flags.append({'label': 'Janela ajustada', 'tone': 'accent'})
        if contextual_guidance.get('available', False):
            assist_flags.append({'label': 'Jogada contextual', 'tone': 'ink'})
        if turn_priority_tension_guidance.get('available', False):
            assist_flags.append(
                {
                    'label': turn_priority_tension_guidance.get('label', 'Leitura de tensao'),
                    'tone': 'accent',
                }
            )
        assist_notes = []
        if timing_guidance.get('best_action_for_stage'):
            assist_notes.append(
                f"Timing puxa {best_action_label} ({timing_guidance.get('best_action_success_rate', 0.0):.1f}% de sucesso)."
            )
        if recommendation_adjustment.get('applied', False):
            assist_notes.append(
                f"Fila trocou a jogada base de {adjusted_from_label} para {action_map.get(item['recommended_action'], item['recommended_action'].replace('_', ' '))}."
            )
        if confidence_adjustment.get('applied', False):
            assist_notes.append(
                f"Confianca subiu para {confidence_map.get(item.get('confidence', ''), item.get('confidence', ''))} com apoio do historico."
            )
        if prediction_window_adjustment.get('applied', False):
            assist_notes.append(
                f"Janela prevista encostou em {item.get('prediction_window', '')}."
            )
        if contextual_guidance.get('available', False) and contextual_action_label:
            assist_notes.append(
                f"Contexto sugere {contextual_action_label} neste tipo de caso."
            )
        if turn_priority_tension_guidance.get('available', False):
            assist_notes.append(tension_guidance_note)
        rows.append(
            {
                'student_name': item['student_name'],
                'student_phone': item.get('student_phone', ''),
                'student_url': f"{reverse('student-quick-update', args=[item['student_id']])}#student-financial-overview",
                'bucket_label': bucket_label,
                'bucket_class': bucket_class,
                'actual_status': student_status_map.get(item['actual_student_status'], item['actual_student_status']),
                'open_amount': open_amount_text,
                'overdue_count_60d': item['financial_signal']['overdue_payment_count_60d'],
                'latest_enrollment_status': enrollment_status_map.get(
                    item['operational_state']['latest_enrollment_status'],
                    'Sem matricula',
                ),
                'last_touch_label': touch_label_map.get(
                    item['communication_state']['last_finance_touch_action_kind'],
                    'Sem toque recente',
                ),
                'reason_labels': [reason_map.get(code, code.replace('_', ' ')) for code in item['reason_codes'][:3]],
                'recommended_action_label': action_map.get(item['recommended_action'], item['recommended_action'].replace('_', ' ')),
                'recommended_action_base_label': adjusted_from_label,
                'confidence_label': confidence_map.get(item['confidence'], item['confidence']),
                'confidence_base_label': confidence_map.get(item.get('confidence_base', ''), item.get('confidence_base', '')),
                'prediction_window': prediction_window_map.get(item['prediction_window'], item['prediction_window']),
                'prediction_window_base': item.get('prediction_window_base', ''),
                'priority_label': item['priority_label'],
                'historical_score_label': f"Score historico {item.get('historical_score', 0.0):.1f}",
                'queue_assist_score_label': f"Score de fila {item.get('queue_assist_score', 0.0):.1f}",
                'contextual_priority_score_label': f"Score contextual {item.get('contextual_priority_score', 0.0):.1f}",
                'contextual_conviction_label': (item.get('contextual_conviction') or {}).get('label', 'Sem leitura contextual'),
                'operational_band_label': (item.get('operational_band') or {}).get('label', 'Observar primeiro'),
                'priority_order_hint': 'Missao primeiro, historico depois, contexto por ultimo',
                'momentum_label': item['recommendation_momentum']['decay_label'],
                'momentum_class': momentum_class_map.get(item['recommendation_momentum']['decay_stage'], 'info'),
                'momentum_detail': (
                    f"{item['recommendation_momentum']['window_age_days']}d de {item['recommendation_momentum']['action_window']}"
                    if item['recommendation_momentum']['window_age_days'] is not None else
                    f"Janela {item['recommendation_momentum']['action_window']}"
                ),
                'timing_guidance_label': best_action_label,
                'timing_guidance_note': (
                    f"Melhor historico neste timing: {best_action_label} ({timing_guidance.get('best_action_success_rate', 0.0):.1f}% em {timing_guidance.get('best_action_realized_count', 0)} caso(s))"
                    if best_action_label else
                    'Sem amostra historica suficiente para sugerir outra jogada neste timing.'
                ),
                'timing_guidance_aligned': timing_guidance.get('is_aligned_with_best_action', False),
                'recommendation_adjusted': recommendation_adjustment.get('applied', False),
                'recommendation_adjustment_note': adjustment_note,
                'confidence_adjusted': confidence_adjustment.get('applied', False),
                'confidence_adjustment_note': confidence_adjustment_note,
                'prediction_window_adjusted': prediction_window_adjustment.get('applied', False),
                'prediction_window_adjustment_note': prediction_window_adjustment_note,
                'contextual_guidance_available': contextual_guidance.get('available', False),
                'contextual_guidance_applied': contextual_guidance.get('applied', False),
                'contextual_guidance_label': contextual_action_label,
                'contextual_guidance_note': contextual_guidance_note,
                'turn_priority_tension_guidance_available': turn_priority_tension_guidance.get('available', False),
                'turn_priority_tension_guidance_label': turn_priority_tension_guidance.get('label', 'Sem leitura de tensao'),
                'turn_priority_tension_guidance_note': tension_guidance_note,
                'assist_flags': assist_flags,
                'assist_notes': assist_notes[:3],
                'playbook_label': playbook['playbook_label'],
                'playbook_note': playbook['playbook_note'],
                'primary_action_label': playbook['primary_label'],
                'primary_action_href': playbook['primary_href'],
                'primary_action_mode': playbook['primary_mode'],
                'primary_action_kind': playbook['primary_action_kind'],
                'secondary_action_label': playbook['secondary_label'],
                'secondary_action_href': playbook['secondary_href'],
                'secondary_action_variant': playbook.get('secondary_variant', 'finance-risk-action-neutral'),
                'payment_id': item.get('payment_id'),
                'enrollment_id': item.get('enrollment_id'),
                'student_id': item.get('student_id'),
                'operational_band_level': (item.get('operational_band') or {}).get('level', 'observe_first'),
            }
        )

    grouped_rows = []
    for band_level in ('act_now', 'act_with_caution', 'observe_first'):
        band_rows = [row for row in rows if row.get('operational_band_level') == band_level]
        if not band_rows:
            continue
        contextual_guidance_count = sum(1 for row in band_rows if row.get('contextual_guidance_available'))
        high_contextual_conviction_count = sum(
            1
            for row in band_rows
            if 'alta' in (row.get('contextual_conviction_label', '') or '').lower()
        )
        high_confidence_count = sum(
            1
            for row in band_rows
            if row.get('confidence_label') == 'Alta confianca'
        )
        if band_level == 'act_now':
            command_message = (
                f"Abra o turno por estes {len(band_rows)}; {high_contextual_conviction_count} chegam com leitura contextual forte."
            )
        elif band_level == 'act_with_caution':
            command_message = (
                f"Avance com calma nestes {len(band_rows)}; {contextual_guidance_count} ainda pedem leitura fina antes do proximo toque."
            )
        else:
            command_message = (
                f"Deixe estes {len(band_rows)} em observacao; {high_confidence_count} ainda sustentam leitura sem pedir aceleracao."
            )
        grouped_rows.append(
            {
                'level': band_level,
                'label': operational_band_map[band_level]['label'],
                'description': operational_band_map[band_level]['description'],
                'count': len(band_rows),
                'contextual_guidance_count': contextual_guidance_count,
                'high_contextual_conviction_count': high_contextual_conviction_count,
                'high_confidence_count': high_confidence_count,
                'dominant_signal': _resolve_turn_priority_dominant_signal(
                    {
                        'count': len(band_rows),
                        'high_contextual_conviction_count': high_contextual_conviction_count,
                        'high_confidence_count': high_confidence_count,
                    }
                ),
                'dominant_action': _resolve_group_dominant_action(band_rows),
                'summary_line': (
                    f"{contextual_guidance_count} com jogada contextual â€¢ "
                    f"{high_contextual_conviction_count} com conviccao alta â€¢ "
                    f"{high_confidence_count} com alta confianca"
                ),
                'command_message': command_message,
                'rows': band_rows,
            }
        )

    turn_priority = {}
    if grouped_rows:
        lead_group = grouped_rows[0]
        dominant_signal = _resolve_turn_priority_dominant_signal(lead_group)
        turn_recommendation = follow_up_analytics_board.get('best_play', {}) or {}
        global_action_label = turn_recommendation.get('action_label')
        dominant_action_label = (lead_group.get('dominant_action') or {}).get('label', 'Sem acao dominante')
        is_turn_action_aligned = bool(
            global_action_label and dominant_action_label and global_action_label == dominant_action_label
        )
        turn_priority = {
            'label': lead_group['label'],
            'count': lead_group['count'],
            'command_message': lead_group['command_message'],
            'description': lead_group['description'],
            'dominant_signal_label': dominant_signal['label'],
            'dominant_action_label': dominant_action_label,
            'why_now': (
                f"{lead_group['count']} caso(s) puxam a abertura. "
                f"O que mais empurra esta faixa e {dominant_signal['label']}."
            ),
            'action_focus': (
                f"Primeira jogada sugerida: {dominant_action_label}."
            ),
            'alignment_note': (
                f"Ela converge com a recomendacao global do turno: {global_action_label}."
                if is_turn_action_aligned else
                f"Ela puxa para outro lado da recomendacao global do turno: {global_action_label}."
                if global_action_label else
                'Ainda sem recomendacao global suficiente para medir alinhamento.'
            ),
            'alignment_status': (
                'aligned' if is_turn_action_aligned else 'tension' if global_action_label else 'unknown'
            ),
        }

    return {
        'queue_focus': queue_focus,
        'queue_focus_label': focus_map.get(queue_focus, 'Todas as missoes'),
        'filtered_count': foundation.get('filtered_count', len(rows)),
        'turn_recommendation': follow_up_analytics_board.get('best_play', {}),
        'turn_priority': turn_priority,
        'summary': {
            'students_in_scope': summary.get('students_in_scope', 0),
            'actual_churn_count': summary.get('actual_churn_count', 0),
            'high_signal_count': summary.get('high_signal_count', 0),
            'watch_count': summary.get('watch_count', 0),
            'recovered_count': summary.get('recovered_count', 0),
        },
        'groups': grouped_rows,
        'rows': rows,
    }


__all__ = ['build_finance_risk_queue']
