"""
ARQUIVO: presenter da edicao curta de plano financeiro.

POR QUE ELE EXISTE:
- tira da view HTTP a montagem estrutural da tela de plano.
- concentra o contrato semantico da pagina sem inflar a borda HTTP com copy e listas visuais.
"""

from django.urls import reverse

from access.roles import ROLE_DEV, ROLE_OWNER
from access.shell_actions import build_shell_action_buttons_from_focus
from shared_support.page_payloads import build_page_hero

from .shared import build_catalog_assets, build_catalog_page_payload


def _build_membership_plan_focus(plan):
    return [
        {
            'label': 'Comece pelo coração da oferta',
            'chip_label': 'Plano',
            'summary': 'Nome, valor e ciclo precisam continuar legíveis para venda, cobrança e carteira sem depender de explicação oral.',
            'pill_class': 'accent',
            'href': '#plan-form-core',
            'href_label': 'Editar núcleo',
        },
        {
            'label': 'Depois valide a entrega',
            'chip_label': 'Comercial',
            'summary': 'A descrição comercial deve reduzir ambiguidade para recepção, manager e leitura futura do próprio plano.',
            'pill_class': 'info',
            'href': '#plan-form-delivery',
            'href_label': 'Revisar entrega',
        },
        {
            'label': 'Feche com impacto na carteira',
            'chip_label': 'Carteira',
            'summary': 'Status, ritmo semanal e leitura rápida precisam deixar claro se o plano fortalece a carteira ou só ocupa espaço visual.',
            'pill_class': 'warning' if plan.active else 'info',
            'href': '#plan-form-summary',
            'href_label': 'Ler impacto',
        },
    ]


def _build_membership_plan_snapshot(plan):
    return {
        'id': plan.id,
        'name': plan.name,
        'is_active': plan.active,
        'status_label': 'ativo' if plan.active else 'inativo',
        'status_summary': 'Ativo' if plan.active else 'Inativo',
        'price_display_short': f'R$ {plan.price:.0f}',
        'price_display_full': f'R$ {plan.price:.2f}',
        'billing_cycle_label': plan.get_billing_cycle_display(),
        'billing_cycle_label_lower': plan.get_billing_cycle_display().lower(),
        'sessions_per_week': plan.sessions_per_week,
        'sessions_per_week_label': f'{plan.sessions_per_week} aula(s)',
        'description': plan.description,
        'delivery_status_label': 'Descrita' if plan.description else 'Pede texto',
    }


def build_membership_plan_page(*, form, plan, current_role_slug):
    plan_focus = _build_membership_plan_focus(plan)
    plan_snapshot = _build_membership_plan_snapshot(plan)
    hero = build_page_hero(
        eyebrow='Plano',
        title='Detalhes do plano.',
        copy='Altere valores, ciclos e a proposta comercial.',
        actions=[
            {'label': 'Editar núcleo', 'href': '#plan-form-core', 'kind': 'primary'},
            {'label': 'Ver leitura rápida', 'href': '#plan-form-summary', 'kind': 'secondary'},
            {'label': 'Voltar para financeiro', 'href': reverse('finance-center'), 'kind': 'secondary'},
        ],
        aria_label='Plano comercial',
        classes=['operation-hero'],
        heading_level='h1',
        data_slot='hero',
        data_panel='finance-plan-hero',
    )

    return build_catalog_page_payload(
        context={
            'page_key': 'finance-plan-form',
            'title': 'Editar plano',
            'subtitle': 'Ajuste valor, ciclo e proposta comercial sem sair do centro financeiro.',
        },
        shell={
            'shell_action_buttons': build_shell_action_buttons_from_focus(focus=plan_focus, scope='finance-plan-form'),
        },
        data={
            'hero': hero,
            'form': form,
            'plan': plan_snapshot,
            'plan_form_guardrails': [
                'Plano bom precisa ser claro para vender, cobrar e explicar sem tradução improvisada.',
                'Valor e ciclo devem parecer consistentes com a entrega prometida e com o tipo de aluno que a carteira quer reter.',
                'Se a descrição ficar vaga, a recepção e o financeiro acabam preenchendo a lacuna no improviso.',
            ],
            'plan_form_summary_cards': [
                {
                    'label': 'Status comercial',
                    'value': plan_snapshot['status_summary'],
                    'summary': 'Mostra se o plano segue disponível para compor carteira e novas vendas.',
                },
                {
                    'label': 'Ritmo semanal',
                    'value': plan_snapshot['sessions_per_week_label'],
                    'summary': 'Ajuda a ler se a proposta cabe como entrada, meio de carteira ou oferta premium.',
                },
                {
                    'label': 'Entrega comercial',
                    'value': plan_snapshot['delivery_status_label'],
                    'summary': 'Evita que a equipe dependa de memória oral para explicar o plano.',
                },
            ],
        },
        actions={
            'primary': {
                'edit_core': '#plan-form-core',
                'read_summary': '#plan-form-summary',
            },
            'secondary': {
                'finance_center': reverse('finance-center'),
                'students': reverse('student-directory'),
                'admin': reverse('admin:boxcore_membershipplan_change', args=[plan.id]) if current_role_slug in (ROLE_OWNER, ROLE_DEV) else None,
            },
        },
        assets=build_catalog_assets(css=['css/catalog/finance.css'], include_catalog_shared=True),
    )