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
        'step': 1,
        'fields': ('full_name', 'phone'),
        'summary': 'Confirme nome completo e WhatsApp. Sem esse nucleo o fluxo nao consegue continuar com seguranca.',
    },
    {
        'label': 'Passo 2: perfil do aluno',
        'href': '#student-form-profile',
        'step': 1,
        'fields': ('intake_record', 'status', 'email', 'gender', 'birth_date'),
        'summary': 'Revise vinculo, status e dados de perfil antes de seguir para a parte comercial.',
    },
    {
        'label': 'Passo 3: saude e identificacao',
        'href': '#student-form-health',
        'step': 1,
        'fields': ('health_issue_status', 'cpf', 'notes'),
        'summary': 'Ajuste CPF ou informacoes de saude para nao levar ruido adiante no cadastro.',
    },
    {
        'label': 'Passo 4: plano e status comercial',
        'href': '#student-form-plan',
        'step': 2,
        'fields': ('selected_plan', 'enrollment_status'),
        'summary': 'Se houver plano ou matricula ativa, essa combinacao precisa fechar sem contradicao.',
    },
    {
        'label': 'Passo 5: cobranca e confirmacao',
        'href': '#student-form-billing',
        'step': 2,
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
                    'step': step['step'],
                    'summary': step['summary'],
                }
            )

    if form.non_field_errors() and not items:
        items.append(
            {
                'label': 'Regra geral do fluxo',
                'href': '#student-form-billing',
                'step': 2,
                'summary': 'Existe uma combinacao de dados que trava o fluxo. Revise os campos marcados abaixo.',
            }
        )

    initial_step = 2 if any(item.get('step') == 2 for item in items) else 1

    return {
        'title': 'Vamos destravar isso por etapa',
        'copy': 'O box separou onde travou para voce corrigir sem cacar erro no formulario inteiro.',
        'initial_step': initial_step,
        'items': items,
    }


def build_student_form_flow_state(*, financial_ready, recovery_guide, selected_intake, latest_enrollment, page_mode):
    if recovery_guide and recovery_guide.get('initial_step') == 2:
        return {
            'headline': 'Corrija plano e cobranca antes de descer para o financeiro.',
            'copy': 'O fluxo ja mostrou que o atrito esta no fechamento comercial. Resolva plano, estrategia e confirmacao para o restante da ficha voltar a fluir.',
            'registration_card_class': 'is-ready',
            'registration_button_label': 'Revisar identificacao',
            'registration_href': '#student-form-essential',
            'registration_step': 1,
            'commercial_kicker': '02 Fechamento',
            'commercial_title': 'Plano e cobranca pedem ajuste agora.',
            'commercial_copy': 'O bloqueio atual esta no fechamento comercial. Corrija esta etapa antes de abrir a camada financeira.',
            'commercial_card_class': 'is-current',
            'commercial_button_label': 'Corrigir fechamento',
            'commercial_href': '#student-form-plan',
            'commercial_step': 2,
        }

    if recovery_guide:
        return {
            'headline': 'Destrave o cadastro antes de avancar para o comercial.',
            'copy': 'A ficha ja separou onde ficou o atrito. Corrija identidade, perfil ou saude sem sair cacando erro no formulario inteiro.',
            'registration_card_class': 'is-current',
            'registration_button_label': 'Corrigir cadastro',
            'registration_href': '#student-form-essential',
            'registration_step': 1,
            'commercial_kicker': '02 Fechamento',
            'commercial_title': 'Plano e cobranca entram depois do cadastro.',
            'commercial_copy': 'Quando a base estiver coerente, o fechamento comercial volta a ser a proxima camada natural da conversa.',
            'commercial_card_class': 'is-muted',
            'commercial_button_label': 'Ver fechamento',
            'commercial_href': '#student-form-plan',
            'commercial_step': 2,
        }

    if financial_ready:
        enrollment_name = latest_enrollment.plan.name if latest_enrollment and getattr(latest_enrollment, 'plan', None) else 'o vinculo atual'
        return {
            'headline': 'Cadastro pronto. Agora a conversa pode descer para o financeiro.',
            'copy': f'O aluno ja existe na base e {enrollment_name} sustenta a proxima leitura sem tirar voce da ficha.',
            'registration_card_class': 'is-ready',
            'registration_button_label': 'Revisar cadastro',
            'registration_href': '#student-form-essential',
            'registration_step': 1,
            'commercial_kicker': '02 Financeiro',
            'commercial_title': 'Vinculo, cobranca e historico no mesmo workspace.',
            'commercial_copy': 'Use a camada financeira para revisar plano, acao pendente e historico sem perder o contexto da ficha.',
            'commercial_card_class': 'is-current',
            'commercial_button_label': 'Abrir financeiro',
            'commercial_href': '#student-form-financial',
            'commercial_step': None,
        }

    intake_copy = (
        f'Esta ficha ja nasceu de {selected_intake.full_name}. Termine o essencial e feche o comercial sem quebrar o fio da conversa.'
        if selected_intake else
        'Primeiro confirme identidade e contexto. Depois use plano e cobranca para fechar o comercial sem retrabalho.'
    )

    return {
        'headline': 'Cadastro primeiro. Plano e cobranca depois.',
        'copy': intake_copy if page_mode == 'create' else 'Revise o nucleo do cadastro antes de mexer na camada comercial. Isso reduz ruido e evita voltar etapas depois.',
        'registration_card_class': 'is-current',
        'registration_button_label': 'Abrir cadastro',
        'registration_href': '#student-form-essential',
        'registration_step': 1,
        'commercial_kicker': '02 Fechamento',
        'commercial_title': 'Plano e cobranca fecham a jornada da ficha.',
        'commercial_copy': 'Quando o cadastro estiver coerente, va para o fechamento comercial e so depois abra o workspace financeiro.',
        'commercial_card_class': 'is-muted',
        'commercial_button_label': 'Ir para fechamento',
        'commercial_href': '#student-form-plan',
        'commercial_step': 2,
    }


def build_student_form_page(*, form, student_object, selected_intake, financial_overview, page_mode, current_role_slug):
    latest_enrollment = financial_overview.get('latest_enrollment')
    recent_payments = financial_overview.get('payments', [])
    financial_ready = financial_overview.get('has_student', False)
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
    initial_form_step = recovery_guide.get('initial_step', 1) if recovery_guide else 1
    flow_state = build_student_form_flow_state(
        financial_ready=financial_ready,
        recovery_guide=recovery_guide,
        selected_intake=selected_intake,
        latest_enrollment=latest_enrollment,
        page_mode=page_mode,
    )
    student_form_handoff = None
    if financial_ready:
        enrollment_name = latest_enrollment.plan.name if latest_enrollment and getattr(latest_enrollment, 'plan', None) else 'o contexto financeiro do aluno'
        student_form_handoff = {
            'title': 'Fechamento pronto. A proxima acao oficial esta no financeiro.',
            'copy': f'Assim que salvar esta etapa, desca para o workspace financeiro e revise {enrollment_name}, historico e proxima acao sem quebrar o contexto da ficha.',
            'href': '#student-form-financial',
            'href_label': 'Seguir para o financeiro',
            'data_action': 'open-tab-student-form-financial',
        }
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
            {
                'label': 'Ver plano e cobranca' if financial_ready else 'Fechar cadastro primeiro',
                'href': '#student-form-financial' if financial_ready else '#student-form-essential',
                'kind': 'secondary',
                'data_action': 'open-tab-student-form-financial' if financial_ready else 'open-tab-student-form-essential',
            },
            {'label': 'Voltar para alunos', 'href': get_shell_route_url('students'), 'kind': 'secondary'},
        ],
        aria_label='Ficha do aluno',
        classes=['student-hero', 'student-form-hero'],
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
            'student_form_flow_state': flow_state,
            'student_form_handoff': student_form_handoff,
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
            'financial_ready': financial_ready,
            'student_form_initial_step': initial_form_step,
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

