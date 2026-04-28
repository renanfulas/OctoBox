"""
ARQUIVO: views da area de alunos do catalogo.

POR QUE ELE EXISTE:
- publica a casca HTTP de diretorio, cadastro leve e acoes da ficha no app catalog.

O QUE ESTE ARQUIVO FAZ:
1. Diretorio de alunos com paginacao e preaquecimento de cache.
2. Formulario leve de cadastro e edicao de aluno.
3. Acoes de pagamento e matricula na ficha do aluno.
4. Lock de edicao com hierarquia de papeis (Owner > Manager > Recep > Coach).
5. Endpoints de heartbeat e polling de lock para o frontend.

PONTOS CRITICOS:
- O lock usa Redis. Se Redis cair, o sistema degrada de forma segura (sem lock, aceita a edicao).
- Dev nao participa do lock operacional: ve a ficha sem adquirir lock.
"""

import json
import time
from urllib.parse import unquote

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.signing import BadSignature, SignatureExpired
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import FormView

from shared_support.decorators import idempotent_action
from shared_support.editing_locks import (
    acquire_student_lock,
    get_student_lock_status,
    release_student_lock,
)
from shared_support.student_event_stream import build_student_event_stream, publish_student_stream_event

from access.permissions import AjaxLoginRequiredMixin, RoleRequiredMixin
from access.roles import ROLE_DEV, ROLE_MANAGER, ROLE_OWNER, ROLE_RECEPTION, get_user_role
from catalog.student_directory_context import (
    build_student_directory_view_context,
    build_student_search_index_payload,
)
from catalog.student_drawer_context import (
    build_student_browser_snapshot,
    build_student_drawer_fragments,
    build_student_drawer_fragments_response,
    build_student_snapshot_response,
)
from catalog.student_financial_http import (
    STUDENT_FINANCIAL_FRAGMENT,
    build_student_financial_json_error as _student_financial_json_error,
    build_student_financial_json_response as _student_financial_json_response,
    expects_student_financial_json_response as _expects_json_response,
    handle_student_enrollment_action_request,
    handle_student_payment_action_request,
)
from catalog.student_form_actions import (
    execute_student_drawer_profile_save,
    enforce_student_creation_throttle,
    execute_student_express_create,
    execute_student_quick_create,
    execute_student_quick_update,
    resolve_student_quick_update_lock_holder,
)
from catalog.student_form_context import (
    build_student_drawer_profile_response,
    build_student_express_page_context,
    build_student_quick_initial,
    build_student_quick_page_context,
    resolve_selected_intake,
)
from catalog.student_lock_http import build_student_lock_status_response, handle_student_lock_heartbeat
from catalog.forms import (
    StudentQuickForm,
    StudentExpressForm,
    StudentSourceDeclarationCaptureForm,
)
from catalog.student_queries import (
    _enrich_student_directory_display_students,
    build_student_directory_snapshot,
)
from quick_sales.facade import (
    run_quick_sale_cancel,
    run_quick_sale_create,
    run_quick_sale_memory_snapshot,
    run_quick_sale_refund,
)
from quick_sales.forms import QuickSaleActionForm, QuickSaleManagementForm
from quick_sales.models import QuickSale
from finance.models import Enrollment, Payment
from reporting.application.catalog_reports import build_student_directory_report
from reporting.facade import run_report_response_build
from shared_support.security import check_export_quota
from students.facade import (
    run_student_source_capture_token_build,
    run_student_source_capture_token_read,
    run_student_source_declaration_record,
)
from students.models import Student

from .catalog_base_views import CatalogBaseView


STUDENT_FORM_ESSENTIAL_FRAGMENT = 'student-form-essential'
STUDENT_DIRECTORY_FRAGMENT = 'student-directory-board'
STUDENT_DIRECTORY_PAGE_SIZE = 15
STUDENT_SEARCH_BOOTSTRAP_LIMIT = 15
STUDENT_SEARCH_INDEX_LIMIT = 200


def _append_fragment(url, fragment):
    if not fragment:
        return url
    return f'{url}#{fragment}'


def _build_student_return_context(request):
    context_key = (request.GET.get('context') or '').strip()
    return_to = (request.GET.get('return_to') or '').strip()
    if not context_key or not return_to:
        return None

    context_map = {
        'reception-payment': {
            'eyebrow': 'Voce veio do balcao',
            'title': 'Resolva a cobranca e volte para a fila sem perder o contexto.',
            'copy': 'A recepcao abriu esta ficha a partir da cobranca curta. Feche o necessario aqui e volte para o mesmo ponto do balcao.',
            'href_label': 'Voltar para cobranca',
        },
        'reception-intake': {
            'eyebrow': 'Voce veio do balcao',
            'title': 'Resolva o cadastro e volte para a fila de atendimento.',
            'copy': 'A recepcao abriu esta ficha a partir da fila de entrada. Feche o essencial sem perder o compasso do balcao.',
            'href_label': 'Voltar para entradas',
        },
    }
    if context_key not in context_map:
        return None

    return {
        'key': context_key,
        'href': unquote(return_to),
        **context_map[context_key],
    }


def _build_student_source_capture_url(*, request, student):
    token = run_student_source_capture_token_build(student_id=student.id)
    return f"{request.build_absolute_uri(reverse('student-source-capture'))}?token={token}"


def _serialize_student_browser_snapshot(*, request, student):
    return build_student_browser_snapshot(
        request=request,
        student=student,
        financial_fragment=STUDENT_FINANCIAL_FRAGMENT,
        build_source_capture_url=_build_student_source_capture_url,
        append_fragment=_append_fragment,
    )


def _serialize_student_directory_search_entry(student):
    latest_payment_due_date = getattr(student, 'latest_payment_due_date', None)
    due_label = latest_payment_due_date.strftime('%d/%m/%Y') if latest_payment_due_date else ''
    created_at = getattr(student, 'created_at', None)
    is_new_30d = getattr(student, 'is_new_30d', None)
    if is_new_30d is None:
        is_new_30d = bool(created_at and created_at >= timezone.now() - timezone.timedelta(days=30))

    return {
        'id': student.id,
        'full_name': student.full_name,
        'email': student.email or '',
        'phone': student.phone or '',
        'status': student.status,
        'is_new_30d': is_new_30d,
        'latest_plan_name': getattr(student, 'latest_plan_name', '') or '',
        'payment_status': getattr(student, 'operational_payment_status', '') or '',
        'presence_percent': getattr(student, 'presence_percent', 0) or 0,
        'due_label': due_label,
        'href': _append_fragment(reverse('student-quick-update', args=[student.id]), STUDENT_FINANCIAL_FRAGMENT),
        'snapshot_url': reverse('student-read-snapshot', args=[student.id]),
        'events_stream_url': reverse('student-event-stream', args=[student.id]),
        'drawer_fragments_url': reverse('student-drawer-fragments', args=[student.id]),
        'drawer_profile_url': reverse('student-drawer-profile-save', args=[student.id]),
        'edit_start_url': reverse('student-edit-session-start', args=[student.id]),
        'edit_release_url': reverse('student-edit-session-release', args=[student.id]),
        'lock_heartbeat_url': reverse('student-lock-heartbeat', args=[student.id]),
        'lock_status_url': reverse('student-lock-status', args=[student.id]),
    }


def _clean_student_search_index_params(params):
    index_params = params.copy()
    for key in ('query', 'page', 'student_status', 'commercial_status', 'payment_status', 'created_window'):
        if key in index_params:
            del index_params[key]
    return index_params


def _has_server_scoped_student_filters(params):
    return any(
        params.get(key)
        for key in ('student_status', 'commercial_status', 'payment_status', 'created_window')
    )


def _parse_non_negative_int(value, default=0):
    try:
        parsed_value = int(value)
    except (TypeError, ValueError):
        return default
    return max(parsed_value, 0)


def _annotate_directory_page_students(students, *, thirty_days_ago):
    for student in students:
        student.is_new_30d = bool(student.created_at and student.created_at >= thirty_days_ago)
        total_presence = getattr(student, 'recent_presence_total', 0) or 0
        attended_presence = getattr(student, 'recent_presence_attended', 0) or 0
        if total_presence > 0:
            student.presence_percent = round((attended_presence / total_presence) * 100)
        else:
            student.presence_percent = 0
    return students


def _build_student_drawer_fragments(*, request, student, form=None):
    return build_student_drawer_fragments(
        request=request,
        student=student,
        form=form,
        build_browser_snapshot=_serialize_student_browser_snapshot,
        build_source_capture_url=_build_student_source_capture_url,
    )


class StudentDirectoryView(CatalogBaseView):
    template_name = 'catalog/students.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        base_context = self.get_base_context()
        context.update(base_context)
        return build_student_directory_view_context(
            request=self.request,
            context=context,
            base_context=base_context,
            page_size_default=STUDENT_DIRECTORY_PAGE_SIZE,
            search_bootstrap_limit=STUDENT_SEARCH_BOOTSTRAP_LIMIT,
            search_index_limit=STUDENT_SEARCH_INDEX_LIMIT,
            clean_index_params=_clean_student_search_index_params,
            has_server_scoped_filters=_has_server_scoped_student_filters,
            annotate_page_students=_annotate_directory_page_students,
            serialize_search_entry=_serialize_student_directory_search_entry,
        )


class StudentSearchIndexPageView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = (ROLE_OWNER, ROLE_DEV, ROLE_MANAGER, ROLE_RECEPTION)

    def get(self, request, *args, **kwargs):
        return JsonResponse(
            build_student_search_index_payload(
                request=request,
                search_index_limit=STUDENT_SEARCH_INDEX_LIMIT,
                parse_non_negative_int=_parse_non_negative_int,
                clean_index_params=_clean_student_search_index_params,
                annotate_page_students=_annotate_directory_page_students,
                serialize_search_entry=_serialize_student_directory_search_entry,
            )
        )


class StudentQuickBaseView(CatalogBaseView, FormView):
    allowed_roles = (ROLE_OWNER, ROLE_MANAGER, ROLE_RECEPTION)
    form_class = StudentQuickForm
    template_name = 'catalog/student-form.html'
    page_mode = 'create'
    object = None

    def get_success_url(self):
        if self.object:
            if self.page_mode == 'create':
                return _append_fragment(reverse('student-quick-update', args=[self.object.id]), STUDENT_FINANCIAL_FRAGMENT)
            return _append_fragment(reverse('student-quick-update', args=[self.object.id]), STUDENT_FORM_ESSENTIAL_FRAGMENT)
        return _append_fragment(reverse('student-directory'), STUDENT_DIRECTORY_FRAGMENT)

    def get_selected_intake(self):
        return resolve_selected_intake(self.request)

    def get_initial(self):
        initial = super().get_initial()
        return build_student_quick_initial(
            initial=initial,
            selected_intake=self.get_selected_intake(),
            page_mode=self.page_mode,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        base_context = self.get_base_context()
        context.update(base_context)
        return build_student_quick_page_context(
            request=self.request,
            context=context,
            base_context=base_context,
            form=context.get('form'),
            student_object=self.object,
            page_mode=self.page_mode,
            build_browser_snapshot=_serialize_student_browser_snapshot,
            build_return_context=_build_student_return_context,
            build_source_capture_url=_build_student_source_capture_url,
        )

    def form_invalid(self, form):
        messages.error(self.request, 'O cadastro travou em alguns pontos. O box destacou o passo certo para voce corrigir sem perder contexto.')
        return super().form_invalid(form)


class StudentQuickCreateView(StudentQuickBaseView):
    page_mode = 'create'

    def dispatch(self, request, *args, **kwargs):
        throttle_response = enforce_student_creation_throttle(request=request, view=self)
        if throttle_response is not None:
            return throttle_response
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        student = execute_student_quick_create(
            request=self.request,
            form=form,
            selected_intake=self.get_selected_intake(),
        )
        if student is None:
            return self.form_invalid(form)
        self.object = student
        return super().form_valid(form)


class StudentExpressCreateView(CatalogBaseView, FormView):
    allowed_roles = (ROLE_OWNER, ROLE_MANAGER, ROLE_RECEPTION)
    form_class = StudentExpressForm
    template_name = 'catalog/student-express-form.html'

    def dispatch(self, request, *args, **kwargs):
        throttle_response = enforce_student_creation_throttle(request=request, view=self)
        if throttle_response is not None:
            return throttle_response
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        return redirect(
            execute_student_express_create(
                request=self.request,
                form=form,
                append_fragment=_append_fragment,
                financial_fragment=STUDENT_FINANCIAL_FRAGMENT,
                reverse=reverse,
            )
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        base_context = self.get_base_context()
        context.update(base_context)
        return build_student_express_page_context(context=context)


class StudentQuickUpdateView(StudentQuickBaseView):
    page_mode = 'update'
    _lock_holder = None

    def dispatch(self, request, *args, **kwargs):
        self.object = get_object_or_404(Student, pk=kwargs['student_id'])
        self._lock_holder = resolve_student_quick_update_lock_holder(request=request, student=self.object)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['student_lock_holder'] = self._lock_holder
        context['student_lock_is_blocked'] = bool(self._lock_holder)
        context['student_id_for_lock'] = self.object.id
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = self.object
        return kwargs

    def form_valid(self, form):
        result = execute_student_quick_update(
            request=self.request,
            student=self.object,
            form=form,
            selected_intake=self.get_selected_intake(),
            append_fragment=_append_fragment,
            form_fragment=STUDENT_FORM_ESSENTIAL_FRAGMENT,
            reverse=reverse,
        )
        if isinstance(result, Student):
            self.object = result
            return redirect(self.get_success_url())
        return redirect(result)


class StudentEditSessionStartView(LoginRequiredMixin, RoleRequiredMixin, View):
    """
    Inicia a sessao autoritativa de edicao da ficha do aluno.

    A leitura da ficha fica livre, mas a caneta so e entregue pelo backend
    quando o operador realmente entra em modo de edicao.
    """

    allowed_roles = (ROLE_OWNER, ROLE_MANAGER, ROLE_RECEPTION, ROLE_DEV)

    def post(self, request, student_id, *args, **kwargs):
        student = get_object_or_404(Student, pk=student_id)
        role = get_user_role(request.user)
        role_slug = getattr(role, 'slug', None)

        if not role_slug:
            return JsonResponse({'status': 'denied', 'reason': 'no_role'}, status=403)

        if role_slug == ROLE_DEV:
            return JsonResponse({'status': 'granted', 'mode': 'dev_bypass'})

        lock_result = acquire_student_lock(student.id, request.user, role_slug)
        if lock_result.acquired:
            holder_meta = {
                'user_display': request.user.get_full_name() or request.user.username,
                'role_label': getattr(role, 'name', '') or getattr(role, 'label', '') or role_slug,
            }
            if lock_result.displaced_holder:
                publish_student_stream_event(
                    student_id=student.id,
                    event_type='student.lock.preempted',
                    meta={
                        'holder': holder_meta,
                        'displaced_holder': {
                            'user_display': lock_result.displaced_holder.get('user_display', ''),
                            'role_label': lock_result.displaced_holder.get('role_label', ''),
                        },
                    },
                )
            else:
                publish_student_stream_event(
                    student_id=student.id,
                    event_type='student.lock.acquired',
                    meta={'holder': holder_meta},
                )
            return JsonResponse({'status': 'granted'})

        holder = lock_result.holder or {}
        return JsonResponse(
            {
                'status': 'blocked',
                'holder': {
                    'user_display': holder.get('user_display', ''),
                    'role_label': holder.get('role_label', ''),
                },
            },
            status=409,
        )


class StudentEditSessionReleaseView(LoginRequiredMixin, RoleRequiredMixin, View):
    """
    Libera explicitamente a sessao de edicao da ficha.
    """

    allowed_roles = (ROLE_OWNER, ROLE_MANAGER, ROLE_RECEPTION, ROLE_DEV)

    def post(self, request, student_id, *args, **kwargs):
        student = get_object_or_404(Student, pk=student_id)
        released = release_student_lock(student.id, request.user.id)
        if released:
            publish_student_stream_event(
                student_id=student.id,
                event_type='student.lock.released',
                meta={
                    'holder': {
                        'user_display': request.user.get_full_name() or request.user.username,
                    }
                },
            )
        return JsonResponse({'status': 'released' if released else 'noop'})


class StudentEventStreamView(LoginRequiredMixin, RoleRequiredMixin, View):
    """
    Stream SSE dos eventos criticos do drawer do aluno.

    Nesta primeira fase, o canal cobre lock autoritativo. O frontend usa
    o evento apenas como gatilho para atualizar snapshot/fragments oficiais.
    """

    allowed_roles = (ROLE_OWNER, ROLE_MANAGER, ROLE_RECEPTION, ROLE_DEV)

    def get(self, request, student_id, *args, **kwargs):
        get_object_or_404(Student, pk=student_id)
        return build_student_event_stream(student_id=student_id)


class StudentReadSnapshotView(LoginRequiredMixin, RoleRequiredMixin, View):
    """
    Entrega um snapshot canonico e enxuto da ficha para prefetch do navegador.

    Nao concede lock nem autoriza edicao. Apenas aquece leitura com a verdade
    server-side mais recente disponivel para o usuario autenticado.
    """

    allowed_roles = (ROLE_OWNER, ROLE_MANAGER, ROLE_RECEPTION, ROLE_DEV)

    def get(self, request, student_id, *args, **kwargs):
        student = get_object_or_404(Student, pk=student_id)
        return JsonResponse(
            build_student_snapshot_response(
                request=request,
                student=student,
                build_browser_snapshot=_serialize_student_browser_snapshot,
            )
        )


class StudentDrawerFragmentsView(LoginRequiredMixin, RoleRequiredMixin, View):
    """
    Carrega os fragments reais da ficha dentro do drawer do diretorio.

    Mantemos a navegação parcial só para leitura e edição curta do perfil,
    sem converter toda a aplicação em SPA improvisada.
    """

    allowed_roles = (ROLE_OWNER, ROLE_MANAGER, ROLE_RECEPTION, ROLE_DEV)

    def get(self, request, student_id, *args, **kwargs):
        student = get_object_or_404(Student, pk=student_id)
        return JsonResponse(
            build_student_drawer_fragments_response(
                request=request,
                student=student,
                build_browser_snapshot=_serialize_student_browser_snapshot,
                build_fragments=_build_student_drawer_fragments,
            )
        )


class StudentDrawerProfileSaveView(LoginRequiredMixin, RoleRequiredMixin, View):
    """
    Salva o perfil do aluno diretamente do drawer do diretorio.

    A regra de lock continua autoritativa no backend; o drawer apenas oferece
    uma casca mais rapida para edicao curta.
    """

    allowed_roles = (ROLE_OWNER, ROLE_MANAGER, ROLE_RECEPTION, ROLE_DEV)

    def post(self, request, student_id, *args, **kwargs):
        student = get_object_or_404(Student, pk=student_id)
        form = StudentQuickForm(request.POST, instance=student)
        response_status, response_payload = execute_student_drawer_profile_save(
            request=request,
            student=student,
            form=form,
            build_drawer_response=lambda **payload: build_student_drawer_profile_response(
                **payload,
                build_browser_snapshot=_serialize_student_browser_snapshot,
                build_drawer_fragments=_build_student_drawer_fragments,
            ),
        )
        return JsonResponse(response_payload, status=response_status)


class StudentPaymentActionView(AjaxLoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = (ROLE_OWNER, ROLE_MANAGER, ROLE_RECEPTION)

    @idempotent_action
    def post(self, request, student_id, *args, **kwargs):
        student = get_object_or_404(Student, pk=student_id)
        return handle_student_payment_action_request(request=request, student=student)


class StudentPaymentDrawerView(AjaxLoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = (ROLE_OWNER, ROLE_MANAGER, ROLE_RECEPTION)

    def get(self, request, student_id, payment_id, *args, **kwargs):
        student = get_object_or_404(Student, pk=student_id)
        payment = get_object_or_404(Payment, pk=payment_id, student=student)

        if not _expects_json_response(request):
            return redirect(_append_fragment(reverse('student-quick-update', args=[student.id]), STUDENT_FINANCIAL_FRAGMENT))

        return _student_financial_json_response(
            request=request,
            student=student,
            message=f'Cobranca de {payment.due_date:%d/%m/%Y} carregada para revisao.',
            selected_payment=payment,
        )


class StudentPaymentCheckoutDrawerView(AjaxLoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = (ROLE_OWNER, ROLE_MANAGER, ROLE_RECEPTION)

    def get(self, request, student_id, *args, **kwargs):
        student = get_object_or_404(Student, pk=student_id)

        if not _expects_json_response(request):
            return redirect(_append_fragment(reverse('student-quick-update', args=[student.id]), STUDENT_FINANCIAL_FRAGMENT))

        return _student_financial_json_response(
            request=request,
            student=student,
            message='Checkout padrao carregado para revisao.',
        )


class StudentStandalonePaymentDrawerView(AjaxLoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = (ROLE_OWNER, ROLE_MANAGER, ROLE_RECEPTION)

    def get(self, request, student_id, *args, **kwargs):
        student = get_object_or_404(Student, pk=student_id)

        if not _expects_json_response(request):
            return redirect(_append_fragment(reverse('student-quick-update', args=[student.id]), STUDENT_FINANCIAL_FRAGMENT))

        return _student_financial_json_response(
            request=request,
            student=student,
            message='Pagamento avulso pronto para preenchimento.',
            standalone_payment=True,
        )


class StudentQuickSaleDrawerView(AjaxLoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = (ROLE_OWNER, ROLE_MANAGER, ROLE_RECEPTION)

    def get(self, request, student_id, *args, **kwargs):
        student = get_object_or_404(Student, pk=student_id)

        if not _expects_json_response(request):
            return redirect(_append_fragment(reverse('student-quick-update', args=[student.id]), STUDENT_FINANCIAL_FRAGMENT))

        return _student_financial_json_response(
            request=request,
            student=student,
            message='Pagamentos rapidos carregados para registro no balcao.',
        )


class StudentQuickSaleSuggestionsView(AjaxLoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = (ROLE_OWNER, ROLE_MANAGER, ROLE_RECEPTION)

    def get(self, request, student_id, *args, **kwargs):
        student = get_object_or_404(Student, pk=student_id)

        if not _expects_json_response(request):
            return redirect(_append_fragment(reverse('student-quick-update', args=[student.id]), STUDENT_FINANCIAL_FRAGMENT))

        return JsonResponse(
            {
                'status': 'success',
                'memory': run_quick_sale_memory_snapshot(
                    student_id=student.id,
                    query=(request.GET.get('q') or '').strip(),
                ),
            }
        )


class StudentQuickSaleActionView(AjaxLoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = (ROLE_OWNER, ROLE_MANAGER, ROLE_RECEPTION)

    @idempotent_action
    def post(self, request, student_id, *args, **kwargs):
        student = get_object_or_404(Student, pk=student_id)
        expects_json = _expects_json_response(request)

        action_form = QuickSaleActionForm(request.POST)
        if not action_form.is_valid():
            error_message = 'O pagamento rapido nao foi aplicado. Revise os campos enviados.'
            if expects_json:
                return _student_financial_json_error(message=error_message, status=400)
            messages.error(request, error_message)
            return redirect(_append_fragment(reverse('student-quick-update', args=[student.id]), STUDENT_FINANCIAL_FRAGMENT))

        action = action_form.cleaned_data['action']

        try:
            if action == 'create-quick-sale':
                form = QuickSaleManagementForm(request.POST)
                if not form.is_valid():
                    error_message = 'O pagamento rapido nao foi registrado. Revise descricao, valor e metodo.'
                    if expects_json:
                        return _student_financial_json_error(message=error_message, status=400)
                    messages.error(request, error_message)
                    return redirect(_append_fragment(reverse('student-quick-update', args=[student.id]), STUDENT_FINANCIAL_FRAGMENT))

                run_quick_sale_create(
                    actor=request.user,
                    student=student,
                    payload=form.cleaned_data,
                )
                success_message = 'Pagamento rapido registrado com sucesso.'
            else:
                quick_sale = get_object_or_404(
                    QuickSale,
                    pk=action_form.cleaned_data['quick_sale_id'],
                    student=student,
                )
                if action == 'cancel-quick-sale':
                    run_quick_sale_cancel(actor=request.user, student=student, quick_sale=quick_sale, payload={})
                    success_message = 'Pagamento rapido cancelado com sucesso.'
                else:
                    run_quick_sale_refund(actor=request.user, student=student, quick_sale=quick_sale, payload={})
                    success_message = 'Pagamento rapido estornado com sucesso.'
        except ValueError as exc:
            if expects_json:
                return _student_financial_json_error(message=str(exc), status=400)
            messages.error(request, str(exc))
            return redirect(_append_fragment(reverse('student-quick-update', args=[student.id]), STUDENT_FINANCIAL_FRAGMENT))

        if expects_json:
            return _student_financial_json_response(
                request=request,
                student=student,
                message=success_message,
            )

        messages.success(request, success_message)
        return redirect(_append_fragment(reverse('student-quick-update', args=[student.id]), STUDENT_FINANCIAL_FRAGMENT))


class StudentDirectoryExportView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = (ROLE_OWNER, ROLE_DEV, ROLE_MANAGER)

    def get(self, request, report_format, *args, **kwargs):
        allowed, count = check_export_quota(user_id=request.user.id, scope=f'student-directory-{report_format}')
        if not allowed:
            messages.warning(request, 'Cota de exportacao semanal atingida para este relatorio. O OctoBox limita exportacoes pesadas a 2 registros por semana para manter a performance do motor.')
            return redirect('student-directory')

        students = build_student_directory_snapshot(request.GET, for_export=True)['students']
        try:
            return run_report_response_build(build_student_directory_report(students=students, report_format=report_format))
        except ValueError as exc:
            raise Http404(str(exc)) from exc


class StudentEnrollmentActionView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = (ROLE_OWNER, ROLE_MANAGER)

    @idempotent_action
    def post(self, request, student_id, *args, **kwargs):
        student = get_object_or_404(Student, pk=student_id)
        return handle_student_enrollment_action_request(request=request, student=student)


class StudentLockHeartbeatView(LoginRequiredMixin, View):
    """
    Heartbeat do lock de edicao.

    Chamado pelo JS a cada 5s enquanto o usuario esta com a ficha aberta.
    Renova o TTL do lock para evitar expiracao por inatividade.
    Retorna JSON com status do lock atual.
    """

    def post(self, request, student_id, *args, **kwargs):
        student = get_object_or_404(Student, pk=student_id)
        role = get_user_role(request.user)
        role_slug = getattr(role, 'slug', None)
        return handle_student_lock_heartbeat(student_id=student.id, user=request.user, role_slug=role_slug)


class StudentLockStatusView(LoginRequiredMixin, View):
    """
    Consulta de status do lock para polling do frontend.

    GET: retorna se este usuario ainda detem o lock.
    Nao renova o TTL; apenas informa o estado atual.
    """

    def get(self, request, student_id, *args, **kwargs):
        student = get_object_or_404(Student, pk=student_id)
        return build_student_lock_status_response(student_id=student.id, user_id=request.user.id)


class StudentBulkActionView(LoginRequiredMixin, RoleRequiredMixin, View):
    """
    Executa acoes em massa (bulk) na listagem de alunos.
    Suporta partial-commit: falhas pontuais geram relatorio em vez de quebrar todo o loto.
    """
    allowed_roles = (ROLE_OWNER, ROLE_MANAGER)

    @idempotent_action
    def post(self, request, *args, **kwargs):
        action = request.POST.get('bulk_action')
        student_ids = request.POST.getlist('selected_students')

        if not action or not student_ids:
            messages.warning(request, "Nenhuma acao ou aluno selecionado.")
            return redirect('student-directory')

        students = Student.objects.filter(id__in=student_ids)

        if not students.exists():
            messages.warning(request, "Os alunos selecionados nao foram encontrados.")
            return redirect('student-directory')

        from shared_support.bulk_executor import execute_bulk_action

        # Definicao dinamica da acao baseada no form submetido
        def apply_action(student: Student):
            from students.models import StudentStatus
            
            # TODO: validar permissoes e regras de negocio
            if action == 'mark_inactive':
                if student.status == StudentStatus.INACTIVE:
                    raise Exception(f"{student.full_name} ja esta inativo.")
                student.status = StudentStatus.INACTIVE
                student.save(update_fields=['status', 'updated_at'])
            
            elif action == 'mark_active':
                if student.status == StudentStatus.ACTIVE:
                    raise Exception(f"{student.full_name} ja esta ativo.")
                student.status = StudentStatus.ACTIVE
                student.save(update_fields=['status', 'updated_at'])
            else:
                raise ValueError("Acao de lote desconhecida ou nao implementada.")

        # Executa as transacoes de forma independente (partial commit)
        results = execute_bulk_action(students, apply_action)

        sucessos = len(results['success'])
        falhas = len(results['failed'])

        if sucessos > 0:
            messages.success(request, f"{sucessos} aluno(s) processado(s) com sucesso na acao: {action}.")
            
        if falhas > 0:
            error_msgs = []
            for fail in results['failed']:
                # max 3 errors no toast
                if len(error_msgs) < 3:
                     # limit error message length
                     error_msgs.append(f"[{fail['item'].full_name}: {str(fail['error'])[:50]}]")
            
            error_details = ' '.join(error_msgs)
            if falhas > 3:
                error_details += f" ... e mais {falhas - 3} itens."
                
            messages.error(request, f"{falhas} falha(s) ignoradas: {error_details}")

        return redirect('student-directory')


class StudentSourceCaptureView(View):
    template_name = 'catalog/student-source-capture.html'

    def _resolve_student(self, token: str):
        student_id = run_student_source_capture_token_read(token=token)
        return get_object_or_404(Student, pk=student_id)

    def get(self, request, *args, **kwargs):
        token = (request.GET.get('token') or '').strip()
        if not token:
            raise Http404('Link de qualificacao invalido.')
        try:
            student = self._resolve_student(token)
        except (BadSignature, SignatureExpired, ValueError):
            raise Http404('Link de qualificacao invalido.')

        form = StudentSourceDeclarationCaptureForm(initial={'token': token})
        return render(request, self.template_name, {'form': form, 'student': student, 'submitted': False})

    def post(self, request, *args, **kwargs):
        form = StudentSourceDeclarationCaptureForm(request.POST)
        if not form.is_valid():
            token = (request.POST.get('token') or '').strip()
            if not token:
                raise Http404('Link de qualificacao invalido.')
            try:
                student = self._resolve_student(token)
            except (BadSignature, SignatureExpired, ValueError):
                raise Http404('Link de qualificacao invalido.')
            return render(request, self.template_name, {'form': form, 'student': student, 'submitted': False}, status=400)

        token = form.cleaned_data['token']
        try:
            student = self._resolve_student(token)
        except (BadSignature, SignatureExpired, ValueError):
            raise Http404('Link de qualificacao invalido.')

        run_student_source_declaration_record(
            student_id=student.id,
            declared_acquisition_source=form.cleaned_data['declared_acquisition_source'],
            declared_source_detail=form.cleaned_data.get('declared_source_detail') or '',
            declared_source_channel='secure_link',
            declared_source_response_id=f'secure-link:{timezone.now().isoformat()}',
            raw_payload={'captured_via': 'secure_link'},
        )
        student.refresh_from_db()
        fresh_form = StudentSourceDeclarationCaptureForm(initial={'token': token})
        return render(request, self.template_name, {'form': fresh_form, 'student': student, 'submitted': True})


class StudentImportView(LoginRequiredMixin, RoleRequiredMixin, View):
    """
    Recebe upload de CSV de alunos, persiste em arquivo temporario, dispara
    StudentImporter em background com job_id e redireciona para a tela de progresso.
    """
    allowed_roles = (ROLE_OWNER, ROLE_MANAGER)

    def post(self, request, *args, **kwargs):
        import os
        import tempfile
        from pathlib import Path

        from django.conf import settings

        from operations.services.student_importer import StudentImporter
        from shared_support.background_jobs import create_job, submit_background_job

        csv_file = request.FILES.get('import_file')
        if not csv_file:
            messages.error(request, 'Nenhum arquivo CSV enviado.')
            return redirect('student-directory')

        raw_bytes = csv_file.read()
        try:
            text = raw_bytes.decode('utf-8-sig')
        except UnicodeDecodeError:
            messages.error(request, 'Arquivo CSV invalido: codificacao precisa ser UTF-8.')
            return redirect('student-directory')

        non_empty_data_lines = [line for line in text.splitlines()[1:] if line.strip()]
        total = len(non_empty_data_lines)

        if total <= 0:
            messages.warning(request, 'O arquivo parece vazio ou tem apenas cabecalho.')
            return redirect('student-directory')

        upload_dir = Path(settings.BASE_DIR) / 'tmp' / 'student_imports'
        upload_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode='wb',
            delete=False,
            dir=str(upload_dir),
            suffix='.csv',
        ) as temp_handle:
            temp_handle.write(raw_bytes)
            temp_path = temp_handle.name

        job_id = create_job(
            'import_students',
            total_items=total,
            metadata={'filename': csv_file.name},
        )

        def _run(job_id_arg, file_path):
            try:
                StudentImporter().import_from_file(file_path, job_id=job_id_arg)
            finally:
                try:
                    os.unlink(file_path)
                except OSError:
                    pass

        submit_background_job(_run, job_id, temp_path)

        return redirect('student-import-progress', job_id=job_id)


class StudentImportProgressView(LoginRequiredMixin, RoleRequiredMixin, View):
    """
    Tela de acompanhamento de operacoes pesadas como Importacao.
    Possui GET para a view visual e GET ?json=1 para o polling.
    """
    allowed_roles = (ROLE_OWNER, ROLE_MANAGER)

    def get(self, request, job_id, *args, **kwargs):
        from shared_support.background_jobs import get_job_status
        job_data = get_job_status(job_id)
        
        if not job_data:
            if request.GET.get('json'):
                return JsonResponse({'status': 'not_found'}, status=404)
            messages.error(request, 'Processo não encontrado ou já expirou.')
            return redirect('student-directory')

        if request.GET.get('json'):
            return JsonResponse({'job': job_data})
            
        # Retorna a UX visual do job (polling de tela)
        # O Base Context (shell lateral, menu, current role, current widget)
        # seria anexado via attach_catalog_page_payload como views nativas.
        context = {
            'job': job_data,
        }
        
        if hasattr(self, 'get_base_context'):
            context.update(self.get_base_context())

        return render(request, 'catalog/import-progress.html', context)


