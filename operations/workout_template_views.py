"""
ARQUIVO: corredor HTTP de templates persistentes de WOD.

POR QUE ELE EXISTE:
- separa a gestao de templates do corredor geral de workspace.

O QUE ESTE ARQUIVO FAZ:
1. publica a tela de management dos templates.
2. executa acoes de politica, metadata, blocos e movimentos.
3. protege o fluxo quando a base de templates ainda nao existe no banco.
"""

from django.contrib import messages
from django.db import OperationalError, ProgrammingError
from django.shortcuts import get_object_or_404, redirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View

from access.roles import ROLE_COACH, ROLE_OWNER
from shared_support.page_payloads import attach_page_payload

from operations.forms import (
    WorkoutApprovalPolicyForm,
    WorkoutTemplateBlockForm,
    WorkoutTemplateDuplicateForm,
    WorkoutTemplateMetadataForm,
    WorkoutTemplateMovementForm,
)
from operations.models import WorkoutTemplate, WorkoutTemplateBlock, WorkoutTemplateMovement
from operations.workout_approval_policy import update_workout_approval_policy_setting
from operations.workout_template_management_context import build_workout_template_management_context
from operations.workout_templates import delete_persisted_template, duplicate_persisted_template

from .base_views import OperationBaseView


TEMPLATE_STORAGE_EXCEPTIONS = (OperationalError, ProgrammingError)


def _handle_template_storage_unavailable(request, *, redirect_name='workout-template-management'):
    messages.warning(
        request,
        'A base de templates ainda nao esta pronta neste banco. Rode as migrations de operations para liberar esse fluxo.',
    )
    return redirect(redirect_name)


def _redirect_to_next_or_default(request, default_name='workout-template-management'):
    next_url = (request.POST.get('next') or request.GET.get('next') or '').strip()
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return redirect(next_url)
    return redirect(default_name)


class WorkoutTemplateManagementView(OperationBaseView):
    allowed_roles = (ROLE_COACH, ROLE_OWNER)
    template_name = 'operations/workout_template_management.html'
    page_title = 'Templates de WOD'
    page_subtitle = 'Catalogo minimo para ativar, inativar e ler uso dos templates.'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_base_context())
        template_context = build_workout_template_management_context(
            request=self.request,
            current_role=context['current_role'],
            page_title=self.page_title,
            page_subtitle=self.page_subtitle,
        )
        attach_page_payload(
            context,
            payload_key='operation_page',
            payload=template_context.pop('operation_page_payload'),
        )
        context.update(template_context)
        return context


class WorkoutApprovalPolicyUpdateView(OperationBaseView, View):
    allowed_roles = (ROLE_OWNER,)

    def post(self, request, *args, **kwargs):
        form = WorkoutApprovalPolicyForm(request.POST)
        if not form.is_valid():
            messages.error(request, 'Revise a politica de aprovacao antes de salvar.')
            return redirect('workout-template-management')
        setting = update_workout_approval_policy_setting(
            actor=request.user,
            approval_policy=form.cleaned_data['approval_policy'],
        )
        if setting is None:
            messages.error(request, 'Nao conseguimos resolver o box ativo para persistir a politica.')
            return redirect('workout-template-management')
        messages.success(request, 'Politica de aprovacao do box atualizada com sucesso.')
        return redirect('workout-template-management')


class WorkoutTemplateDuplicateView(OperationBaseView, View):
    allowed_roles = (ROLE_COACH, ROLE_OWNER)

    def post(self, request, template_id, *args, **kwargs):
        try:
            template = get_object_or_404(WorkoutTemplate, pk=template_id)
        except TEMPLATE_STORAGE_EXCEPTIONS:
            return _handle_template_storage_unavailable(request)
        if request.user.groups.filter(name=ROLE_COACH).exists() and template.created_by_id != request.user.id:
            messages.error(request, 'Coach so pode gerenciar templates criados por ele.')
            return redirect('workout-template-management')
        form = WorkoutTemplateDuplicateForm(request.POST)
        if not form.is_valid():
            messages.error(request, 'Revise o nome antes de duplicar o template.')
            return redirect('workout-template-management')
        try:
            duplicated = duplicate_persisted_template(
                actor=request.user,
                template=template,
                name=form.cleaned_data.get('name') or '',
            )
        except TEMPLATE_STORAGE_EXCEPTIONS:
            return _handle_template_storage_unavailable(request)
        messages.success(request, f'Template "{duplicated.name}" duplicado com sucesso.')
        return _redirect_to_next_or_default(request)


class WorkoutTemplateDeleteView(OperationBaseView, View):
    allowed_roles = (ROLE_COACH, ROLE_OWNER)

    def post(self, request, template_id, *args, **kwargs):
        try:
            template = get_object_or_404(WorkoutTemplate, pk=template_id)
        except TEMPLATE_STORAGE_EXCEPTIONS:
            return _handle_template_storage_unavailable(request)
        if request.user.groups.filter(name=ROLE_COACH).exists() and template.created_by_id != request.user.id:
            messages.error(request, 'Coach so pode gerenciar templates criados por ele.')
            return redirect('workout-template-management')
        try:
            deleted_payload = delete_persisted_template(template=template)
        except TEMPLATE_STORAGE_EXCEPTIONS:
            return _handle_template_storage_unavailable(request)
        messages.success(request, f'Template "{deleted_payload["deleted_name"]}" removido do catalogo.')
        return redirect('workout-template-management')


class WorkoutTemplateToggleActiveView(OperationBaseView, View):
    allowed_roles = (ROLE_COACH, ROLE_OWNER)

    def post(self, request, template_id, *args, **kwargs):
        try:
            template = get_object_or_404(WorkoutTemplate, pk=template_id)
        except TEMPLATE_STORAGE_EXCEPTIONS:
            return _handle_template_storage_unavailable(request)
        if request.user.groups.filter(name=ROLE_COACH).exists() and template.created_by_id != request.user.id:
            messages.error(request, 'Coach so pode gerenciar templates criados por ele.')
            return redirect('workout-template-management')
        template.is_active = not template.is_active
        try:
            template.save(update_fields=['is_active', 'updated_at'])
        except TEMPLATE_STORAGE_EXCEPTIONS:
            return _handle_template_storage_unavailable(request)
        messages.success(request, f'Template "{template.name}" {"ativado" if template.is_active else "inativado"}.')
        return redirect('workout-template-management')


class WorkoutTemplateToggleFeaturedView(OperationBaseView, View):
    allowed_roles = (ROLE_COACH, ROLE_OWNER)

    def post(self, request, template_id, *args, **kwargs):
        try:
            template = get_object_or_404(WorkoutTemplate, pk=template_id)
        except TEMPLATE_STORAGE_EXCEPTIONS:
            return _handle_template_storage_unavailable(request)
        if request.user.groups.filter(name=ROLE_COACH).exists() and template.created_by_id != request.user.id:
            messages.error(request, 'Coach so pode gerenciar templates criados por ele.')
            return redirect('workout-template-management')
        template.is_featured = not template.is_featured
        try:
            template.save(update_fields=['is_featured', 'updated_at'])
        except TEMPLATE_STORAGE_EXCEPTIONS:
            return _handle_template_storage_unavailable(request)
        messages.success(request, f'Template "{template.name}" {"destacado" if template.is_featured else "normalizado"}.')
        return redirect('workout-template-management')


class WorkoutTemplateUpdateMetadataView(OperationBaseView, View):
    allowed_roles = (ROLE_COACH, ROLE_OWNER)

    def post(self, request, template_id, *args, **kwargs):
        try:
            template = get_object_or_404(WorkoutTemplate, pk=template_id)
        except TEMPLATE_STORAGE_EXCEPTIONS:
            return _handle_template_storage_unavailable(request)
        if request.user.groups.filter(name=ROLE_COACH).exists() and template.created_by_id != request.user.id:
            messages.error(request, 'Coach so pode gerenciar templates criados por ele.')
            return redirect('workout-template-management')
        form = WorkoutTemplateMetadataForm(request.POST)
        if not form.is_valid():
            messages.error(request, 'Revise nome e metadados do template.')
            return redirect('workout-template-management')
        template.name = form.cleaned_data['name']
        template.description = (form.cleaned_data.get('description') or '').strip()
        template.is_featured = bool(form.cleaned_data.get('is_featured'))
        template.is_trusted = bool(form.cleaned_data.get('is_trusted'))
        try:
            template.save(update_fields=['name', 'description', 'is_featured', 'is_trusted', 'updated_at'])
        except TEMPLATE_STORAGE_EXCEPTIONS:
            return _handle_template_storage_unavailable(request)
        messages.success(request, f'Metadados do template "{template.name}" atualizados.')
        return redirect('workout-template-management')


class WorkoutTemplateUpdateBlockView(OperationBaseView, View):
    allowed_roles = (ROLE_COACH, ROLE_OWNER)

    def post(self, request, block_id, *args, **kwargs):
        try:
            block = get_object_or_404(WorkoutTemplateBlock, pk=block_id)
        except TEMPLATE_STORAGE_EXCEPTIONS:
            return _handle_template_storage_unavailable(request)
        if request.user.groups.filter(name=ROLE_COACH).exists() and block.template.created_by_id != request.user.id:
            messages.error(request, 'Coach so pode editar templates criados por ele.')
            return redirect('workout-template-management')
        form = WorkoutTemplateBlockForm(request.POST)
        if not form.is_valid():
            messages.error(request, 'Revise os dados do bloco do template.')
            return redirect('workout-template-management')
        block.title = form.cleaned_data['title']
        block.kind = form.cleaned_data['kind']
        block.notes = form.cleaned_data['notes']
        block.sort_order = form.cleaned_data['sort_order']
        try:
            block.save(update_fields=['title', 'kind', 'notes', 'sort_order', 'updated_at'])
        except TEMPLATE_STORAGE_EXCEPTIONS:
            return _handle_template_storage_unavailable(request)
        messages.success(request, f'Bloco "{block.title}" do template atualizado.')
        return redirect('workout-template-management')


class WorkoutTemplateCreateBlockView(OperationBaseView, View):
    allowed_roles = (ROLE_COACH, ROLE_OWNER)

    def post(self, request, template_id, *args, **kwargs):
        try:
            template = get_object_or_404(WorkoutTemplate, pk=template_id)
        except TEMPLATE_STORAGE_EXCEPTIONS:
            return _handle_template_storage_unavailable(request)
        if request.user.groups.filter(name=ROLE_COACH).exists() and template.created_by_id != request.user.id:
            messages.error(request, 'Coach so pode editar templates criados por ele.')
            return redirect('workout-template-management')
        form = WorkoutTemplateBlockForm(request.POST)
        if not form.is_valid():
            messages.error(request, 'Revise os dados do novo bloco do template.')
            return redirect('workout-template-management')
        try:
            block = WorkoutTemplateBlock.objects.create(
                template=template,
                title=form.cleaned_data['title'],
                kind=form.cleaned_data['kind'],
                notes=form.cleaned_data['notes'],
                sort_order=form.cleaned_data['sort_order'],
            )
        except TEMPLATE_STORAGE_EXCEPTIONS:
            return _handle_template_storage_unavailable(request)
        messages.success(request, f'Bloco "{block.title}" criado no template.')
        return redirect('workout-template-management')


class WorkoutTemplateDeleteBlockView(OperationBaseView, View):
    allowed_roles = (ROLE_COACH, ROLE_OWNER)

    def post(self, request, block_id, *args, **kwargs):
        try:
            block = get_object_or_404(WorkoutTemplateBlock, pk=block_id)
        except TEMPLATE_STORAGE_EXCEPTIONS:
            return _handle_template_storage_unavailable(request)
        if request.user.groups.filter(name=ROLE_COACH).exists() and block.template.created_by_id != request.user.id:
            messages.error(request, 'Coach so pode editar templates criados por ele.')
            return redirect('workout-template-management')
        title = block.title
        try:
            block.delete()
        except TEMPLATE_STORAGE_EXCEPTIONS:
            return _handle_template_storage_unavailable(request)
        messages.success(request, f'Bloco "{title}" removido do template.')
        return redirect('workout-template-management')


class WorkoutTemplateMoveBlockView(OperationBaseView, View):
    allowed_roles = (ROLE_COACH, ROLE_OWNER)

    def post(self, request, block_id, direction, *args, **kwargs):
        try:
            block = get_object_or_404(WorkoutTemplateBlock, pk=block_id)
        except TEMPLATE_STORAGE_EXCEPTIONS:
            return _handle_template_storage_unavailable(request)
        if request.user.groups.filter(name=ROLE_COACH).exists() and block.template.created_by_id != request.user.id:
            messages.error(request, 'Coach so pode editar templates criados por ele.')
            return redirect('workout-template-management')
        siblings = list(block.template.blocks.order_by('sort_order', 'id'))
        index = siblings.index(block)
        target_index = index - 1 if direction == 'up' else index + 1
        if target_index < 0 or target_index >= len(siblings):
            return redirect('workout-template-management')
        target = siblings[target_index]
        block.sort_order, target.sort_order = target.sort_order, block.sort_order
        try:
            block.save(update_fields=['sort_order', 'updated_at'])
            target.save(update_fields=['sort_order', 'updated_at'])
        except TEMPLATE_STORAGE_EXCEPTIONS:
            return _handle_template_storage_unavailable(request)
        messages.success(request, f'Ordem do bloco "{block.title}" atualizada.')
        return redirect('workout-template-management')


class WorkoutTemplateUpdateMovementView(OperationBaseView, View):
    allowed_roles = (ROLE_COACH, ROLE_OWNER)

    def post(self, request, movement_id, *args, **kwargs):
        try:
            movement = get_object_or_404(WorkoutTemplateMovement, pk=movement_id)
        except TEMPLATE_STORAGE_EXCEPTIONS:
            return _handle_template_storage_unavailable(request)
        if request.user.groups.filter(name=ROLE_COACH).exists() and movement.block.template.created_by_id != request.user.id:
            messages.error(request, 'Coach so pode editar templates criados por ele.')
            return redirect('workout-template-management')
        form = WorkoutTemplateMovementForm(request.POST)
        if not form.is_valid():
            messages.error(request, 'Revise os dados do movimento do template.')
            return redirect('workout-template-management')
        movement.movement_slug = form.cleaned_data['movement_slug']
        movement.movement_label = form.cleaned_data['movement_label']
        movement.sets = form.cleaned_data['sets']
        movement.reps = form.cleaned_data['reps']
        movement.load_type = form.cleaned_data['load_type']
        movement.load_value = form.cleaned_data['load_value']
        movement.notes = form.cleaned_data['notes']
        movement.sort_order = form.cleaned_data['sort_order']
        try:
            movement.save(
                update_fields=[
                    'movement_slug',
                    'movement_label',
                    'sets',
                    'reps',
                    'load_type',
                    'load_value',
                    'notes',
                    'sort_order',
                    'updated_at',
                ]
            )
        except TEMPLATE_STORAGE_EXCEPTIONS:
            return _handle_template_storage_unavailable(request)
        messages.success(request, f'Movimento "{movement.movement_label}" do template atualizado.')
        return redirect('workout-template-management')


class WorkoutTemplateCreateMovementView(OperationBaseView, View):
    allowed_roles = (ROLE_COACH, ROLE_OWNER)

    def post(self, request, block_id, *args, **kwargs):
        try:
            block = get_object_or_404(WorkoutTemplateBlock, pk=block_id)
        except TEMPLATE_STORAGE_EXCEPTIONS:
            return _handle_template_storage_unavailable(request)
        if request.user.groups.filter(name=ROLE_COACH).exists() and block.template.created_by_id != request.user.id:
            messages.error(request, 'Coach so pode editar templates criados por ele.')
            return redirect('workout-template-management')
        form = WorkoutTemplateMovementForm(request.POST)
        if not form.is_valid():
            messages.error(request, 'Revise os dados do novo movimento do template.')
            return redirect('workout-template-management')
        try:
            movement = WorkoutTemplateMovement.objects.create(
                block=block,
                movement_slug=form.cleaned_data['movement_slug'],
                movement_label=form.cleaned_data['movement_label'],
                sets=form.cleaned_data['sets'],
                reps=form.cleaned_data['reps'],
                load_type=form.cleaned_data['load_type'],
                load_value=form.cleaned_data['load_value'],
                notes=form.cleaned_data['notes'],
                sort_order=form.cleaned_data['sort_order'],
            )
        except TEMPLATE_STORAGE_EXCEPTIONS:
            return _handle_template_storage_unavailable(request)
        messages.success(request, f'Movimento "{movement.movement_label}" criado no template.')
        return redirect('workout-template-management')


class WorkoutTemplateDeleteMovementView(OperationBaseView, View):
    allowed_roles = (ROLE_COACH, ROLE_OWNER)

    def post(self, request, movement_id, *args, **kwargs):
        try:
            movement = get_object_or_404(WorkoutTemplateMovement, pk=movement_id)
        except TEMPLATE_STORAGE_EXCEPTIONS:
            return _handle_template_storage_unavailable(request)
        if request.user.groups.filter(name=ROLE_COACH).exists() and movement.block.template.created_by_id != request.user.id:
            messages.error(request, 'Coach so pode editar templates criados por ele.')
            return redirect('workout-template-management')
        label = movement.movement_label
        try:
            movement.delete()
        except TEMPLATE_STORAGE_EXCEPTIONS:
            return _handle_template_storage_unavailable(request)
        messages.success(request, f'Movimento "{label}" removido do template.')
        return redirect('workout-template-management')


class WorkoutTemplateMoveMovementView(OperationBaseView, View):
    allowed_roles = (ROLE_COACH, ROLE_OWNER)

    def post(self, request, movement_id, direction, *args, **kwargs):
        try:
            movement = get_object_or_404(WorkoutTemplateMovement, pk=movement_id)
        except TEMPLATE_STORAGE_EXCEPTIONS:
            return _handle_template_storage_unavailable(request)
        if request.user.groups.filter(name=ROLE_COACH).exists() and movement.block.template.created_by_id != request.user.id:
            messages.error(request, 'Coach so pode editar templates criados por ele.')
            return redirect('workout-template-management')
        siblings = list(movement.block.movements.order_by('sort_order', 'id'))
        index = siblings.index(movement)
        target_index = index - 1 if direction == 'up' else index + 1
        if target_index < 0 or target_index >= len(siblings):
            return redirect('workout-template-management')
        target = siblings[target_index]
        movement.sort_order, target.sort_order = target.sort_order, movement.sort_order
        try:
            movement.save(update_fields=['sort_order', 'updated_at'])
            target.save(update_fields=['sort_order', 'updated_at'])
        except TEMPLATE_STORAGE_EXCEPTIONS:
            return _handle_template_storage_unavailable(request)
        messages.success(request, f'Ordem do movimento "{movement.movement_label}" atualizada.')
        return redirect('workout-template-management')


__all__ = [
    'WorkoutApprovalPolicyUpdateView',
    'WorkoutTemplateCreateBlockView',
    'WorkoutTemplateCreateMovementView',
    'WorkoutTemplateDeleteBlockView',
    'WorkoutTemplateDeleteMovementView',
    'WorkoutTemplateDeleteView',
    'WorkoutTemplateDuplicateView',
    'WorkoutTemplateManagementView',
    'WorkoutTemplateMoveBlockView',
    'WorkoutTemplateMoveMovementView',
    'WorkoutTemplateToggleActiveView',
    'WorkoutTemplateToggleFeaturedView',
    'WorkoutTemplateUpdateBlockView',
    'WorkoutTemplateUpdateMetadataView',
    'WorkoutTemplateUpdateMovementView',
]
