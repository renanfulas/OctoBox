"""
ARQUIVO: views da grade de aulas do catalogo.

POR QUE ELE EXISTE:
- Isola a camada HTTP da leitura visual de agenda e ocupacao de aulas.

O QUE ESTE ARQUIVO FAZ:
1. Renderiza a grade visual de aulas.
2. Consome o snapshot de agenda vindo da camada de queries.

PONTOS CRITICOS:
- Esta tela depende do snapshot de agenda e da coerencia de datas no contexto base.
"""

from django.contrib import messages
from django.http import QueryDict
from django.shortcuts import redirect
from django.urls import reverse

from boxcore.access.roles import ROLE_MANAGER, ROLE_OWNER
from boxcore.catalog.services import (
    handle_class_session_cancel_action,
    handle_class_session_duplicate_action,
    handle_class_session_update_action,
    run_class_schedule_create_workflow,
)
from boxcore.models import ClassSession

from ..forms import ClassScheduleRecurringForm, ClassSessionQuickEditForm
from ..class_grid_queries import build_class_grid_snapshot
from .catalog_base_views import CatalogBaseView
from django.views.generic import FormView


class ClassGridView(CatalogBaseView, FormView):
    template_name = 'catalog/class-grid.html'
    form_class = ClassScheduleRecurringForm

    def get_success_url(self):
        query_string = self._get_return_query_string()
        url = reverse('class-grid')
        return f'{url}?{query_string}' if query_string else url

    def _get_return_query_string(self):
        if self.request.method == 'POST':
            return (self.request.POST.get('return_query') or '').strip()
        filter_query = self.request.GET.copy()
        filter_query.pop('edit_session', None)
        return filter_query.urlencode()

    def _get_filter_params(self):
        if self.request.method == 'POST' and self.request.POST.get('return_query'):
            return QueryDict(self.request.POST.get('return_query'), mutable=False)
        return self.request.GET

    def _get_selected_session(self):
        selected_session_id = self.request.GET.get('edit_session')
        if self.request.method == 'POST':
            selected_session_id = self.request.POST.get('session_id') or selected_session_id
        if not selected_session_id:
            return None
        return ClassSession.objects.filter(pk=selected_session_id).select_related('coach').first()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_base_context())
        snapshot = build_class_grid_snapshot(context['today'], params=kwargs.get('filter_params') or self._get_filter_params())
        context['grouped_sessions'] = snapshot['grouped_sessions']
        context['today_schedule'] = snapshot['today_schedule']
        context['weekly_calendar'] = snapshot['weekly_calendar']
        context['monthly_calendar'] = snapshot['monthly_calendar']
        context['class_metrics'] = snapshot['class_metrics']
        context['selected_month_label'] = snapshot['selected_month_label']
        context['can_manage_classes'] = context['current_role'].slug in (ROLE_OWNER, ROLE_MANAGER)
        context['schedule_form'] = kwargs.get('form') or self.get_form()
        selected_session = kwargs.get('selected_session') or self._get_selected_session()
        context['selected_session'] = selected_session
        context['session_edit_form'] = kwargs.get('session_edit_form') or (ClassSessionQuickEditForm(instance=selected_session) if selected_session else None)
        context['current_query_string'] = self._get_return_query_string()
        context['class_focus'] = [
            'Use esta tela para validar rapidamente a agenda real da equipe sem abrir o admin o tempo todo.',
            'A grade agora destaca volume de reservas, pressao de lotacao e distribuicao das aulas por dia.',
            'Quando houver duvida operacional, leia primeiro a agenda daqui e depois aprofunde no workspace do coach ou no admin.',
        ]
        return context

    def post(self, request, *args, **kwargs):
        current_role = self.get_base_context()['current_role']
        if current_role.slug not in (ROLE_OWNER, ROLE_MANAGER):
            messages.error(request, 'Seu papel atual pode consultar a grade, mas nao criar aulas por esta tela.')
            return redirect(self.get_success_url())
        form_kind = request.POST.get('form_kind') or 'planner'
        if form_kind == 'session-action':
            return self._handle_session_action()
        if form_kind == 'session-edit':
            return self._handle_session_edit()
        return super().post(request, *args, **kwargs)

    def _handle_session_action(self):
        session = self._get_selected_session()
        if session is None:
            messages.error(self.request, 'A aula selecionada nao foi encontrada.')
            return redirect(self.get_success_url())

        action = self.request.POST.get('action')
        try:
            if action == 'cancel-session':
                handle_class_session_cancel_action(actor=self.request.user, session=session)
                messages.success(self.request, f'Aula {session.title} cancelada com sucesso.')
            elif action == 'duplicate-session':
                duplicated_session = handle_class_session_duplicate_action(actor=self.request.user, session=session)
                messages.success(self.request, f'Aula duplicada para {duplicated_session.scheduled_at:%d/%m %H:%M}.')
            else:
                messages.error(self.request, 'Acao rapida de aula nao reconhecida.')
        except ValueError as exc:
            messages.error(self.request, str(exc))
        return redirect(self.get_success_url())

    def _handle_session_edit(self):
        session = self._get_selected_session()
        if session is None:
            messages.error(self.request, 'A aula selecionada nao foi encontrada.')
            return redirect(self.get_success_url())

        form = ClassSessionQuickEditForm(self.request.POST, instance=session)
        if form.is_valid():
            try:
                updated_session = handle_class_session_update_action(actor=self.request.user, session=session, form=form)
            except ValueError as exc:
                form.add_error(None, str(exc))
            else:
                messages.success(self.request, f'Aula {updated_session.title} atualizada com sucesso.')
                query_string = self._get_return_query_string()
                url = reverse('class-grid')
                if query_string:
                    return redirect(f'{url}?{query_string}')
                return redirect(url)

        messages.error(self.request, 'A aula nao foi atualizada. Revise os campos destacados.')
        filter_params = QueryDict(self._get_return_query_string(), mutable=False)
        return self.render_to_response(
            self.get_context_data(
                filter_params=filter_params,
                selected_session=session,
                session_edit_form=form,
            )
        )

    def form_valid(self, form):
        try:
            result = run_class_schedule_create_workflow(actor=self.request.user, form=form)
        except ValueError as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)
        created_count = len(result['created_sessions'])
        skipped_count = len(result['skipped_slots'])
        if created_count == 0 and skipped_count > 0:
            messages.error(self.request, 'Nenhuma aula nova foi criada porque todos os horarios escolhidos ja existiam.')
        else:
            message = f'{created_count} aula(s) criada(s) com sucesso.'
            if skipped_count:
                message += f' {skipped_count} horario(s) ja existiam e foram pulados.'
            messages.success(self.request, message)
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'A agenda nao foi criada. Revise os campos destacados do planejador.')
        return super().form_invalid(form)