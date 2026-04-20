"""
ARQUIVO: dispatcher de intents da Central de Intake.

POR QUE ELE EXISTE:
- tira da view o roteamento do post para quick create, fila e handoff de convite.

O QUE ESTE ARQUIVO FAZ:
1. identifica a intent do post da central.
2. despacha para quick create, queue action ou invite.
3. preserva mensagens e redirects do fluxo anterior.

PONTOS CRITICOS:
- qualquer mudanca aqui pode mandar uma acao valida para o corredor errado.
- o dispatcher nao deve inventar regra de negocio; ele apenas encaminha.
"""

from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse

from access.roles import ROLE_MANAGER, ROLE_OWNER, ROLE_RECEPTION

from .forms import IntakeQueueActionForm
from .intake_actions import create_intake_quick_entry, execute_intake_queue_form
from .intake_invite_actions import send_intake_whatsapp_invite


def dispatch_intake_center_post(*, view, request):
    role_slug = view._get_current_role_slug()
    if request.POST.get('action') == 'send-whatsapp-invite':
        if role_slug not in (ROLE_OWNER, ROLE_MANAGER, ROLE_RECEPTION):
            messages.error(request, 'Seu papel atual nao pode disparar convites do app para leads.')
            return redirect(view._get_success_url(request.POST.get('return_query', '')))
        return send_intake_whatsapp_invite(
            request=request,
            role_slug=role_slug,
            get_success_url=view._get_success_url,
        )

    if request.POST.get('form_kind') == 'quick-create':
        return _handle_intake_quick_create(view=view, request=request, role_slug=role_slug)

    return _handle_intake_queue_action(view=view, request=request, role_slug=role_slug)


def _handle_intake_quick_create(*, view, request, role_slug: str):
    if role_slug not in (ROLE_OWNER, ROLE_MANAGER, ROLE_RECEPTION):
        messages.error(request, 'Seu papel atual pode consultar a central, mas nao cadastrar entradas por esta tela.')
        return redirect(reverse('intake-center'))

    entry_kind = (request.POST.get('entry_kind', 'lead') or '').strip().lower()
    if entry_kind not in ('lead', 'intake'):
        entry_kind = 'lead'

    form = view._build_create_form(entry_kind=entry_kind, bound_data=request.POST)
    if not form.is_valid():
        context_kwargs = {
            'active_panel': view.PANEL_CREATE_LEAD if entry_kind == 'lead' else view.PANEL_CREATE_INTAKE,
            'lead_create_form': form if entry_kind == 'lead' else view._build_create_form(entry_kind='lead'),
            'intake_create_form': form if entry_kind == 'intake' else view._build_create_form(entry_kind='intake'),
        }
        return view.render_to_response(view.get_context_data(**context_kwargs))

    create_intake_quick_entry(
        actor=request.user,
        form=form,
        entry_kind=entry_kind,
    )
    entry_label = 'Lead' if entry_kind == 'lead' else 'Intake'
    messages.success(request, f'{entry_label} cadastrado com sucesso na Central de Intake.')
    return redirect(view._get_quick_create_success_url(entry_kind))


def _handle_intake_queue_action(*, view, request, role_slug: str):
    if role_slug not in (ROLE_OWNER, ROLE_MANAGER, ROLE_RECEPTION):
        messages.error(request, 'Seu papel atual pode consultar a central, mas nao executar a fila por esta tela.')
        return redirect(view._get_success_url())

    form = IntakeQueueActionForm(request.POST)
    if not form.is_valid():
        messages.error(request, 'A acao de entradas nao foi entendida. Revise a fila e tente novamente.')
        return redirect(view._get_success_url(request.POST.get('return_query', '')))

    try:
        result = execute_intake_queue_form(
            actor=request.user,
            form=form,
        )
    except ValueError as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, result.message)

    return redirect(view._get_success_url(form.cleaned_data.get('return_query', '')))


__all__ = ['dispatch_intake_center_post']
