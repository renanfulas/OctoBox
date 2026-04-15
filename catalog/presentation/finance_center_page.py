"""
ARQUIVO: fachada do presenter da central financeira.

POR QUE ELE EXISTE:
- preserva o contrato publico da pagina enquanto a Onda 4 separa tradicional, IA e hibrido.
"""

from collections import Counter

from access.roles import ROLE_DEV, ROLE_MANAGER, ROLE_OWNER
from communications.application.message_templates import build_operational_message_body
from django.urls import reverse
from django.utils import timezone
from shared_support.page_payloads import build_page_context, build_page_hero
from shared_support.whatsapp_links import build_whatsapp_message_href

from .finance_ai_page import build_follow_up_analytics_board
from .finance_hybrid_page import build_finance_hero, build_finance_operational_focus
from .finance_modes import build_finance_mode_contract
from .finance_risk_queue_page import build_finance_risk_queue
from .finance_traditional_page import (
    build_finance_churn_chart,
    build_finance_filter_summary,
    build_finance_filter_summary_current,
    build_finance_overdue_rows,
    build_finance_portfolio_panel,
    build_finance_revenue_chart,
)
from .shared import build_catalog_assets, build_catalog_page_payload


def build_finance_center_page(
    *,
    snapshot,
    operational_queue,
    export_links,
    current_role_slug,
    form,
    default_panel_override=None,
    filter_state_restored=False,
):
    filter_form = snapshot['filter_form']
    transport_payload = snapshot.get('transport_payload') or {}
    financial_alerts = transport_payload.get('financial_alerts') or snapshot['financial_alerts']
    financial_churn_foundation = snapshot.get('financial_churn_foundation', {})
    finance_follow_up_analytics = snapshot.get('finance_follow_up_analytics', {})
    finance_follow_up_analytics_board = build_follow_up_analytics_board(finance_follow_up_analytics)
    plan_portfolio = snapshot['plan_portfolio']
    finance_pulse = snapshot['finance_pulse']
    finance_priority_context = snapshot['finance_priority_context']
    can_manage_finance = current_role_slug in (ROLE_OWNER, ROLE_MANAGER)
    has_operational_queue = bool(operational_queue)

    default_panel = finance_priority_context['default_panel']
    default_action = finance_priority_context['default_action']
    if default_panel_override == 'tab-finance-filters':
        default_panel = 'tab-finance-filters'
        default_action = 'open-tab-finance-filters'
    finance_mode_contract = build_finance_mode_contract(
        finance_follow_up_analytics=finance_follow_up_analytics,
    )

    hero = build_finance_hero(
        finance_priority_context=finance_priority_context,
        has_operational_queue=has_operational_queue,
    )
    operational_focus = build_finance_operational_focus(
        finance_priority_context=finance_priority_context,
        operational_queue=operational_queue,
        financial_alerts=financial_alerts,
        finance_pulse=finance_pulse,
    )
    finance_filter_summary = build_finance_filter_summary(filter_form)
    finance_trend_foundation = snapshot['finance_trend_foundation']

    return build_catalog_page_payload(
        context={
            **build_page_context(
                page_key='finance-center',
                title='Financeiro',
                subtitle='Receita, carteira e sinais operacionais em leitura guiada.',
                mode='management' if can_manage_finance else 'read-only',
                role_slug=current_role_slug,
            ),
        },
        data={
            'hero': hero,
            'can_manage_finance': can_manage_finance,
            'finance_mode_contract': finance_mode_contract,
            'finance_filter_form': filter_form,
            'finance_metrics': snapshot['finance_metrics'],
            'finance_pulse': finance_pulse,
            'financial_churn_foundation': financial_churn_foundation,
            'finance_risk_queue': build_finance_risk_queue(
                financial_churn_foundation,
                follow_up_analytics_board=finance_follow_up_analytics_board,
            ),
            'finance_follow_up_analytics': finance_follow_up_analytics,
            'finance_follow_up_analytics_board': finance_follow_up_analytics_board,
            'finance_revenue_chart': build_finance_revenue_chart(snapshot['monthly_comparison'], snapshot['comparison_peaks']),
            'finance_trend_metric_pills': finance_trend_foundation['metric_pills'],
            'finance_trend_foundation': finance_trend_foundation,
            'finance_trend_metric_views': finance_trend_foundation['metric_views'],
            'finance_trend_default_metric_key': finance_trend_foundation['default_metric_key'],
            'finance_churn_chart': build_finance_churn_chart(snapshot['monthly_comparison'], snapshot['comparison_peaks']),
            'finance_overdue_rows': build_finance_overdue_rows(financial_alerts),
            'interactive_kpis': snapshot.get('interactive_kpis', []),
            'finance_priority_context': finance_priority_context,
            'operational_focus': operational_focus,
            'plan_portfolio': plan_portfolio,
            'finance_portfolio_panel': build_finance_portfolio_panel(plan_portfolio),
            'monthly_comparison': snapshot['monthly_comparison'],
            'comparison_peaks': snapshot['comparison_peaks'],
            'financial_alerts': financial_alerts,
            'recent_movements': transport_payload.get('recent_movements') or snapshot.get('recent_movements') or [],
            'finance_transport_payload': transport_payload,
            'operational_queue': operational_queue,
            'finance_filter_summary': finance_filter_summary,
            'finance_filter_summary_current': build_finance_filter_summary_current(finance_filter_summary),
            'finance_active_window_label': finance_trend_foundation['window_label'],
            'finance_filter_state_restored': filter_state_restored,
            'form': form,
        },
        actions={
            'finance_export_links': export_links,
        },
        behavior={
            'default_panel': default_panel,
            'default_action': default_action,
            'active_mode': finance_mode_contract['active_mode'],
        },
        capabilities={
            'can_manage_finance': can_manage_finance,
            'can_export_finance': current_role_slug in (ROLE_OWNER, ROLE_DEV, ROLE_MANAGER),
        },
        assets=build_catalog_assets(
            css=[
                'css/catalog/shared/scene.css',
                'css/catalog/finance/_shell.css',
                'css/catalog/finance/_modes.css',
                'css/catalog/finance/_metrics.css',
                'css/catalog/finance/_responsive.css',
            ],
            deferred_css=[
                'bundle:css/catalog/finance-deferred.css',
            ],
            enhancement_css=[
                'bundle:css/catalog/finance-enhancement.css',
            ],
            deferred_js=[
                'js/pages/interactive_tabs.js',
                'js/pages/finance/finance-filter-summary.js',
                'js/pages/finance/finance-mode-controller.js',
                'js/pages/finance/finance-trend-board-controller.js',
                'js/pages/finance/finance-priority-carousel.js',
            ],
        ),
    )


__all__ = ['build_finance_center_page']
