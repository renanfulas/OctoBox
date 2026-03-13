"""
ARQUIVO: views da grade de aulas do catalogo.

POR QUE ELE EXISTE:
- publica a casca HTTP da grade no app catalog.
"""

from django.contrib import messages
from django.http import QueryDict
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import FormView

from access.roles import ROLE_MANAGER, ROLE_OWNER, ROLE_RECEPTION
from catalog.class_grid_queries import build_class_grid_snapshot
from catalog.forms import ClassScheduleRecurringForm, ClassSessionQuickEditForm
from operations.facade import run_class_schedule_create, run_class_session_delete, run_class_session_update
from operations.application import class_grid_messages as grid_messages
from operations.application.class_grid_dispatcher import (
    FORM_KIND_SESSION_ACTION,
    FORM_KIND_SESSION_EDIT,
    SESSION_ACTION_DELETE,
    resolve_class_grid_form_kind,
    resolve_class_grid_session_action,
)
from operations.models import ClassSession

from .catalog_base_views import CatalogBaseView


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
        role_slug = context['current_role'].slug
        context['can_manage_classes'] = role_slug in (ROLE_OWNER, ROLE_MANAGER)
        context['can_open_class_admin'] = role_slug in (ROLE_OWNER, ROLE_MANAGER)
        context['schedule_form'] = kwargs.get('form') or self.get_form()
        selected_session = kwargs.get('selected_session') or self._get_selected_session()
        context['selected_session'] = selected_session
        context['session_edit_form'] = kwargs.get('session_edit_form') or (ClassSessionQuickEditForm(instance=selected_session) if selected_session else None)
        context['current_query_string'] = self._get_return_query_string()
        today_schedule = snapshot['today_schedule']
        grouped_sessions = snapshot['grouped_sessions']
        monthly_calendar = snapshot['monthly_calendar']
        today_sessions = today_schedule['sessions'] if today_schedule else []
        today_pressure_count = sum(
            1 for item in today_sessions
            if item['occupied_slots'] >= item['capacity'] or item['occupancy_percent'] >= 85
        )
        busiest_day = max(grouped_sessions, key=lambda item: len(item['sessions']), default=None)
        busy_days = sum(
            1
            for week in monthly_calendar
            for day in week
            if day['is_in_month'] and day['session_count'] >= 8
        )
        free_days = sum(
            1
            for week in monthly_calendar
            for day in week
            if day['is_in_month'] and day['session_count'] == 0
        )
        context['class_grid_operational_focus'] = [
            {
                'title': 'Comece pelo ritmo de hoje',
                'summary': (
                    f"{len(today_sessions)} aula(s) entram no dia e {today_pressure_count} horario(s) ja pedem olho na lotacao."
                    if today_schedule else
                    'Nao ha aula marcada hoje, entao vale revisar o restante da janela para nao descobrir vazios tarde demais.'
                ),
                'action_label': 'Abrir agenda de hoje',
                'action_href': '#today-board',
            },
            {
                'title': 'Depois leia o pico da janela',
                'summary': (
                    f"O maior volume da janela cai em {busiest_day['date'].strftime('%d/%m')} com {len(busiest_day['sessions'])} aula(s)."
                    if busiest_day else
                    'A janela atual ainda nao tem concentracao suficiente para gerar pico de agenda.'
                ),
                'action_label': 'Ver visao semanal',
                'action_href': '#weekly-board',
            },
            {
                'title': 'Feche com o ajuste do mes',
                'summary': (
                    f"O mes tem {busy_days} dia(s) com agenda carregada e {free_days} dia(s) livres para redistribuir a grade."
                    if context['can_manage_classes'] else
                    f"O mes mostra {busy_days} dia(s) carregados e {free_days} dia(s) livres para voce acompanhar com antecedencia."
                ),
                'action_label': 'Abrir mapa do mes' if not context['can_manage_classes'] else 'Revisar mes e planner',
                'action_href': '#monthly-board' if not context['can_manage_classes'] else '#planner-board',
            },
        ]
        context['class_focus'] = [
            'Use esta tela para validar rapidamente a agenda real da equipe sem abrir o admin toda hora.',
            'A grade destaca volume de reservas, pressao de lotacao e distribuicao das aulas por dia.',
            'Quando houver duvida operacional, leia primeiro a agenda daqui e depois aprofunde no workspace do coach ou no admin.',
        ]
        return context

    def post(self, request, *args, **kwargs):
        current_role = self.get_base_context()['current_role']
        if current_role.slug not in (ROLE_OWNER, ROLE_MANAGER):
            messages.error(request, grid_messages.ROLE_CANNOT_MANAGE_CLASSES)
            return redirect(self.get_success_url())
        try:
            form_kind = resolve_class_grid_form_kind(request.POST)
        except ValueError as exc:
            messages.error(request, str(exc))
            return redirect(self.get_success_url())
        if form_kind == FORM_KIND_SESSION_ACTION:
            return self._handle_session_action()
        if form_kind == FORM_KIND_SESSION_EDIT:
            return self._handle_session_edit()
        return super().post(request, *args, **kwargs)

    def _handle_session_action(self):
        session = self._get_selected_session()
        if session is None:
            messages.error(self.request, grid_messages.SESSION_NOT_FOUND)
            return redirect(self.get_success_url())

        try:
            action = resolve_class_grid_session_action(self.request.POST)
        except ValueError as exc:
            messages.error(self.request, str(exc))
            return redirect(self.get_success_url())

        try:
            if action == SESSION_ACTION_DELETE:
                result = run_class_session_delete(actor=self.request.user, session=session)
            else:
                raise ValueError(grid_messages.UNKNOWN_SESSION_ACTION)
            messages.success(self.request, result.message)
        except ValueError as exc:
            messages.error(self.request, str(exc))
        return redirect(self.get_success_url())

    def _handle_session_edit(self):
        session = self._get_selected_session()
        if session is None:
            messages.error(self.request, grid_messages.SESSION_NOT_FOUND)
            return redirect(self.get_success_url())

        form = ClassSessionQuickEditForm(self.request.POST, instance=session)
        if form.is_valid():
            try:
                result = run_class_session_update(actor=self.request.user, session=session, form=form)
            except ValueError as exc:
                form.add_error(None, str(exc))
            else:
                messages.success(self.request, result.message)
                query_string = self._get_return_query_string()
                url = reverse('class-grid')
                if query_string:
                    return redirect(f'{url}?{query_string}')
                return redirect(url)

        messages.error(self.request, grid_messages.SESSION_UPDATE_INVALID)
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
            result = run_class_schedule_create(actor=self.request.user, form=form)
        except ValueError as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)
        created_count = len(result.created_sessions)
        skipped_count = len(result.skipped_slots)
        if created_count == 0 and skipped_count > 0:
            messages.error(self.request, grid_messages.PLANNER_SKIPPED_ONLY)
        else:
            messages.success(self.request, grid_messages.planner_success(created_count, skipped_count))
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, grid_messages.PLANNER_INVALID)
        return super().form_invalid(form)
