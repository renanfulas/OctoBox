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
from catalog.presentation import build_student_directory_page, build_student_form_page
from catalog.presentation.shared import attach_catalog_page_payload
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


STUDENT_FORM_ESSENTIAL_FRAGMENT = 'student-form-essential'
STUDENT_FINANCIAL_FRAGMENT = 'student-financial-overview'
STUDENT_DIRECTORY_FRAGMENT = 'student-directory-board'


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
        student_count = students.count()
        current_role_slug = base_context['current_role'].slug
        export_links = {
            'csv': f"{reverse('student-directory-export', args=['csv'])}?{self.request.GET.urlencode()}",
            'pdf': f"{reverse('student-directory-export', args=['pdf'])}?{self.request.GET.urlencode()}",
        }
        page_payload = build_student_directory_page(
            student_count=student_count,
            students=students[:24],
            student_filter_form=snapshot['filter_form'],
            snapshot=snapshot,
            current_role_slug=current_role_slug,
            export_links=export_links,
        )
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
            return redirect(_append_fragment(reverse('student-quick-update', args=[student.id]), STUDENT_FINANCIAL_FRAGMENT))

        enrollment = get_object_or_404(Enrollment, pk=form.cleaned_data['enrollment_id'], student=student)
        handle_student_enrollment_action(
            actor=request.user,
            student=student,
            enrollment=enrollment,
            action=action,
            action_date=form.cleaned_data['action_date'],
            reason=form.cleaned_data['reason'],
        )

        return redirect(_append_fragment(reverse('student-quick-update', args=[student.id]), STUDENT_FINANCIAL_FRAGMENT))
