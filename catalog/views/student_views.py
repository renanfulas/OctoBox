"""
ARQUIVO: views da area de alunos do catalogo.

POR QUE ELE EXISTE:
- publica a casca HTTP de diretorio, cadastro leve e acoes da ficha no app catalog.
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import FormView

from access.permissions import RoleRequiredMixin
from access.roles import ROLE_DEV, ROLE_MANAGER, ROLE_OWNER, ROLE_RECEPTION
from catalog.forms import EnrollmentManagementForm, PaymentManagementForm, StudentQuickForm
from catalog.services.student_enrollment_actions import handle_student_enrollment_action
from catalog.services.student_payment_actions import handle_student_payment_action
from catalog.services.student_workflows import run_student_quick_create_workflow, run_student_quick_update_workflow
from catalog.student_queries import build_student_directory_snapshot, build_student_financial_snapshot
from communications.models import StudentIntake
from finance.models import Enrollment, Payment
from reporting.application.catalog_reports import build_student_directory_report
from reporting.infrastructure import build_report_response
from students.models import Student

from .catalog_base_views import CatalogBaseView


class StudentDirectoryView(CatalogBaseView):
    template_name = 'catalog/students.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_base_context())
        snapshot = build_student_directory_snapshot(self.request.GET)
        students = snapshot['students']
        student_count = students.count()

        context['students'] = students[:24]
        context['student_filter_form'] = snapshot['filter_form']
        context['student_metrics'] = snapshot['metrics']
        context['student_funnel'] = snapshot['funnel']
        context['priority_students'] = snapshot['priority_students']
        context['intake_queue'] = snapshot['intake_queue']
        context['student_operational_focus'] = [
            {
                'label': 'Triagem imediata',
                'summary': f'{len(snapshot["priority_students"])} aluno(s) ou lead(s) já pedem leitura antes de esfriarem.',
                'pill_class': 'warning' if len(snapshot['priority_students']) > 0 else 'success',
                'href': '#student-priority-board',
                'href_label': 'Ver prioridades',
            },
            {
                'label': 'Conversão pronta',
                'summary': f'{len(snapshot["intake_queue"])} entrada(s) provisória(s) já podem virar aluno com pouco atrito.',
                'pill_class': 'info' if len(snapshot['intake_queue']) > 0 else 'accent',
                'href': '#student-intake-board',
                'href_label': 'Ver fila de entrada',
            },
            {
                'label': 'Base no recorte atual',
                'summary': f'{student_count} registro(s) sustentam a leitura desta tela e precisam ser escaneados sem fadiga.',
                'pill_class': 'accent',
                'href': '#student-directory-board',
                'href_label': 'Ver base principal',
            },
        ]
        context['student_focus'] = [
            'A recepcao usa esta tela para localizar rapido, converter lead e abrir ficha sem perder tempo no admin.',
            'A gerencia usa esta leitura para enxergar quem exige contato comercial, ajuste de plano ou acao financeira.',
            'O foco aqui e praticidade: triagem primeiro, detalhe depois.',
        ]
        current_role_slug = context['current_role'].slug
        context['student_export_links'] = {
            'csv': f"{reverse('student-directory-export', args=['csv'])}?{self.request.GET.urlencode()}",
            'pdf': f"{reverse('student-directory-export', args=['pdf'])}?{self.request.GET.urlencode()}",
        }
        context['can_manage_students'] = current_role_slug in (ROLE_OWNER, ROLE_MANAGER, ROLE_RECEPTION)
        context['can_export_students'] = current_role_slug in (ROLE_OWNER, ROLE_DEV, ROLE_MANAGER)
        context['can_open_student_admin'] = current_role_slug in (ROLE_OWNER, ROLE_MANAGER)
        return context


class StudentQuickBaseView(CatalogBaseView, FormView):
    allowed_roles = (ROLE_OWNER, ROLE_MANAGER, ROLE_RECEPTION)
    form_class = StudentQuickForm
    template_name = 'catalog/student-form.html'
    page_mode = 'create'
    object = None

    def get_success_url(self):
        return reverse('student-directory')

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
        latest_payment = self.object.payments.order_by('-due_date', '-created_at').first()
        if latest_payment is None:
            return None
        return PaymentManagementForm(
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
        context.update(self.get_base_context())
        selected_intake = self.get_selected_intake()
        financial_overview = build_student_financial_snapshot(self.object)
        latest_enrollment = financial_overview.get('latest_enrollment')
        recent_payments = financial_overview.get('payments', [])
        context['page_mode'] = self.page_mode
        context['page_title'] = 'Cadastrar aluno' if self.page_mode == 'create' else 'Editar aluno'
        context['page_subtitle'] = (
            'Comece pelo essencial e complete o resto só se já fizer sentido agora.'
            if self.page_mode == 'create'
            else 'Ajuste rapidamente o cadastro sem cair no admin bruto.'
        )
        context['form_focus'] = [
            'Nome completo e WhatsApp formam o núcleo do cadastro rápido.',
            'Os campos de perfil entram no segundo bloco com a mesma linguagem operacional do box.',
            'A ideia desta tela é reduzir fricção sem perder legibilidade.',
        ]
        context['student_object'] = self.object
        context['selected_intake'] = selected_intake
        context['financial_overview'] = financial_overview
        role_slug = context['current_role'].slug
        context['payment_management_form'] = self.get_payment_management_form() if role_slug in (ROLE_OWNER, ROLE_MANAGER, ROLE_RECEPTION) else None
        context['enrollment_management_form'] = self.get_enrollment_management_form() if role_slug in (ROLE_OWNER, ROLE_MANAGER) else None
        context['can_open_student_admin'] = role_slug in (ROLE_OWNER, ROLE_MANAGER)
        context['can_manage_student_payments_full'] = role_slug in (ROLE_OWNER, ROLE_MANAGER)
        context['student_form_operational_focus'] = [
            {
                'label': 'Comece pelo núcleo do cadastro',
                'summary': 'Nome completo e WhatsApp já destravam quase todo o fluxo. O restante só entra quando melhorar decisão, vínculo ou cobrança.',
                'pill_class': 'accent',
                'href': '#student-form-essential',
                'href_label': 'Abrir essencial',
            },
            {
                'label': 'Use o intake para reduzir atrito',
                'summary': (
                    f'Esta edição já nasceu de {selected_intake.full_name} e pode seguir com conversão guiada.'
                    if selected_intake else
                    'Se houver lead ou entrada provisória, vincular aqui evita retrabalho e mantém a conversa viva.'
                ),
                'pill_class': 'info' if selected_intake else 'accent',
                'href': '#student-form-profile',
                'href_label': 'Ver perfil e vínculo',
            },
            {
                'label': 'Feche com plano e cobrança',
                'summary': (
                    f'{latest_enrollment.plan.name} já está ligado ao aluno e {len(recent_payments)} cobrança(s) recente(s) ajudam a ler o financeiro sem sair desta tela.'
                    if latest_enrollment else
                    'Plano, status comercial e cobrança inicial ficam no mesmo fluxo para evitar ida e volta entre cadastro e financeiro.'
                ),
                'pill_class': 'warning' if latest_enrollment else 'success',
                'href': '#student-form-plan',
                'href_label': 'Ver plano e cobrança',
            },
        ]
        form = context.get('form')
        context['plan_price_map'] = {
            str(plan.id): str(plan.price)
            for plan in getattr(getattr(form, 'fields', {}).get('selected_plan'), 'queryset', [])
        }
        return context

    def form_invalid(self, form):
        messages.error(self.request, 'O cadastro não foi salvo. Revise os campos destacados.')
        return super().form_invalid(form)


class StudentQuickCreateView(StudentQuickBaseView):
    page_mode = 'create'

    def form_valid(self, form):
        workflow = run_student_quick_create_workflow(
            actor=self.request.user,
            form=form,
            selected_intake=self.get_selected_intake(),
        )
        self.object = workflow['student']
        messages.success(self.request, f'Aluno {self.object.full_name} cadastrado com sucesso.')
        return super().form_valid(form)


class StudentQuickUpdateView(StudentQuickBaseView):
    page_mode = 'update'

    def dispatch(self, request, *args, **kwargs):
        self.object = get_object_or_404(Student, pk=kwargs['student_id'])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = self.object
        return kwargs

    def form_valid(self, form):
        changed_fields = list(form.changed_data)
        workflow = run_student_quick_update_workflow(
            actor=self.request.user,
            form=form,
            changed_fields=changed_fields,
            selected_intake=self.get_selected_intake(),
        )
        self.object = workflow['student']
        messages.success(self.request, f'Cadastro de {self.object.full_name} atualizado com sucesso.')
        return redirect(self.get_success_url())


class StudentPaymentActionView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = (ROLE_OWNER, ROLE_MANAGER, ROLE_RECEPTION)

    def post(self, request, student_id, *args, **kwargs):
        student = get_object_or_404(Student, pk=student_id)
        action = request.POST.get('action')
        payment = get_object_or_404(Payment, pk=request.POST.get('payment_id'), student=student)

        restricted_actions = {'refund-payment', 'cancel-payment', 'regenerate-payment'}
        if action in restricted_actions and ROLE_RECEPTION in set(request.user.groups.values_list('name', flat=True)):
            messages.error(request, 'A Recepcao so pode salvar cobranca ou confirmar pagamento neste fluxo.')
            return redirect('student-quick-update', student_id=student.id)

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

        return redirect('student-quick-update', student_id=student.id)


class StudentDirectoryExportView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = (ROLE_OWNER, ROLE_DEV, ROLE_MANAGER)

    def get(self, request, report_format, *args, **kwargs):
        students = build_student_directory_snapshot(request.GET)['students']
        try:
            return build_report_response(build_student_directory_report(students=students, report_format=report_format))
        except ValueError as exc:
            raise Http404(str(exc)) from exc


class StudentEnrollmentActionView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = (ROLE_OWNER, ROLE_MANAGER)

    def post(self, request, student_id, *args, **kwargs):
        student = get_object_or_404(Student, pk=student_id)
        action = request.POST.get('action')
        form = EnrollmentManagementForm(request.POST)
        if not form.is_valid():
            return redirect('student-quick-update', student_id=student.id)

        enrollment = get_object_or_404(Enrollment, pk=form.cleaned_data['enrollment_id'], student=student)
        handle_student_enrollment_action(
            actor=request.user,
            student=student,
            enrollment=enrollment,
            action=action,
            action_date=form.cleaned_data['action_date'],
            reason=form.cleaned_data['reason'],
        )

        return redirect('student-quick-update', student_id=student.id)
