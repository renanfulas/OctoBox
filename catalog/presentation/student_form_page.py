"""
ARQUIVO: presenter da ficha leve do aluno.

POR QUE ELE EXISTE:
- tira da view HTTP a montagem visual da ficha, do recovery guide e do comportamento da pagina.
- organiza a tela por contrato explicito para o catalogo amadurecer por payload.
"""

from access.roles import ROLE_DEV, ROLE_MANAGER, ROLE_OWNER
from access.shell_actions import build_shell_action_buttons_from_focus
from access.navigation_contracts import get_shell_route_url
from shared_support.page_payloads import build_page_hero

from .shared import build_catalog_assets, build_catalog_page_payload


STUDENT_FORM_GUIDE_STEPS = (
    {
        'label': 'Passo 1: essencial',
        'href': '#student-form-essential',
        'fields': ('full_name', 'phone'),
        'summary': 'Confirme nome completo e WhatsApp. Sem esse nucleo o fluxo nao consegue continuar com seguranca.',
    },
    {
        'label': 'Passo 2: perfil do aluno',
        'href': '#student-form-profile',
        'fields': ('intake_record', 'status', 'email', 'gender', 'birth_date'),
        'summary': 'Revise vinculo, status e dados de perfil antes de seguir para a parte comercial.',
    },
    {
        'label': 'Passo 3: saude e identificacao',
        'href': '#student-form-health',
        'fields': ('health_issue_status', 'cpf', 'notes'),
        'summary': 'Ajuste CPF ou informacoes de saude para nao levar ruido adiante no cadastro.',
    },
    {
        'label': 'Passo 4: plano e status comercial',
        'href': '#student-form-plan',
        'fields': ('selected_plan', 'enrollment_status'),
        'summary': 'Se houver plano ou matricula ativa, essa combinacao precisa fechar sem contradicao.',
    },
    {
        'label': 'Passo 5: cobranca e confirmacao',
        'href': '#student-form-billing',
        'fields': (
            'billing_strategy',
            'initial_payment_amount',
            'payment_method',
            'confirm_payment_now',
            'payment_due_date',
            'payment_reference',
            'installment_total',
            'recurrence_cycles',
        ),
        'summary': 'Quando o travamento for financeiro, ajuste a forma de cobranca antes de tentar salvar de novo.',
    },
)


def build_student_form_recovery_guide(form):
    if not form or not form.errors:
        return None

    items = []
    for step in STUDENT_FORM_GUIDE_STEPS:
        if any(form.errors.get(field_name) for field_name in step['fields']):
            items.append(
                {
                    'label': step['label'],
                    'href': step['href'],
                    'summary': step['summary'],
                }
            )

    if form.non_field_errors() and not items:
        items.append(
            {
                'label': 'Regra geral do fluxo',
                'href': '#student-form-billing',
                'summary': 'Existe uma combinacao de dados que trava o fluxo. Revise os campos marcados abaixo.',
            }
        )

    return {
        'title': 'Vamos destravar isso por etapa',
        'copy': 'O box separou onde travou para voce corrigir sem cacar erro no formulario inteiro.',
        'items': items,
    }


def build_student_form_page(*, form, student_object, selected_intake, financial_overview, page_mode, current_role_slug):
    latest_enrollment = financial_overview.get('latest_enrollment')
    recent_payments = financial_overview.get('payments', [])
    can_open_student_admin = current_role_slug in (ROLE_OWNER, ROLE_DEV)
    can_manage_student_payments_full = current_role_slug in (ROLE_OWNER, ROLE_MANAGER)
    payment_management_form = financial_overview.get('payment_management_form')
    enrollment_management_form = financial_overview.get('enrollment_management_form')
    operational_focus = [
        {
            'label': 'Comece pelo nucleo do cadastro',
            'chip_label': 'Cadastro',
            'summary': 'Nome completo e WhatsApp ja destravam quase todo o fluxo. O restante so entra quando melhorar decisao, vinculo ou cobranca.',
            'pill_class': 'accent',
            'href': '#student-form-essential',
            'href_label': 'Abrir essencial',
        },
        {
            'label': 'Use o intake para reduzir atrito',
            'chip_label': 'Perfil',
            'summary': (
                f'Esta edicao ja nasceu de {selected_intake.full_name} e pode seguir com conversao guiada.'
                if selected_intake else
                'Se houver lead ou entrada provisoria, vincular aqui evita retrabalho e mantem a conversa viva.'
            ),
            'pill_class': 'info' if selected_intake else 'accent',
            'href': '#student-form-profile',
            'href_label': 'Ver perfil e vinculo',
        },
        {
            'label': 'Feche com plano e cobranca',
            'chip_label': 'Plano',
            'summary': (
                f'{latest_enrollment.plan.name} ja esta ligado ao aluno e {len(recent_payments)} cobranca(s) recente(s) ajudam a ler o financeiro sem sair desta tela.'
                if latest_enrollment else
                'Plano, status comercial e cobranca inicial ficam no mesmo fluxo para evitar ida e volta entre cadastro e financeiro.'
            ),
            'count': len(recent_payments),
            'pill_class': 'warning' if latest_enrollment else 'success',
            'href': '#student-form-plan',
            'href_label': 'Ver plano e cobranca',
        },
    ]
    shell_action_buttons = build_shell_action_buttons_from_focus(focus=operational_focus, scope='student-form')
    plan_price_map = {
        str(plan.id): str(plan.price)
        for plan in getattr(getattr(form, 'fields', {}).get('selected_plan'), 'queryset', [])
    }
    recovery_guide = build_student_form_recovery_guide(form)
    hero = build_page_hero(
        eyebrow='Fluxo leve de cadastro',
        title='Cadastrar aluno' if page_mode == 'create' else 'Editar aluno',
        copy=(
            'Essencial agora, plano e cobranca no mesmo fluxo.'
            if page_mode == 'create'
            else 'Ajuste cadastro, plano e cobranca sem cair no admin.'
        ),
        actions=[
            {'label': 'Preencher essencial', 'href': '#student-form-essential', 'kind': 'primary', 'data_action': 'open-tab-student-form-essential'},
            {'label': 'Ver plano e cobranca', 'href': '#student-form-financial', 'kind': 'secondary', 'data_action': 'open-tab-student-form-financial'},
            {'label': 'Voltar para alunos', 'href': get_shell_route_url('students'), 'kind': 'secondary'},
        ],
        aria_label='Ficha do aluno',
        classes=['operation-hero'],
    )

    return build_catalog_page_payload(
        context={
            'page_key': 'student-form',
            'title': 'Cadastrar aluno' if page_mode == 'create' else 'Editar aluno',
            'subtitle': (
                'Comece pelo essencial e complete o resto so se ja fizer sentido agora.'
                if page_mode == 'create'
                else 'Ajuste rapidamente o cadastro sem cair no admin bruto.'
            ),
            'mode': page_mode,
            'role_slug': current_role_slug,
        },
        shell={
            'shell_action_buttons': shell_action_buttons,
        },
        data={
            'hero': hero,
            'form': form,
            'page_mode': page_mode,
            'student_object': student_object,
            'selected_intake': selected_intake,
            'financial_overview': financial_overview,
            'payment_management_form': payment_management_form,
            'enrollment_management_form': enrollment_management_form,
            'student_form_recovery_guide': recovery_guide,
        },
        actions={
            'anchors': {
                'essential': '#student-form-essential',
                'profile': '#student-form-profile',
                'health': '#student-form-health',
                'plan': '#student-form-plan',
                'billing': '#student-form-billing',
                'financial': '#student-financial-overview',
            },
        },
        behavior={
            'plan_price_map': plan_price_map,
            'focus_sections': {
                'lead': {
                    'open': ['student-form-profile'],
                    'close': ['student-form-health', 'student-form-plan', 'student-form-billing'],
                    'scroll_target': 'student-form-essential',
                },
                'active': {
                    'close': ['student-form-essential', 'student-form-profile', 'student-form-health', 'student-form-plan', 'student-form-billing'],
                    'scroll_target': 'student-financial-overview',
                },
            },
        },
        capabilities={
            'can_open_student_admin': can_open_student_admin,
            'can_manage_student_payments_full': can_manage_student_payments_full,
        },
        assets=build_catalog_assets(
            css=['css/catalog/students.css', 'css/catalog/student_form_stepper.css', 'css/design-system/financial.css'],
            js=[
                'js/pages/students/student-form.js',
                'js/pages/students/student-form-stepper.js',
                'js/pages/interactive_tabs.js',
                'js/pages/finance/billing_console.js',
                'js/pages/finance/student-financial-workspace.js',
                'js/catalog/student_form_lock.js',
            ],
            include_catalog_shared=True,
        ),
    )
