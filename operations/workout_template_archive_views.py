"""
ARQUIVO: endpoints HTTP de arquivamento de templates de WOD.

POR QUE ELE EXISTE:
- separa as rotas de archive/restore do workout_template_views.py já cheio.

O QUE ESTE ARQUIVO FAZ:
1. WorkoutTemplateArchiveView    — POST: arquiva um template individual.
2. WorkoutTemplateArchiveAllView — POST: arquiva todos (exige confirmação "ARQUIVAR").
3. WorkoutTemplateRestoreView    — POST: restaura um template arquivado.

PONTOS CRÍTICOS:
- archive é reversível (archived_at + archived_by); delete definitivo não existe aqui.
- archiveAll exige formulário com campo confirmation para evitar clique acidental.
"""

from django.contrib import messages
from django.db import OperationalError, ProgrammingError
from django.shortcuts import get_object_or_404, redirect
from django.views import View

from access.roles import ROLE_COACH, ROLE_OWNER
from operations.forms_template_archive import TemplateArchiveAllForm, TemplateRestoreForm
from operations.models import WorkoutTemplate
from operations.services.workout_template_archive import (
    archive_all_templates,
    archive_template,
    restore_template,
)

from .base_views import OperationBaseView


TEMPLATE_STORAGE_EXCEPTIONS = (OperationalError, ProgrammingError)


class WorkoutTemplateArchiveView(OperationBaseView, View):
    allowed_roles = (ROLE_COACH, ROLE_OWNER)

    def post(self, request, template_id, *args, **kwargs):
        try:
            template = get_object_or_404(WorkoutTemplate, pk=template_id, archived_at__isnull=True)
        except TEMPLATE_STORAGE_EXCEPTIONS:
            messages.warning(request, 'Base de templates indisponível. Rode as migrations.')
            return redirect('workout-template-management')

        archive_template(template=template, actor=request.user)
        messages.success(request, f'"{template.name}" arquivado. Recuperável por 30 dias.')
        return redirect('workout-template-management')


class WorkoutTemplateArchiveAllView(OperationBaseView, View):
    allowed_roles = (ROLE_OWNER,)

    def post(self, request, *args, **kwargs):
        form = TemplateArchiveAllForm(request.POST)
        if not form.is_valid():
            messages.error(request, 'Confirmação inválida. Digite ARQUIVAR para confirmar.')
            return redirect('workout-template-management')

        try:
            count = archive_all_templates(box_id=None, actor=request.user)
        except TEMPLATE_STORAGE_EXCEPTIONS:
            messages.warning(request, 'Base de templates indisponível. Rode as migrations.')
            return redirect('workout-template-management')

        messages.success(request, f'{count} template(s) arquivado(s). Recuperáveis por 30 dias.')
        return redirect('workout-template-management')


class WorkoutTemplateRestoreView(OperationBaseView, View):
    allowed_roles = (ROLE_COACH, ROLE_OWNER)

    def post(self, request, template_id, *args, **kwargs):
        try:
            template = get_object_or_404(WorkoutTemplate, pk=template_id, archived_at__isnull=False)
        except TEMPLATE_STORAGE_EXCEPTIONS:
            messages.warning(request, 'Base de templates indisponível. Rode as migrations.')
            return redirect('workout-template-management')

        restore_template(template=template)
        messages.success(request, f'"{template.name}" restaurado ao catálogo.')
        return redirect('workout-template-management')


__all__ = [
    'WorkoutTemplateArchiveView',
    'WorkoutTemplateArchiveAllView',
    'WorkoutTemplateRestoreView',
]
