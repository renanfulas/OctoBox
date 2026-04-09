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

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.signing import BadSignature, SignatureExpired
from django.db import IntegrityError
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import FormView

from shared_support.decorators import idempotent_action
from shared_support.editing_locks import (
    acquire_student_lock,
    get_student_lock_status,
    refresh_student_lock,
    release_student_lock,
)
from shared_support.student_event_stream import build_student_event_stream, publish_student_stream_event
from shared_support.student_snapshot_versions import build_profile_version, build_student_snapshot_version

from access.permissions import AjaxLoginRequiredMixin, RoleRequiredMixin
from access.roles import ROLE_DEV, ROLE_MANAGER, ROLE_OWNER, ROLE_RECEPTION, get_user_role
from catalog.forms import (
    EnrollmentManagementForm,
    PaymentManagementForm,
    StudentPaymentActionForm,
    StudentQuickForm,
    StudentExpressForm,
    StudentSourceDeclarationCaptureForm,
)
from catalog.presentation import build_student_directory_page, build_student_form_page
from catalog.presentation.student_financial_fragments import render_student_financial_fragments
from catalog.presentation.shared import attach_catalog_page_payload
from catalog.services.student_enrollment_actions import handle_student_enrollment_action
from catalog.services.student_payment_actions import handle_student_payment_action
from catalog.services.student_workflows import run_student_quick_create_workflow, run_student_quick_update_workflow, run_student_express_create_workflow
from catalog.student_queries import build_student_directory_snapshot, build_student_financial_snapshot, get_operational_enrollment
from shared_support.redis_snapshots import prewarm_student_snapshots
from finance.models import Enrollment, Payment
from monitoring.student_realtime_metrics import record_student_save_conflict
from onboarding.attribution import extract_acquisition_channel
from onboarding.models import StudentIntake
from reporting.application.catalog_reports import build_student_directory_report
from reporting.infrastructure import build_report_response
from shared_support.security import check_export_quota
from students.facade import run_student_source_declaration_record
from students.infrastructure.source_capture_links import build_student_source_capture_token, read_student_source_capture_token
from students.models import Student

from .catalog_base_views import CatalogBaseView


STUDENT_FORM_ESSENTIAL_FRAGMENT = 'student-form-essential'
STUDENT_FINANCIAL_FRAGMENT = 'student-financial-overview'
STUDENT_DIRECTORY_FRAGMENT = 'student-directory-board'
STUDENT_DIRECTORY_PAGE_SIZE = 15


def _append_fragment(url, fragment):
    if not fragment:
        return url
    return f'{url}#{fragment}'


def _expects_json_response(request):
    return request.headers.get('X-Requested-With') == 'XMLHttpRequest'


def _student_financial_json_response(*, request, student, message, selected_payment=None, status=200):
    return JsonResponse(
        {
            'status': 'success',
            'message': message,
            'selected_payment_id': getattr(selected_payment, 'id', None),
            'fragments': render_student_financial_fragments(
                student,
                request=request,
                selected_payment=selected_payment,
            ),
        },
        status=status,
    )


def _student_financial_json_error(*, message, status=400):
    return JsonResponse(
        {
            'status': 'error',
            'message': message,
        },
        status=status,
    )


def _build_student_source_capture_url(*, request, student):
    token = build_student_source_capture_token(student_id=student.id)
    return f"{request.build_absolute_uri(reverse('student-source-capture'))}?token={token}"


def _serialize_student_browser_snapshot(*, request, student):
    """
    Serializa uma leitura canonica e enxuta da ficha do aluno para warm-up do navegador.

    Mantemos o backend como fonte oficial, mas entregamos um payload pequeno o bastante
    para o browser guardar e reaproveitar sem custo excessivo.
    """

    financial_overview = build_student_financial_snapshot(student)
    latest_enrollment = financial_overview.get('latest_enrollment')
    latest_payment = next(iter(financial_overview.get('payments') or []), None)
    current_lock = get_student_lock_status(student.id)
    snapshot_version = build_student_snapshot_version(
        student=student,
        latest_enrollment=latest_enrollment,
        latest_payment=latest_payment,
    )
    profile_version = build_profile_version(student)

    if not current_lock:
        lock_payload = {'status': 'free'}
    elif current_lock.get('user_id') == request.user.id:
        lock_payload = {'status': 'owner'}
    else:
        lock_payload = {
            'status': 'blocked',
            'holder': {
                'user_display': current_lock.get('user_display', ''),
                'role_label': current_lock.get('role_label', ''),
            },
        }

    return {
        'id': student.id,
        'full_name': student.full_name,
        'email': student.email or '',
        'phone': student.phone or '',
        'status': student.status,
        'financial': {
            'latest_plan_name': latest_enrollment.plan.name if latest_enrollment and getattr(latest_enrollment, 'plan', None) else '',
            'latest_payment_status': getattr(latest_payment, 'status', '') or '',
            'latest_payment_due_date': latest_payment.due_date.isoformat() if getattr(latest_payment, 'due_date', None) else '',
            'overdue_count': financial_overview.get('metrics', {}).get('pagamentos_atrasados', 0),
            'pending_count': financial_overview.get('metrics', {}).get('pagamentos_pendentes', 0),
        },
        'presence': {
            'percent_30d': financial_overview.get('metrics', {}).get('presenca_percentual_30d', 0) or 0,
        },
        'snapshot_version': snapshot_version,
        'profile_version': profile_version,
        'lock': lock_payload,
        'links': {
            'edit': _append_fragment(reverse('student-quick-update', args=[student.id]), STUDENT_FINANCIAL_FRAGMENT),
            'source_capture': _build_student_source_capture_url(request=request, student=student),
        },
        'generated_at': timezone.now().isoformat(),
        'source': 'backend-snapshot',
    }


def _serialize_student_directory_search_entry(student):
    latest_payment_due_date = getattr(student, 'latest_payment_due_date', None)
    due_label = latest_payment_due_date.strftime('%d/%m/%Y') if latest_payment_due_date else ''

    return {
        'id': student.id,
        'full_name': student.full_name,
        'email': student.email or '',
        'phone': student.phone or '',
        'status': student.status,
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


def _build_student_drawer_fragments(*, request, student, form=None):
    role = get_user_role(request.user)
    role_slug = getattr(role, 'slug', ROLE_RECEPTION)
    financial_overview = build_student_financial_snapshot(student)
    page = build_student_form_page(
        form=form or StudentQuickForm(instance=student),
        student_object=student,
        selected_intake=None,
        financial_overview=financial_overview,
        page_mode='update',
        current_role_slug=role_slug,
        browser_snapshot=_serialize_student_browser_snapshot(request=request, student=student),
    )
    page['context']['surface_mode'] = 'drawer'
    page['data']['source_snapshot']['capture_url'] = _build_student_source_capture_url(request=request, student=student)
    context = {'page': page}

    return {
        'profile': render_to_string('includes/catalog/student_page/student_page_profile_panel.html', context=context, request=request),
        'financial': render_to_string('catalog/includes/student/student_quick_panel_financial.html', context=context, request=request),
    }


class StudentDirectoryView(CatalogBaseView):
    template_name = 'catalog/students.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        base_context = self.get_base_context()
        context.update(base_context)
        snapshot = build_student_directory_snapshot(self.request.GET)
        index_params = self.request.GET.copy()
        if 'query' in index_params:
            del index_params['query']
        if 'page' in index_params:
            del index_params['page']
        students = snapshot['students']
        student_count = snapshot['total_students']
        current_role_slug = base_context['current_role'].slug
        context['students'] = students
        search_snapshot = snapshot if not self.request.GET.get('query') else build_student_directory_snapshot(index_params)
        directory_search_entries = [
            _serialize_student_directory_search_entry(student)
            for student in search_snapshot['students']
        ]

        from django.core.paginator import Paginator
        
        # 🚀 Performance AAA (Db-Bypass Pagination)
        # Ao injetar o `count` pré-calculado pelo aggregate, impedimos que o Django execute a 
        # assassina query SELECT COUNT(*) no banco de dados inteiramente.
        class PrecountedPaginator(Paginator):
            @property
            def count(self):
                return student_count
        
        # 🚀 Segurança de Elite (Fintech Hardening): Pagination Boundary
        # Previne DoS por memória caso o atacante envie page_size=1000000
        MAX_PAGE_SIZE = 100
        page_size_raw = self.request.GET.get('page_size', STUDENT_DIRECTORY_PAGE_SIZE)
        try:
            page_size = min(int(page_size_raw), MAX_PAGE_SIZE)
        except (ValueError, TypeError):
            page_size = STUDENT_DIRECTORY_PAGE_SIZE

        paginator = PrecountedPaginator(students, page_size)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        query_params = self.request.GET.copy()
        if 'page' in query_params:
            del query_params['page']
        base_query_string = query_params.urlencode()

        page_payload = build_student_directory_page(
            student_count=student_count,
            students=page_obj,
            student_filter_form=snapshot['filter_form'],
            snapshot=snapshot,
            current_role_slug=current_role_slug,
            base_query_string=base_query_string,
            directory_search={
                'cache_key': index_params.urlencode() or 'all',
                'refresh_token': timezone.now().isoformat(),
                'index': directory_search_entries,
            },
        )

        # 🚀 Performance AAA (Preloading Preditivo): Aquecimento de Cache
        # Carregamos os Snapshots Fantasma dos alunos desta página para cliques instantâneos.
        try:
            page_student_ids = [s.id for s in page_obj]
            prewarm_student_snapshots(page_student_ids)
        except Exception:
            pass

        return attach_catalog_page_payload(
            context,
            payload_key='student_directory_page',
            payload=page_payload,
            include_sections=('context', 'shell'),
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
        intake_id = self.request.GET.get('intake') if self.request.method == 'GET' else self.request.POST.get('intake_record')
        if not intake_id:
            return None
        return StudentIntake.objects.filter(pk=intake_id).first()

    def get_initial(self):
        initial = super().get_initial()
        selected_intake = self.get_selected_intake()
        if selected_intake and self.page_mode == 'create':
            intake_raw_payload = getattr(selected_intake, 'raw_payload', {}) or {}
            intake_channel = extract_acquisition_channel(
                raw_payload=intake_raw_payload,
                fallback_source=getattr(selected_intake, 'source', ''),
            )
            intake_detail = ((intake_raw_payload.get('attribution') or {}).get('acquisition') or {}).get('declared_detail', '')
            initial.update(
                {
                    'full_name': selected_intake.full_name,
                    'phone': selected_intake.phone,
                    'email': selected_intake.email,
                    'intake_record': selected_intake,
                    'acquisition_source': intake_channel,
                    'acquisition_source_detail': intake_detail,
                }
            )
        return initial

    def get_payment_management_form(self):
        if not self.object:
            return None
        from django.utils import timezone
        latest_payment = self.object.payments.order_by('-due_date', '-created_at').first()
        if latest_payment is None:
            # Estado "Nova Cobrança": sem payment vinculado
            return PaymentManagementForm(initial={
                'amount': '',
                'due_date': timezone.localdate().strftime('%d/%m/%Y'),
            })
        
        return PaymentManagementForm(
            instance=latest_payment,
            initial={
                'payment_id': latest_payment.id,
                'amount': latest_payment.amount,
                'due_date': latest_payment.due_date,
                'method': latest_payment.method,
                'reference': latest_payment.reference,
                'notes': latest_payment.notes,
            }
        )

    def get_enrollment_management_form(self):
        if not self.object:
            return None
        latest_enrollment = get_operational_enrollment(self.object)
        if latest_enrollment is None:
            return None
        return EnrollmentManagementForm(
            initial={
                'enrollment_id': latest_enrollment.id,
                'action_date': timezone.localdate(),
            }
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        base_context = self.get_base_context()
        context.update(base_context)
        selected_intake = self.get_selected_intake()
        financial_overview = build_student_financial_snapshot(self.object)
        role_slug = base_context['current_role'].slug
        financial_overview['payment_management_form'] = self.get_payment_management_form() if role_slug in (ROLE_OWNER, ROLE_MANAGER, ROLE_RECEPTION) else None
        financial_overview['enrollment_management_form'] = self.get_enrollment_management_form() if role_slug in (ROLE_OWNER, ROLE_MANAGER) else None
        page_payload = build_student_form_page(
            form=context.get('form'),
            student_object=self.object,
            selected_intake=selected_intake,
            financial_overview=financial_overview,
            page_mode=self.page_mode,
            current_role_slug=role_slug,
            browser_snapshot=_serialize_student_browser_snapshot(request=self.request, student=self.object) if self.object else None,
        )
        if self.object is not None:
            page_payload['data']['source_snapshot']['capture_url'] = _build_student_source_capture_url(request=self.request, student=self.object)
        return attach_catalog_page_payload(
            context,
            payload_key='student_form_page',
            payload=page_payload,
            include_sections=('context', 'shell'),
        )

    def form_invalid(self, form):
        messages.error(self.request, 'O cadastro travou em alguns pontos. O box destacou o passo certo para voce corrigir sem perder contexto.')
        return super().form_invalid(form)


class StudentQuickCreateView(StudentQuickBaseView):
    page_mode = 'create'

    def dispatch(self, request, *args, **kwargs):
        from shared_support.security.anti_cheat_throttles import StudentCreationSpamThrottle
        throttle = StudentCreationSpamThrottle()
        if not throttle.allow_request(request, self):
            throttle.on_throttle_exceeded(request, self)
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Limite de criação atingido. Tente novamente em 1 hora.")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        try:
            workflow = run_student_quick_create_workflow(
                actor=self.request.user,
                form=form,
                selected_intake=self.get_selected_intake(),
            )
        except IntegrityError as exc:
            if 'phone_lookup_index' not in str(exc):
                raise
            form.add_error('phone', 'Ja existe um aluno cadastrado com este WhatsApp.')
            return self.form_invalid(form)
        self.object = workflow['student']
        messages.success(self.request, f'Aluno {self.object.full_name} cadastrado com sucesso.')
        return super().form_valid(form)


class StudentExpressCreateView(CatalogBaseView, FormView):
    allowed_roles = (ROLE_OWNER, ROLE_MANAGER, ROLE_RECEPTION)
    form_class = StudentExpressForm
    template_name = 'catalog/student-express-form.html'

    def dispatch(self, request, *args, **kwargs):
        from shared_support.security.anti_cheat_throttles import StudentCreationSpamThrottle
        throttle = StudentCreationSpamThrottle()
        if not throttle.allow_request(request, self):
            throttle.on_throttle_exceeded(request, self)
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Limite de criação atingido. Tente novamente em 1 hora.")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        workflow = run_student_express_create_workflow(
            actor=self.request.user,
            form=form,
        )
        student = workflow['student']
        messages.success(self.request, f'Cadastro Expresso: {student.full_name} pronto para vinculação financeira!')
        return redirect(_append_fragment(reverse('student-quick-update', args=[student.id]), STUDENT_FINANCIAL_FRAGMENT))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        base_context = self.get_base_context()
        context.update(base_context)
        
        page_payload = {
            'data': {
                'hero': {
                    'title': 'Checkout Rápido (Balcão)',
                    'subtitle': 'Nome e Zap para fechar a venda agora.',
                    'icon': 'zap',
                    'back_url': reverse('student-directory')
                }
            }
        }
        return attach_catalog_page_payload(
            context,
            payload_key='student_express_page',
            payload=page_payload,
            include_sections=('context', 'shell'),
        )


class StudentQuickUpdateView(StudentQuickBaseView):
    page_mode = 'update'
    _lock_holder = None  # Detentor do lock quando este usuario nao consegue adquirir

    def dispatch(self, request, *args, **kwargs):
        # 🚀 Segurança de Elite (Fintech Hardening): Tenant Isolation
        # TODO: Quando o sistema for Multi-Box pleno, filtrar por workspace.
        self.object = get_object_or_404(Student, pk=kwargs['student_id'])

        # --- Lock de edicao com hierarquia de papeis ---
        # A ficha abre em leitura. O lock so e pedido quando a pessoa entra em edicao.
        role = get_user_role(request.user)
        role_slug = getattr(role, 'slug', None)

        if role_slug and role_slug != ROLE_DEV:
            current_lock = get_student_lock_status(self.object.id)
            if current_lock and current_lock.get('user_id') != request.user.id:
                self._lock_holder = current_lock

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Injeta informacao do lock no contexto para o template renderizar o banner.
        if self._lock_holder:
            context['student_lock_holder'] = self._lock_holder
            context['student_lock_is_blocked'] = True
        else:
            context['student_lock_is_blocked'] = False
        context['student_id_for_lock'] = self.object.id
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = self.object
        return kwargs

    def form_valid(self, form):
        # Revalida o lock antes de persistir. Salvar sem lock valido nao e permitido.
        role = get_user_role(self.request.user)
        role_slug = getattr(role, 'slug', None)
        request_profile_version = self.request.POST.get('profile_version', '')

        if role_slug and role_slug != ROLE_DEV:
            current_lock = get_student_lock_status(self.object.id)
            if not current_lock or current_lock.get('user_id') != self.request.user.id:
                if not current_lock:
                    messages.error(
                        self.request,
                        'A edicao desta ficha nao esta reservada para voce agora. Entre em modo de edicao novamente antes de salvar.'
                    )
                    return redirect(_append_fragment(reverse('student-quick-update', args=[self.object.id]), STUDENT_FORM_ESSENTIAL_FRAGMENT))
                holder = current_lock
                messages.error(
                    self.request,
                    f"{holder.get('user_display', 'Outro usuário')} ({holder.get('role_label', '')}) "
                    f"assumiu a edição deste aluno enquanto você preenchia. "
                    f"Suas alterações não foram salvas. Fale com ele para coordenar."
                )
                return redirect(_append_fragment(reverse('student-quick-update', args=[self.object.id]), STUDENT_FORM_ESSENTIAL_FRAGMENT))

        current_profile_version = build_profile_version(self.object)
        if request_profile_version and current_profile_version and request_profile_version != current_profile_version:
            record_student_save_conflict('student-form')
            messages.error(
                self.request,
                'A ficha mudou antes do seu salvar. Reabrimos a leitura oficial para evitar sobrescrever informacao mais nova.'
            )
            return redirect(_append_fragment(reverse('student-quick-update', args=[self.object.id]), STUDENT_FORM_ESSENTIAL_FRAGMENT))

        changed_fields = list(form.changed_data)
        workflow = run_student_quick_update_workflow(
            actor=self.request.user,
            form=form,
            changed_fields=changed_fields,
            selected_intake=self.get_selected_intake(),
        )
        self.object = workflow['student']

        # Libera o lock apos salvar com sucesso.
        if role_slug and role_slug != ROLE_DEV:
            release_student_lock(self.object.id, self.request.user.id)
            publish_student_stream_event(
                student_id=self.object.id,
                event_type='student.lock.released',
                meta={
                    'holder': {
                        'user_display': self.request.user.get_full_name() or self.request.user.username,
                    },
                    'reason': 'student_form_saved',
                },
            )

        messages.success(self.request, f'Cadastro de {self.object.full_name} atualizado com sucesso.')
        return redirect(self.get_success_url())


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
            {
                'status': 'ok',
                'snapshot': _serialize_student_browser_snapshot(request=request, student=student),
            }
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
            {
                'status': 'ok',
                'snapshot': _serialize_student_browser_snapshot(request=request, student=student),
                'fragments': _build_student_drawer_fragments(request=request, student=student),
            }
        )


class StudentDrawerProfileSaveView(LoginRequiredMixin, RoleRequiredMixin, View):
    """
    Salva o perfil do aluno diretamente do drawer do diretorio.

    A regra de lock continua autoritativa no backend; o drawer apenas oferece
    uma casca mais rápida para edição curta.
    """

    allowed_roles = (ROLE_OWNER, ROLE_MANAGER, ROLE_RECEPTION, ROLE_DEV)

    def post(self, request, student_id, *args, **kwargs):
        student = get_object_or_404(Student, pk=student_id)
        role = get_user_role(request.user)
        role_slug = getattr(role, 'slug', None)
        form = StudentQuickForm(request.POST, instance=student)
        request_profile_version = request.POST.get('profile_version', '')

        if role_slug and role_slug != ROLE_DEV:
            current_lock = get_student_lock_status(student.id)
            if not current_lock or current_lock.get('user_id') != request.user.id:
                fragments = _build_student_drawer_fragments(request=request, student=student, form=form)
                holder = current_lock or {}
                return JsonResponse(
                    {
                        'status': 'error',
                        'message': (
                            f"{holder.get('user_display', 'Outro usuário')} ({holder.get('role_label', '')}) está com a edição desta ficha."
                            if current_lock else
                            'Entre em modo de edição novamente antes de salvar.'
                        ),
                        'snapshot': _serialize_student_browser_snapshot(request=request, student=student),
                        'fragments': fragments,
                    },
                    status=409,
                )

        current_profile_version = build_profile_version(student)
        if request_profile_version and current_profile_version and request_profile_version != current_profile_version:
            record_student_save_conflict('drawer-profile')
            return JsonResponse(
                {
                    'status': 'conflict',
                    'message': 'A ficha mudou antes do seu salvar. Atualizamos a leitura oficial para evitar conflito.',
                    'snapshot': _serialize_student_browser_snapshot(request=request, student=student),
                    'fragments': _build_student_drawer_fragments(request=request, student=student, form=form),
                },
                status=409,
            )

        if not form.is_valid():
            return JsonResponse(
                {
                    'status': 'error',
                    'message': 'Revise os campos destacados antes de salvar.',
                    'snapshot': _serialize_student_browser_snapshot(request=request, student=student),
                    'fragments': _build_student_drawer_fragments(request=request, student=student, form=form),
                },
                status=400,
            )

        workflow = run_student_quick_update_workflow(
            actor=request.user,
            form=form,
            changed_fields=list(form.changed_data),
            selected_intake=None,
        )
        student = workflow['student']

        if role_slug and role_slug != ROLE_DEV:
            release_student_lock(student.id, request.user.id)
            publish_student_stream_event(
                student_id=student.id,
                event_type='student.lock.released',
                meta={
                    'holder': {
                        'user_display': request.user.get_full_name() or request.user.username,
                    },
                    'reason': 'profile_saved',
                },
            )

        return JsonResponse(
            {
                'status': 'success',
                'message': f'Perfil de {student.full_name} atualizado com sucesso.',
                'snapshot': _serialize_student_browser_snapshot(request=request, student=student),
                'fragments': _build_student_drawer_fragments(request=request, student=student),
            }
        )


class StudentPaymentActionView(AjaxLoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = (ROLE_OWNER, ROLE_MANAGER, ROLE_RECEPTION)

    @idempotent_action
    def post(self, request, student_id, *args, **kwargs):
        student = get_object_or_404(Student, pk=student_id)
        expects_json = _expects_json_response(request)
        action_form = StudentPaymentActionForm(request.POST)
        if not action_form.is_valid():
            error_message = 'A acao financeira enviada para o aluno nao e valida neste fluxo.'
            if expects_json:
                return _student_financial_json_error(message=error_message, status=400)
            messages.error(request, error_message)
            return redirect(_append_fragment(reverse('student-quick-update', args=[student.id]), STUDENT_FINANCIAL_FRAGMENT))

        action = action_form.cleaned_data['action']
        
        # --- FLUXO 1: CRIACAO AVULSA (1-Clique Balcao) ---
        if action == 'create-payment':
            # Nao tentar dar lock em payment existente
            from catalog.services.student_payment_actions import handle_student_payment_creation
            new_payment = handle_student_payment_creation(
                actor=request.user,
                student=student,
                payload=request.POST
            )
            if new_payment:
                success_message = 'Cobranca avulsa criada e recebimento confirmado via Balcao.'
                if expects_json:
                    return _student_financial_json_response(
                        request=request,
                        student=student,
                        message=success_message,
                        selected_payment=new_payment,
                    )
                messages.success(request, success_message)
            else:
                error_message = 'Erro ao criar cobranca avulsa.'
                if expects_json:
                    return _student_financial_json_error(message=error_message, status=400)
                messages.error(request, error_message)
            return redirect(_append_fragment(reverse('student-quick-update', args=[student.id]), STUDENT_FINANCIAL_FRAGMENT))

        # --- FLUXO 2: ATUALIZACAO/RECEBIMENTO DE EXISTENTE ---
        # 🚀 Segurança de Elite (Fintech Hardening): Pessimistic Locking com Fail-Fast
        # nowait=True evita que o servidor trave se a linha já estiver bloqueada (ataque de DoS)
        from django.db import transaction, DatabaseError
        try:
            with transaction.atomic():
                payment = get_object_or_404(
                    Payment.objects.select_for_update(nowait=True), 
                    pk=action_form.cleaned_data['payment_id'], 
                    student=student
                )
        except DatabaseError:
            error_message = 'Esta operacao financeira esta sendo processada em outra aba ou por outro administrador. Tente novamente em 15 segundos.'
            if expects_json:
                return _student_financial_json_error(message=error_message, status=409)
            messages.error(request, error_message)
            return redirect(_append_fragment(reverse('student-quick-update', args=[student.id]), STUDENT_FINANCIAL_FRAGMENT))

        restricted_actions = {'refund-payment', 'cancel-payment', 'regenerate-payment'}
        if action in restricted_actions and getattr(get_user_role(request.user), 'slug', '') == ROLE_RECEPTION:
            error_message = 'A Recepcao so pode salvar cobranca ou confirmar pagamento neste fluxo.'
            if expects_json:
                return _student_financial_json_error(message=error_message, status=403)
            messages.error(request, error_message)
            return redirect(_append_fragment(reverse('student-quick-update', args=[student.id]), STUDENT_FINANCIAL_FRAGMENT))

        if action == 'update-payment':
            form = PaymentManagementForm(request.POST)
            if not form.is_valid():
                error_message = 'A cobranca nao foi atualizada. Revise valor, vencimento e campos enviados.'
                if expects_json:
                    return _student_financial_json_error(message=error_message, status=400)
                messages.error(request, error_message)
                return redirect(_append_fragment(reverse('student-quick-update', args=[student.id]), STUDENT_FINANCIAL_FRAGMENT))

            updated_payment = handle_student_payment_action(
                actor=request.user,
                student=student,
                payment=payment,
                action=action,
                payload=form.cleaned_data,
            )
            if updated_payment is not None:
                payment = updated_payment
            success_message = 'Cobranca atualizada com sucesso.'
        else:
            updated_payment = handle_student_payment_action(
                actor=request.user,
                student=student,
                payment=payment,
                action=action,
            )
            if updated_payment is not None:
                payment = updated_payment
            action_success_messages = {
                'mark-paid': 'Pagamento registrado com sucesso.',
                'refund-payment': 'Estorno registrado com sucesso.',
                'cancel-payment': 'Cobranca cancelada com sucesso.',
                'regenerate-payment': 'Cobranca regenerada com sucesso.',
            }
            success_message = action_success_messages.get(action, 'Acao financeira concluida com sucesso.')

        if expects_json:
            return _student_financial_json_response(
                request=request,
                student=student,
                message=success_message,
                selected_payment=payment,
            )

        messages.success(request, success_message)
        return redirect(_append_fragment(reverse('student-quick-update', args=[student.id]), STUDENT_FINANCIAL_FRAGMENT))


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


class StudentDirectoryExportView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = (ROLE_OWNER, ROLE_DEV, ROLE_MANAGER)

    def get(self, request, report_format, *args, **kwargs):
        allowed, count = check_export_quota(user_id=request.user.id, scope=f'student-directory-{report_format}')
        if not allowed:
            messages.warning(request, 'Cota de exportacao semanal atingida para este relatorio. O OctoBox limita exportacoes pesadas a 2 registros por semana para manter a performance do motor.')
            return redirect('student-directory')

        students = build_student_directory_snapshot(request.GET, for_export=True)['students']
        try:
            return build_report_response(build_student_directory_report(students=students, report_format=report_format))
        except ValueError as exc:
            raise Http404(str(exc)) from exc


class StudentEnrollmentActionView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = (ROLE_OWNER, ROLE_MANAGER)

    @idempotent_action
    def post(self, request, student_id, *args, **kwargs):
        student = get_object_or_404(Student, pk=student_id)
        form = EnrollmentManagementForm(request.POST)
        if not form.is_valid():
            messages.error(request, 'A acao de matricula nao foi aplicada. Revise os campos enviados.')
            return redirect(_append_fragment(reverse('student-quick-update', args=[student.id]), STUDENT_FINANCIAL_FRAGMENT))

        from django.db import transaction, DatabaseError
        try:
            with transaction.atomic():
                enrollment = get_object_or_404(
                    Enrollment.objects.select_for_update(nowait=True), 
                    pk=form.cleaned_data['enrollment_id'], 
                    student=student
                )
        except DatabaseError:
            messages.error(request, 'Esta matricula está bloqueada para alteracao no momento (outra operacao em curso).')
            return redirect(_append_fragment(reverse('student-quick-update', args=[student.id]), STUDENT_FINANCIAL_FRAGMENT))
        if form.cleaned_data['action'] == 'cancel-enrollment' and enrollment.status != 'active':
            messages.error(request, 'Esta matricula já se encontra inativa ou cancelada.')
            return redirect(_append_fragment(reverse('student-quick-update', args=[student.id]), STUDENT_FINANCIAL_FRAGMENT))
        updated_enrollment = handle_student_enrollment_action(
            actor=request.user,
            student=student,
            enrollment=enrollment,
            action=form.cleaned_data['action'],
            action_date=form.cleaned_data['action_date'],
            reason=form.cleaned_data['reason'],
        )

        return redirect(_append_fragment(reverse('student-quick-update', args=[student.id]), STUDENT_FINANCIAL_FRAGMENT))


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

        if not role_slug or role_slug == 'Dev':
            return JsonResponse({'status': 'dev_bypass'})

        refreshed = refresh_student_lock(student.id, request.user.id)

        if refreshed:
            return JsonResponse({'status': 'active', 'holder': 'self'})

        # Lock pode ter expirado ou sido tomado por outro usuario
        current = get_student_lock_status(student.id)
        if current:
            return JsonResponse({
                'status': 'stolen',
                'holder': {
                    'user_display': current.get('user_display', ''),
                    'role_label': current.get('role_label', ''),
                }
            })

        # Lock expirou: tenta readquirir
        lock_result = acquire_student_lock(student.id, request.user, role_slug)
        if lock_result.acquired:
            return JsonResponse({'status': 'reacquired'})

        holder = lock_result.holder or {}
        return JsonResponse({
            'status': 'blocked',
            'holder': {
                'user_display': holder.get('user_display', ''),
                'role_label': holder.get('role_label', ''),
            }
        })


class StudentLockStatusView(LoginRequiredMixin, View):
    """
    Consulta de status do lock para polling do frontend.

    GET: retorna se este usuario ainda detém o lock.
    Nao renova o TTL — apenas informa o estado atual.
    """

    def get(self, request, student_id, *args, **kwargs):
        student = get_object_or_404(Student, pk=student_id)
        current = get_student_lock_status(student.id)

        if not current:
            return JsonResponse({'status': 'free'})

        if current.get('user_id') == request.user.id:
            return JsonResponse({'status': 'owner'})

        return JsonResponse({
            'status': 'blocked',
            'holder': {
                'user_display': current.get('user_display', ''),
                'role_label': current.get('role_label', ''),
            }
        })


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
        student_id = read_student_source_capture_token(token=token)
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
    Inicia o job de importacao assincrona de alunos ou exibe a tela de form (se houvesse).
    """
    allowed_roles = (ROLE_OWNER, ROLE_MANAGER)

    def post(self, request, *args, **kwargs):
        from shared_support.background_jobs import create_job, submit_background_job
        # Normalmente leriamos o CSV de request.FILES, mas como e um prototipo/hub para 
        # provar o async e o partial commit, vamos mocar a logica do job.
        
        csv_file = request.FILES.get('import_file')
        if not csv_file:
            messages.error(request, 'Nenhum arquivo CSV enviado.')
            return redirect('student-directory')
            
        # Simula a leitura e determinacao do total de itens no CSV
        linhas = csv_file.read().decode('utf-8').splitlines()
        total = len(linhas) - 1 if len(linhas) > 1 else 0
        
        if total <= 0:
            messages.warning(request, 'O arquivo parece vazio ou não tem cabeçalho.')
            return redirect('student-directory')

        job_id = create_job('import_students', total_items=total, metadata={'filename': csv_file.name})
        
        # A funcao que vai rodar em background.
        def process_csv_chunk(job_id, linhas_dados):
            import time
            for i, linha in enumerate(linhas_dados):
                # time sleep para simular o processo DB pesado (100ms)
                time.sleep(0.1)
                
                # Simula falha proposital para testar a engine se a linha contiver 'erro'
                if 'erro' in linha.lower():
                    from shared_support.background_jobs import update_job_progress
                    update_job_progress(job_id, 1, failed_item={'line': i+2, 'error': f'Dados invalidos ou ja existentes: linha "{linha[:20]}..."'})
                else:
                    from shared_support.background_jobs import update_job_progress
                    update_job_progress(job_id, 1)

        submit_background_job(process_csv_chunk, job_id, linhas[1:])
        
        # Redireciona para a UI de progresso
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


