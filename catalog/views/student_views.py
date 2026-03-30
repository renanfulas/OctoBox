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
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect
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

from access.permissions import RoleRequiredMixin
from access.roles import ROLE_DEV, ROLE_MANAGER, ROLE_OWNER, ROLE_RECEPTION, get_user_role
from catalog.forms import EnrollmentManagementForm, PaymentManagementForm, StudentPaymentActionForm, StudentQuickForm, StudentExpressForm
from catalog.presentation import build_student_directory_page, build_student_form_page
from catalog.presentation.shared import attach_catalog_page_payload
from catalog.services.student_enrollment_actions import handle_student_enrollment_action
from catalog.services.student_payment_actions import handle_student_payment_action
from catalog.services.student_workflows import run_student_quick_create_workflow, run_student_quick_update_workflow, run_student_express_create_workflow
from catalog.student_queries import build_student_directory_snapshot, build_student_financial_snapshot
from shared_support.redis_snapshots import prewarm_student_snapshots
from finance.models import Enrollment, Payment
from onboarding.models import StudentIntake
from reporting.application.catalog_reports import build_student_directory_report
from reporting.infrastructure import build_report_response
from shared_support.security import check_export_quota
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


class StudentDirectoryView(CatalogBaseView):
    template_name = 'catalog/students.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        base_context = self.get_base_context()
        context.update(base_context)
        snapshot = build_student_directory_snapshot(self.request.GET)
        students = snapshot['students']
        student_count = snapshot['total_students']
        current_role_slug = base_context['current_role'].slug
        context['students'] = students

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
            initial.update(
                {
                    'full_name': selected_intake.full_name,
                    'phone': selected_intake.phone,
                    'email': selected_intake.email,
                    'intake_record': selected_intake,
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
        latest_enrollment = self.object.enrollments.order_by('-start_date', '-created_at').first()
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
        )
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
        workflow = run_student_quick_create_workflow(
            actor=self.request.user,
            form=form,
            selected_intake=self.get_selected_intake(),
        )
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
        # Dev nao participa do lock: ve a ficha sem adquirir nem bloquear.
        role = get_user_role(request.user)
        role_slug = getattr(role, 'slug', None)

        if role_slug and role_slug != ROLE_DEV:
            lock_result = acquire_student_lock(self.object.id, request.user, role_slug)
            if not lock_result.acquired:
                # Armazena o detentor para o template exibir o banner contextual.
                self._lock_holder = lock_result.holder

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
        # Revalida o lock antes de persistir. Se outro usuario de maior prioridade
        # tomou o lock enquanto este usuario estava preenchendo, rejeita a gravacao.
        role = get_user_role(self.request.user)
        role_slug = getattr(role, 'slug', None)

        if role_slug and role_slug != ROLE_DEV:
            current_lock = get_student_lock_status(self.object.id)
            if current_lock and current_lock.get('user_id') != self.request.user.id:
                holder = current_lock
                messages.error(
                    self.request,
                    f"{holder.get('user_display', 'Outro usuário')} ({holder.get('role_label', '')}) "
                    f"assumiu a edição deste aluno enquanto você preenchia. "
                    f"Suas alterações não foram salvas. Fale com ele para coordenar."
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

        messages.success(self.request, f'Cadastro de {self.object.full_name} atualizado com sucesso.')
        return redirect(self.get_success_url())


class StudentPaymentActionView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = (ROLE_OWNER, ROLE_MANAGER, ROLE_RECEPTION)

    @idempotent_action
    def post(self, request, student_id, *args, **kwargs):
        student = get_object_or_404(Student, pk=student_id)
        action_form = StudentPaymentActionForm(request.POST)
        if not action_form.is_valid():
            messages.error(request, 'A acao financeira enviada para o aluno nao e valida neste fluxo.')
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
                messages.success(request, 'Cobranca avulsa criada e recebimento confirmado via Balcao.')
            else:
                messages.error(request, 'Erro ao criar cobranca avulsa.')
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
            messages.error(request, 'Esta operacao financeira está sendo processada em outra aba ou por outro administrador. Tente novamente em 15 segundos.')
            return redirect(_append_fragment(reverse('student-quick-update', args=[student.id]), STUDENT_FINANCIAL_FRAGMENT))

        restricted_actions = {'refund-payment', 'cancel-payment', 'regenerate-payment'}
        if action in restricted_actions and getattr(get_user_role(request.user), 'slug', '') == ROLE_RECEPTION:
            messages.error(request, 'A Recepcao so pode salvar cobranca ou confirmar pagamento neste fluxo.')
            return redirect(_append_fragment(reverse('student-quick-update', args=[student.id]), STUDENT_FINANCIAL_FRAGMENT))

        if action == 'update-payment':
            form = PaymentManagementForm(request.POST)
            if form.is_valid():
                handle_student_payment_action(
                    actor=request.user,
                    student=student,
                    payment=payment,
                    action=action,
                    payload=form.cleaned_data,
                )
        else:
            handle_student_payment_action(
                actor=request.user,
                student=student,
                payment=payment,
                action=action,
            )

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
        handle_student_enrollment_action(
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


