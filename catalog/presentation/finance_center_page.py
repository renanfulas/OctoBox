"""
ARQUIVO: presenter da central financeira.

POR QUE ELE EXISTE:
- tira da view HTTP a montagem da fachada financeira.
- organiza a tela por contrato explicito para reduzir contexto solto e facilitar a evolucao da area.
"""

from access.roles import ROLE_DEV, ROLE_MANAGER, ROLE_OWNER
from communications.application.message_templates import build_operational_message_body
from collections import Counter
from django.urls import reverse
from django.utils import timezone
from shared_support.page_payloads import build_page_hero
from shared_support.whatsapp_links import build_whatsapp_message_href

from ..finance_snapshot.follow_up_analytics import build_turn_recommendation
from .shared import build_catalog_assets, build_catalog_page_payload


FINANCE_PORTFOLIO_COLORS = ('cyan', 'violet', 'green', 'amber', 'rose', 'slate')


def _build_follow_up_analytics_board(analytics):
    analytics = analytics or {}
    action_map = {
        'review_winback': 'Revisar winback',
        'monitor_recent_reactivation': 'Acompanhar reativacao',
        'escalate_manual_retention': 'Escalar retencao manual',
        'send_financial_followup': 'Enviar follow-up financeiro',
        'monitor_and_nudge': 'Monitorar e lembrar',
        'observe_payment_resolution': 'Observar regularizacao',
        'maintain_relationship': 'Manter relacionamento',
        'overdue': 'WhatsApp de cobranca',
        'reactivation': 'WhatsApp de reativacao',
    }
    signal_bucket_map = {
        'already_inactive': 'Ja inativo',
        'high_signal': 'Alto risco',
        'watch': 'Observacao',
        'recovered': 'Recuperado',
        'stable': 'Estavel',
        'unknown': 'Sem classificacao',
    }
    recommendation_performance = []
    for item in analytics.get('recommendation_performance', [])[:4]:
        recommendation_performance.append(
            {
                'label': action_map.get(item['recommended_action'], item['recommended_action'].replace('_', ' ')),
                'historical_score': item['historical_score'],
                'success_rate': item['success_rate'],
                'execution_rate': item['execution_rate'],
                'sample': item['realized_count'],
            }
        )

    realized_actions = []
    for item in analytics.get('realized_action_performance', [])[:3]:
        realized_actions.append(
            {
                'label': action_map.get(item['action_kind'], item['action_kind']),
                'executed_count': item['executed_count'],
                'succeeded_count': item['succeeded_count'],
            }
        )

    weakest = []
    for item in analytics.get('weakest_recommendations', [])[:3]:
        weakest.append(
            {
                'label': action_map.get(item['recommended_action'], item['recommended_action'].replace('_', ' ')),
                'failure_rate': item['failure_rate'],
                'failed_count': item['failed_count'],
            }
        )

    windows = list(analytics.get('window_performance', [])[:3])
    timing = list(analytics.get('window_stage_performance', [])[:3])
    recommendation_timing = []
    for item in analytics.get('recommendation_timing_matrix', [])[:4]:
        recommendation_timing.append(
            {
                'action_label': action_map.get(item['recommended_action'], item['recommended_action'].replace('_', ' ')),
                'timing_label': item['suggestion_window_label'],
                'success_rate': item['success_rate'],
                'realized_count': item['realized_count'],
                'average_queue_assist_score': item['average_queue_assist_score'],
            }
        )
    recommendation_window = []
    for item in analytics.get('recommendation_window_matrix', [])[:4]:
        recommendation_window.append(
            {
                'action_label': action_map.get(item['recommended_action'], item['recommended_action'].replace('_', ' ')),
                'outcome_window': item['outcome_window'],
                'success_rate': item['success_rate'],
                'realized_count': item['realized_count'],
            }
        )
    divergence_timing = []
    for item in analytics.get('divergence_timing_matrix', [])[:4]:
        divergence_timing.append(
            {
                'timing_label': item['suggestion_window_label'],
                'divergent_realized_count': item['divergent_realized_count'],
                'smart_divergence_count': item['smart_divergence_count'],
                'bad_divergence_count': item['bad_divergence_count'],
                'smart_divergence_rate': item['smart_divergence_rate'],
                'bad_divergence_rate': item['bad_divergence_rate'],
            }
        )
    divergence_action = []
    for item in analytics.get('divergence_action_matrix', [])[:4]:
        divergence_action.append(
            {
                'action_label': action_map.get(item['recommended_action'], item['recommended_action'].replace('_', ' ')),
                'divergent_realized_count': item['divergent_realized_count'],
                'smart_divergence_count': item['smart_divergence_count'],
                'bad_divergence_count': item['bad_divergence_count'],
                'smart_divergence_rate': item['smart_divergence_rate'],
                'bad_divergence_rate': item['bad_divergence_rate'],
            }
        )
    divergence_signal_bucket = []
    for item in analytics.get('divergence_signal_bucket_matrix', [])[:4]:
        divergence_signal_bucket.append(
            {
                'signal_bucket_label': signal_bucket_map.get(item['signal_bucket'], item['signal_bucket']),
                'divergent_realized_count': item['divergent_realized_count'],
                'smart_divergence_count': item['smart_divergence_count'],
                'bad_divergence_count': item['bad_divergence_count'],
                'smart_divergence_rate': item['smart_divergence_rate'],
                'bad_divergence_rate': item['bad_divergence_rate'],
            }
        )
    turn_priority_tension_timing = []
    for item in analytics.get('turn_priority_tension_timing_matrix', [])[:4]:
        turn_priority_tension_timing.append(
            {
                'timing_label': item['suggestion_window_label'],
                'realized_count': item['realized_count'],
                'healthy_tension_count': item['healthy_tension_count'],
                'dangerous_tension_count': item['dangerous_tension_count'],
                'healthy_tension_rate': item['healthy_tension_rate'],
                'dangerous_tension_rate': item['dangerous_tension_rate'],
            }
        )
    turn_priority_tension_signal_bucket = []
    for item in analytics.get('turn_priority_tension_signal_bucket_matrix', [])[:4]:
        turn_priority_tension_signal_bucket.append(
            {
                'signal_bucket_label': signal_bucket_map.get(item['signal_bucket'], item['signal_bucket']),
                'realized_count': item['realized_count'],
                'healthy_tension_count': item['healthy_tension_count'],
                'dangerous_tension_count': item['dangerous_tension_count'],
                'healthy_tension_rate': item['healthy_tension_rate'],
                'dangerous_tension_rate': item['dangerous_tension_rate'],
            }
        )
    turn_priority_tension_compound = []
    for item in analytics.get('turn_priority_tension_compound_matrix', [])[:4]:
        turn_priority_tension_compound.append(
            {
                'timing_label': item['suggestion_window_label'],
                'signal_bucket_label': signal_bucket_map.get(item['signal_bucket'], item['signal_bucket']),
                'realized_count': item['realized_count'],
                'healthy_tension_rate': item['healthy_tension_rate'],
                'dangerous_tension_rate': item['dangerous_tension_rate'],
            }
        )
    divergence_compound = []
    for item in analytics.get('divergence_compound_matrix', [])[:4]:
        divergence_compound.append(
            {
                'action_label': action_map.get(item['recommended_action'], item['recommended_action'].replace('_', ' ')),
                'timing_label': item['suggestion_window_label'],
                'signal_bucket_label': signal_bucket_map.get(item['signal_bucket'], item['signal_bucket']),
                'divergent_realized_count': item['divergent_realized_count'],
                'smart_divergence_rate': item['smart_divergence_rate'],
                'bad_divergence_rate': item['bad_divergence_rate'],
            }
        )
    best_play = build_turn_recommendation(analytics)
    if best_play.get('recommended_action'):
        action_label = action_map.get(best_play['recommended_action'], best_play['recommended_action'].replace('_', ' '))
        best_play['action_label'] = action_label
        best_play['summary'] = (
            f"{action_label} esta liderando no historico ativo dentro da janela {best_play.get('outcome_window', '')}, "
            f"com {best_play.get('success_rate', 0.0)}% de sucesso em {best_play.get('realized_count', 0)} realizado(s)."
        )
    adherence = analytics.get('turn_recommendation_adherence', {}) or {}
    turn_outcome = analytics.get('turn_recommendation_outcome', {}) or {}
    turn_learning = analytics.get('turn_recommendation_learning', {}) or {}
    turn_priority_outcome = analytics.get('turn_priority_outcome', {}) or {}
    turn_priority_learning = analytics.get('turn_priority_learning', {}) or {}

    return {
        'summary': analytics.get('summary', {}),
        'best_play': best_play,
        'turn_recommendation_adherence': adherence,
        'turn_recommendation_outcome': {
            'aligned': {
                'label': 'Seguiu o turno',
                'realized_count': (turn_outcome.get('aligned') or {}).get('realized_count', 0),
                'succeeded_count': (turn_outcome.get('aligned') or {}).get('succeeded_count', 0),
                'failed_count': (turn_outcome.get('aligned') or {}).get('failed_count', 0),
                'success_rate': (turn_outcome.get('aligned') or {}).get('success_rate', 0.0),
            },
            'divergent': {
                'label': 'Divergiu do turno',
                'realized_count': (turn_outcome.get('divergent') or {}).get('realized_count', 0),
                'succeeded_count': (turn_outcome.get('divergent') or {}).get('succeeded_count', 0),
                'failed_count': (turn_outcome.get('divergent') or {}).get('failed_count', 0),
                'success_rate': (turn_outcome.get('divergent') or {}).get('success_rate', 0.0),
            },
        },
        'turn_recommendation_learning': {
            'smart_divergence': {
                'headline': (turn_learning.get('smart_divergence') or {}).get('headline', 'Quando divergir valeu a pena'),
                'realized_count': (turn_learning.get('smart_divergence') or {}).get('realized_count', 0),
                'success_rate': (turn_learning.get('smart_divergence') or {}).get('success_rate', 0.0),
                'summary': (turn_learning.get('smart_divergence') or {}).get(
                    'summary',
                    'Ainda sem casos suficientes para provar divergencia inteligente.',
                ),
            },
            'bad_divergence': {
                'headline': (turn_learning.get('bad_divergence') or {}).get(
                    'headline',
                    'Quando divergir piorou o resultado',
                ),
                'realized_count': (turn_learning.get('bad_divergence') or {}).get('realized_count', 0),
                'failure_rate': (turn_learning.get('bad_divergence') or {}).get('failure_rate', 0.0),
                'summary': (turn_learning.get('bad_divergence') or {}).get(
                    'summary',
                    'Ainda sem casos suficientes para provar desvio ruim.',
                ),
            },
        },
        'turn_priority_outcome': {
            'aligned': {
                'label': 'Turno alinhado',
                'realized_count': (turn_priority_outcome.get('aligned') or {}).get('realized_count', 0),
                'succeeded_count': (turn_priority_outcome.get('aligned') or {}).get('succeeded_count', 0),
                'failed_count': (turn_priority_outcome.get('aligned') or {}).get('failed_count', 0),
                'success_rate': (turn_priority_outcome.get('aligned') or {}).get('success_rate', 0.0),
            },
            'tension': {
                'label': 'Turno em tensao',
                'realized_count': (turn_priority_outcome.get('tension') or {}).get('realized_count', 0),
                'succeeded_count': (turn_priority_outcome.get('tension') or {}).get('succeeded_count', 0),
                'failed_count': (turn_priority_outcome.get('tension') or {}).get('failed_count', 0),
                'success_rate': (turn_priority_outcome.get('tension') or {}).get('success_rate', 0.0),
            },
        },
        'turn_priority_learning': {
            'healthy_tension': {
                'headline': (turn_priority_learning.get('healthy_tension') or {}).get(
                    'headline',
                    'Quando a tensao valeu a pena',
                ),
                'realized_count': (turn_priority_learning.get('healthy_tension') or {}).get('realized_count', 0),
                'success_rate': (turn_priority_learning.get('healthy_tension') or {}).get('success_rate', 0.0),
                'summary': (turn_priority_learning.get('healthy_tension') or {}).get(
                    'summary',
                    'Ainda sem casos suficientes para provar tensao saudavel.',
                ),
            },
            'dangerous_tension': {
                'headline': (turn_priority_learning.get('dangerous_tension') or {}).get(
                    'headline',
                    'Quando a tensao virou dispersao',
                ),
                'realized_count': (turn_priority_learning.get('dangerous_tension') or {}).get('realized_count', 0),
                'failure_rate': (turn_priority_learning.get('dangerous_tension') or {}).get('failure_rate', 0.0),
                'summary': (turn_priority_learning.get('dangerous_tension') or {}).get(
                    'summary',
                    'Ainda sem casos suficientes para provar tensao perigosa.',
                ),
            },
        },
        'turn_priority_tension_timing': turn_priority_tension_timing,
        'turn_priority_tension_signal_bucket': turn_priority_tension_signal_bucket,
        'turn_priority_tension_compound': turn_priority_tension_compound,
        'recommendations': recommendation_performance,
        'realized_actions': realized_actions,
        'weakest': weakest,
        'windows': windows,
        'timing': timing,
        'recommendation_timing': recommendation_timing,
        'recommendation_window': recommendation_window,
        'divergence_timing': divergence_timing,
        'divergence_action': divergence_action,
        'divergence_signal_bucket': divergence_signal_bucket,
        'divergence_compound': divergence_compound,
        'score_guide': analytics.get('score_guide', {}),
    }


def _build_finance_revenue_chart(monthly_comparison, comparison_peaks):
    max_revenue = comparison_peaks.get('max_revenue') or 0
    axis_step = 3000
    axis_max = axis_step

    if max_revenue:
        axis_max = ((int(max_revenue) + axis_step - 1) // axis_step) * axis_step
        axis_max = max(axis_max, axis_step)

    ticks = []
    for step in range(4, -1, -1):
        value = int(axis_max * step / 4)
        ticks.append(
            {
                'value': value,
                'label': f'{int(round(value / 1000))}k',
            }
        )

    items = []
    for item in monthly_comparison:
        revenue = item['revenue']
        expected_revenue = item.get('expected_revenue', revenue)
        items.append(
            {
                'label': item.get('short_label') or item['label'],
                'realized_value': revenue,
                'expected_value': expected_revenue,
                'realized_height': max(8, round((float(revenue) / axis_max) * 100)) if axis_max else 8,
                'expected_height': max(8, round((float(expected_revenue) / axis_max) * 100)) if axis_max else 8,
            }
        )

    return {
        'ticks': ticks,
        'items': items,
    }


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


def _build_finance_churn_chart(monthly_comparison, comparison_peaks):
    max_count = comparison_peaks.get('max_count') or 1
    axis_max = max(max_count, 1)

    ticks = []
    for step in range(4, -1, -1):
        value = int(round(axis_max * step / 4))
        ticks.append({'value': value, 'label': str(value)})

    items = []
    for item in monthly_comparison:
        activations = item['activations']
        cancellations = item['cancellations']
        items.append(
            {
                'label': item.get('short_label') or item['label'],
                'activations': activations,
                'cancellations': cancellations,
                'net_growth': item['net_growth'],
                'activation_height': max(8, round((activations / axis_max) * 100)) if axis_max else 8,
                'cancellation_height': max(8, round((cancellations / axis_max) * 100)) if axis_max else 8,
            }
        )

    return {
        'ticks': ticks,
        'items': items,
    }


def _build_finance_overdue_rows(financial_alerts):
    today = timezone.localdate()
    rows = []

    for payment in financial_alerts:
        student_name = payment.student.full_name
        initials = ''.join(part[0] for part in student_name.split()[:2]).upper()
        due_date = payment.due_date
        overdue_days = max((today - due_date).days, 0)

        rows.append(
            {
                'student_name': student_name,
                'student_url': f"{reverse('student-quick-update', args=[payment.student.id])}#student-financial-overview",
                'initials': initials[:2],
                'plan_name': payment.enrollment.plan.name if payment.enrollment else 'Sem vinculo de plano',
                'amount': payment.amount,
                'overdue_days': overdue_days,
                'badge': 'Urgente' if overdue_days >= 7 else 'Atencao',
            }
        )

    return rows


def _build_finance_risk_queue(financial_churn_foundation, *, follow_up_analytics_board=None):
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
                'secondary_label': 'Revisar matricula',
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
                'secondary_label': 'Revisar matricula',
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
                'secondary_label': 'Monitorar por 7 dias',
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
                'secondary_label': 'Abrir ficha',
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
                'secondary_label': 'Monitorar por 7 dias',
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
                f"{playbook['playbook_note']} Aqui vale abrir espaco para ajuste humano, porque a tensao neste contexto costuma ajudar."
            )
            if playbook.get('secondary_href'):
                playbook['secondary_label'] = 'Abrir ficha' if item['recommended_action'] in {
                    'review_winback',
                    'monitor_recent_reactivation',
                } else 'Revisar matricula'
                playbook['secondary_variant'] = 'finance-risk-action-healthy'
        elif tendency == 'dangerous':
            playbook['playbook_note'] = (
                f"{playbook['playbook_note']} Aqui vale seguir o plano base com mais disciplina, porque a tensao neste contexto costuma virar ruido."
            )
            if playbook.get('secondary_href'):
                playbook['secondary_label'] = 'Seguir plano base'
                playbook['secondary_variant'] = 'finance-risk-action-dangerous'
        elif tendency == 'mixed':
            playbook['playbook_note'] = (
                f"{playbook['playbook_note']} Aqui vale prudencia: a tensao neste contexto ainda esta mista."
            )
            if playbook.get('secondary_href'):
                playbook['secondary_label'] = 'Monitorar antes de escalar'
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
        rows.append(
            {
                'student_name': item['student_name'],
                'student_phone': item.get('student_phone', ''),
                'student_url': f"{reverse('student-quick-update', args=[item['student_id']])}#student-financial-overview",
                'bucket_label': bucket_label,
                'bucket_class': bucket_class,
                'actual_status': item['actual_student_status'],
                'open_amount': open_amount_text,
                'overdue_count_60d': item['financial_signal']['overdue_payment_count_60d'],
                'latest_enrollment_status': item['operational_state']['latest_enrollment_status'] or 'Sem matricula',
                'last_touch_label': item['communication_state']['last_finance_touch_action_kind'] or 'Sem toque recente',
                'reason_labels': [reason_map.get(code, code.replace('_', ' ')) for code in item['reason_codes'][:3]],
                'recommended_action_label': action_map.get(item['recommended_action'], item['recommended_action'].replace('_', ' ')),
                'recommended_action_base_label': adjusted_from_label,
                'confidence_label': confidence_map.get(item['confidence'], item['confidence']),
                'confidence_base_label': confidence_map.get(item.get('confidence_base', ''), item.get('confidence_base', '')),
                'prediction_window': item['prediction_window'],
                'prediction_window_base': item.get('prediction_window_base', ''),
                'priority_label': item['priority_label'],
                'historical_score_label': f"Score historico {item.get('historical_score', 0.0):.1f}",
                'queue_assist_score_label': f"Score de fila {item.get('queue_assist_score', 0.0):.1f}",
                'contextual_priority_score_label': f"Score contextual {item.get('contextual_priority_score', 0.0):.1f}",
                'contextual_conviction_label': (item.get('contextual_conviction') or {}).get('label', 'Sem leitura contextual'),
                'operational_band_label': (item.get('operational_band') or {}).get('label', 'Observar primeiro'),
                'priority_order_hint': 'Missao primeiro, historico depois, contextual por ultimo',
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
                f"Ataque esses {len(band_rows)} primeiro; {high_contextual_conviction_count} chegam com conviccao contextual alta."
            )
        elif band_level == 'act_with_caution':
            command_message = (
                f"Avance com calma nestes {len(band_rows)}; {contextual_guidance_count} pedem leitura contextual antes do proximo toque."
            )
        else:
            command_message = (
                f"So vigie estes {len(band_rows)} por enquanto; {high_confidence_count} ainda sustentam leitura forte sem pedir aceleracao."
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
                f"{lead_group['count']} caso(s) estao nesta faixa, "
                f"{lead_group['high_contextual_conviction_count']} com conviccao contextual alta "
                f"e {lead_group['high_confidence_count']} com alta confianca. "
                f"O peso maior veio de {dominant_signal['label']}."
            ),
            'action_focus': (
                f"A jogada que mais pede energia neste turno e "
                f"{dominant_action_label}."
            ),
            'alignment_note': (
                f"Ela esta alinhada com a recomendacao global do turno: {global_action_label}."
                if is_turn_action_aligned else
                f"Ela esta em tensao com a recomendacao global do turno: {global_action_label}."
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


def _build_finance_portfolio_panel(plan_portfolio):
    active_rows = []
    total_revenue = 0.0

    for plan in plan_portfolio:
        revenue = float(plan.revenue_this_month or 0)
        active_enrollments = int(plan.active_enrollments or 0)
        is_active_plan = bool(getattr(plan, 'active', False))
        if revenue <= 0 and active_enrollments <= 0 and not is_active_plan:
            continue

        active_rows.append(
            {
                'name': plan.name,
                'revenue': revenue,
                'active_enrollments': active_enrollments,
                'is_active_plan': is_active_plan,
            }
        )
        total_revenue += revenue

    if not active_rows:
        return {'items': [], 'total_revenue': 0.0}

    active_rows.sort(key=lambda item: (-int(item['is_active_plan']), -item['revenue'], -item['active_enrollments'], item['name']))

    total_revenue = total_revenue or 1.0
    items = []
    for index, row in enumerate(active_rows[:6]):
        items.append(
            {
                'name': row['name'],
                'revenue': row['revenue'],
                'active_enrollments': row['active_enrollments'],
                'width': max(12, round((row['revenue'] / total_revenue) * 100)),
                'color': FINANCE_PORTFOLIO_COLORS[index % len(FINANCE_PORTFOLIO_COLORS)],
                'is_new_empty_plan': row['revenue'] <= 0 and row['active_enrollments'] <= 0,
            }
        )

    return {
        'items': items,
        'total_revenue': sum(item['revenue'] for item in items),
    }


def build_finance_filter_summary(filter_form):
    months_choices = dict(filter_form.fields['months'].choices)
    status_choices = dict(filter_form.fields['payment_status'].choices)
    method_choices = dict(filter_form.fields['payment_method'].choices)

    months_value = '6'
    selected_plan = None
    payment_status = ''
    payment_method = ''

    if filter_form.is_valid():
        months_value = str(filter_form.cleaned_data.get('months') or '6')
        selected_plan = filter_form.cleaned_data.get('plan')
        payment_status = filter_form.cleaned_data.get('payment_status') or ''
        payment_method = filter_form.cleaned_data.get('payment_method') or ''

    return [
        {
            'label': 'Janela atual',
            'value': months_choices.get(months_value, '6 meses'),
            'summary': 'Define o horizonte da leitura gerencial antes de comparar caixa e retencao.',
        },
        {
            'label': 'Plano em foco',
            'value': selected_plan.name if selected_plan else 'Todos os planos',
            'summary': 'Mostra se o recorte esta amplo ou se ja esta olhando uma carteira especifica.',
        },
        {
            'label': 'Status financeiro',
            'value': status_choices.get(payment_status, 'Todos'),
            'summary': 'Ajuda a separar leitura total de leitura de pressao operacional.',
        },
        {
            'label': 'Metodo de pagamento',
            'value': method_choices.get(payment_method, 'Todos'),
            'summary': 'Util quando a analise precisa isolar comportamento de recebimento.',
        },
        {
            'label': 'Missao da fila',
            'value': dict(filter_form.fields['queue_focus'].choices).get(
                filter_form.cleaned_data.get('queue_focus') if filter_form.is_valid() else '',
                'Todas',
            ),
            'summary': 'Recorta a fila para a missao operacional que merece foco agora.',
        },
    ]


def build_finance_center_page(*, snapshot, operational_queue, export_links, current_role_slug, form):
    filter_form = snapshot['filter_form']
    financial_alerts = snapshot['financial_alerts']
    financial_churn_foundation = snapshot.get('financial_churn_foundation', {})
    finance_follow_up_analytics = snapshot.get('finance_follow_up_analytics', {})
    finance_follow_up_analytics_board = _build_follow_up_analytics_board(finance_follow_up_analytics)
    plan_portfolio = snapshot['plan_portfolio']
    finance_pulse = snapshot['finance_pulse']
    finance_priority_context = snapshot['finance_priority_context']
    pressure_total = len(operational_queue) + len(financial_alerts)
    can_manage_finance = current_role_slug in (ROLE_OWNER, ROLE_MANAGER)
    has_operational_queue = bool(operational_queue)

    default_panel = finance_priority_context['default_panel']
    default_action = finance_priority_context['default_action']

    operational_focus = [
        {
            'label': 'Quem pede contato agora' if finance_priority_context['dominant_key'] == 'queue' else 'Onde a fila ainda pode virar caixa',
            'chip_label': 'Cobrancas',
            'summary': (
                f'{len(operational_queue)} caso(s) ja tem abordagem sugerida e nao deveriam esperar outra leitura para virar acao.'
                if finance_priority_context['dominant_key'] == 'queue' else
                f'{len(operational_queue)} caso(s) continuam prontos para acao, mas hoje dividem a abertura com leitura de caixa e carteira.'
            ),
            'count': len(operational_queue),
            'pill_class': 'warning' if len(operational_queue) > 0 else 'success',
            'href': '#finance-priority-board' if has_operational_queue else '#finance-queue-board',
            'href_label': 'Abrir regua' if has_operational_queue else 'Abrir fila',
            'data_action': 'open-tab-finance-queue',
        },
        {
            'label': 'Onde a fila pressiona o caixa',
            'chip_label': 'Fila',
            'summary': f'{len(financial_alerts)} cobranca(s) ja aparecem como pendencia ou atraso no periodo atual.',
            'count': len(financial_alerts),
            'pill_class': 'warning' if len(financial_alerts) > 0 else 'info',
            'href': '#finance-queue-board',
            'href_label': 'Ver fila financeira',
            'data_action': 'open-tab-finance-queue',
        },
        {
            'label': 'Como a carteira respira',
            'chip_label': 'Carteira',
            'summary': f"Recebido: R$ {finance_pulse['received']:.2f} | Em aberto: R$ {finance_pulse['open']:.2f}.",
            'count': finance_pulse['overdue_students'],
            'pill_class': 'accent',
            'href': '#finance-trend-board',
            'href_label': 'Ver tendencia',
            'data_action': 'open-tab-finance-movements',
        },
    ]

    hero_actions = [
        {
            'label': 'Ver prioridades',
            'href': '#finance-priority-board' if has_operational_queue else '#finance-queue-board',
            'kind': 'primary',
            'data_action': 'open-tab-finance-queue',
        },
        {'label': 'Abrir carteira', 'href': '#finance-portfolio-board', 'kind': 'secondary', 'data_action': 'open-tab-finance-portfolio'},
    ]

    dominant_key = finance_priority_context.get('dominant_key')
    if dominant_key == 'portfolio':
        hero_title = 'Carteira em leitura.'
    elif dominant_key == 'queue':
        hero_title = 'Fila financeira.'
    else:
        hero_title = 'Financeiro ativo.'

    hero = build_page_hero(
        eyebrow='Financeiro',
        title=hero_title,
        copy='Veja a pressao dominante, abra a primeira passagem e desca sem ruido.',
        actions=hero_actions,
        aria_label='Panorama financeiro',
        classes=['finance-hero'],
        heading_level='h1',
    )

    return build_catalog_page_payload(
        context={
            'page_key': 'finance-center',
            'title': 'Financeiro',
            'subtitle': 'Receita, carteira e sinais operacionais em leitura guiada.',
            'mode': 'management' if can_manage_finance else 'read-only',
            'role_slug': current_role_slug,
        },
        data={
            'hero': hero,
            'can_manage_finance': can_manage_finance,
            'finance_filter_form': filter_form,
            'finance_metrics': snapshot['finance_metrics'],
            'finance_pulse': finance_pulse,
            'financial_churn_foundation': financial_churn_foundation,
            'finance_risk_queue': _build_finance_risk_queue(
                financial_churn_foundation,
                follow_up_analytics_board=finance_follow_up_analytics_board,
            ),
            'finance_follow_up_analytics': finance_follow_up_analytics,
            'finance_follow_up_analytics_board': finance_follow_up_analytics_board,
            'finance_revenue_chart': _build_finance_revenue_chart(snapshot['monthly_comparison'], snapshot['comparison_peaks']),
            'finance_churn_chart': _build_finance_churn_chart(snapshot['monthly_comparison'], snapshot['comparison_peaks']),
            'finance_overdue_rows': _build_finance_overdue_rows(financial_alerts),
            'interactive_kpis': snapshot.get('interactive_kpis', []),
            'finance_priority_context': finance_priority_context,
            'operational_focus': operational_focus,
            'plan_portfolio': plan_portfolio,
            'finance_portfolio_panel': _build_finance_portfolio_panel(plan_portfolio),
            'monthly_comparison': snapshot['monthly_comparison'],
            'comparison_peaks': snapshot['comparison_peaks'],
            'financial_alerts': financial_alerts,
            'operational_queue': operational_queue,
            'finance_filter_summary': build_finance_filter_summary(filter_form),
            'form': form,
        },
        actions={
            'finance_export_links': export_links,
        },
        behavior={
            'default_panel': default_panel,
            'default_action': default_action,
        },
        capabilities={
            'can_manage_finance': can_manage_finance,
            'can_export_finance': current_role_slug in (ROLE_OWNER, ROLE_DEV, ROLE_MANAGER),
        },
        assets=build_catalog_assets(css=['css/catalog/finance.css', 'css/design-system/financial.css'], include_catalog_shared=True),
    )
