"""
ARQUIVO: views das paginas visuais de catalogo.

POR QUE ELE EXISTE:
- Reune as telas operacionais leves de alunos, financeiro e grade sem jogar o usuario direto no admin.

O QUE ESTE ARQUIVO FAZ:
1. Monta a pagina de alunos com busca, funil e fila de conversao de intake.
2. Entrega o fluxo leve de cadastro/edicao com plano, matricula e cobranca inicial.
3. Permite acoes financeiras e de matricula direto da ficha do aluno.
4. Monta a central visual de financeiro e a grade de aulas.

PONTOS CRITICOS:
- Boa parte da costura comercial do produto passa por este arquivo.
- Alteracoes aqui afetam cadastro, matricula, cobranca, filtros financeiros e auditoria.
"""

from collections import OrderedDict
from uuid import uuid4
from decimal import Decimal
from calendar import month_abbr

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, OuterRef, Q, Subquery, Sum
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import FormView, TemplateView

from boxcore.access.permissions import RoleRequiredMixin
from boxcore.access.roles import ROLE_COACH, ROLE_DEV, ROLE_MANAGER, ROLE_OWNER, get_user_role
from boxcore.auditing import log_audit_event
from .forms import (
    EnrollmentManagementForm,
    FinanceFilterForm,
    MembershipPlanQuickForm,
    PaymentManagementForm,
    StudentDirectoryFilterForm,
    StudentQuickForm,
)
from boxcore.models import (
    BillingCycle,
    ClassSession,
    Enrollment,
    EnrollmentStatus,
    IntakeStatus,
    MembershipPlan,
    Payment,
    PaymentMethod,
    PaymentStatus,
    Student,
    StudentIntake,
    StudentStatus,
)


class CatalogBaseView(LoginRequiredMixin, RoleRequiredMixin, TemplateView):
    allowed_roles = (ROLE_OWNER, ROLE_DEV, ROLE_MANAGER, ROLE_COACH)

    def get_base_context(self):
        return {
            'current_role': get_user_role(self.request.user),
            'today': timezone.localdate(),
        }


class StudentDirectoryView(CatalogBaseView):
    template_name = 'catalog/students.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_base_context())

        latest_enrollment_status = Enrollment.objects.filter(student=OuterRef('pk')).order_by('-start_date', '-created_at').values('status')[:1]
        latest_plan_name = Enrollment.objects.filter(student=OuterRef('pk')).order_by('-start_date', '-created_at').values('plan__name')[:1]
        latest_payment_status = Payment.objects.filter(student=OuterRef('pk')).order_by('-due_date', '-created_at').values('status')[:1]

        students = Student.objects.annotate(
            latest_enrollment_status=Subquery(latest_enrollment_status),
            latest_plan_name=Subquery(latest_plan_name),
            latest_payment_status=Subquery(latest_payment_status),
        ).order_by('full_name')

        filter_form = StudentDirectoryFilterForm(self.request.GET or None)
        if filter_form.is_valid():
            query = filter_form.cleaned_data.get('query')
            student_status = filter_form.cleaned_data.get('student_status')
            commercial_status = filter_form.cleaned_data.get('commercial_status')
            payment_status = filter_form.cleaned_data.get('payment_status')

            if query:
                students = students.filter(
                    Q(full_name__icontains=query)
                    | Q(phone__icontains=query)
                    | Q(cpf__icontains=query)
                    | Q(email__icontains=query)
                )
            if student_status:
                students = students.filter(status=student_status)
            if commercial_status:
                students = students.filter(latest_enrollment_status=commercial_status)
            if payment_status:
                students = students.filter(latest_payment_status=payment_status)

        context['students'] = students[:24]
        context['student_filter_form'] = filter_form
        context['student_metrics'] = {
            'total_alunos': students.count(),
            'ativos': students.filter(status=StudentStatus.ACTIVE).count(),
            'leads': students.filter(status=StudentStatus.LEAD).count(),
            'com_email': students.exclude(email='').count(),
        }
        context['student_funnel'] = {
            'entradas_pendentes': StudentIntake.objects.filter(status__in=[IntakeStatus.NEW, IntakeStatus.REVIEWING], linked_student__isnull=True).count(),
            'alunos_com_plano_ativo': Student.objects.filter(enrollments__status=EnrollmentStatus.ACTIVE).distinct().count(),
            'alunos_com_pagamento_atrasado': Student.objects.filter(payments__status=PaymentStatus.OVERDUE).distinct().count(),
        }
        context['intake_queue'] = StudentIntake.objects.filter(
            status__in=[IntakeStatus.NEW, IntakeStatus.REVIEWING, IntakeStatus.MATCHED],
            linked_student__isnull=True,
        ).order_by('status', '-created_at')[:6]
        context['student_focus'] = [
            'Use esta página para enxergar rapidamente quem já existe no núcleo principal.',
            'O objetivo aqui é leitura e organização mental, não operação fina de cadastro.',
            'Agora esta tela também funciona como funil entre entrada provisoria, aluno definitivo e situacao comercial.',
        ]
        context['can_manage_students'] = context['current_role'].slug in (ROLE_OWNER, ROLE_MANAGER)
        return context


class StudentQuickBaseView(CatalogBaseView, FormView):
    allowed_roles = (ROLE_OWNER, ROLE_MANAGER)
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
        context['page_mode'] = self.page_mode
        context['page_title'] = 'Cadastrar aluno' if self.page_mode == 'create' else 'Editar aluno'
        context['page_subtitle'] = (
            'Comece pelo essencial e complete o resto só se já fizer sentido agora.'
            if self.page_mode == 'create'
            else 'Ajuste rapidamente o cadastro sem cair no admin bruto.'
        )
        context['form_focus'] = [
            'Nome completo e WhatsApp formam o núcleo do cadastro rápido.',
            'Os campos de perfil entram no segundo bloco com a mesma linguagem operacional da academia.',
            'A ideia desta tela é reduzir fricção sem perder legibilidade.',
        ]
        context['student_object'] = self.object
        context['selected_intake'] = self.get_selected_intake()
        context['financial_overview'] = self.get_financial_overview()
        context['payment_management_form'] = self.get_payment_management_form()
        context['enrollment_management_form'] = self.get_enrollment_management_form()
        return context

    def sync_student_enrollment(self, form):
        selected_plan = form.cleaned_data.get('selected_plan')
        enrollment_status = form.cleaned_data.get('enrollment_status') or EnrollmentStatus.PENDING
        latest_enrollment = self.object.enrollments.order_by('-start_date', '-created_at').first()
        due_date = form.cleaned_data.get('payment_due_date') or timezone.localdate()
        payment_method = form.cleaned_data.get('payment_method') or PaymentMethod.PIX
        confirm_payment_now = bool(form.cleaned_data.get('confirm_payment_now'))
        payment_reference = form.cleaned_data.get('payment_reference') or ''
        billing_strategy = form.cleaned_data.get('billing_strategy') or 'single'
        installment_total = form.cleaned_data.get('installment_total') or 1
        recurrence_cycles = form.cleaned_data.get('recurrence_cycles') or 1
        base_amount = form.cleaned_data.get('initial_payment_amount') or selected_plan.price if selected_plan else Decimal('0.00')

        if selected_plan is None:
            return {'enrollment': None, 'payment': None, 'movement': 'none'}

        if latest_enrollment is None:
            enrollment = Enrollment.objects.create(
                student=self.object,
                plan=selected_plan,
                status=enrollment_status,
                start_date=timezone.localdate(),
                notes='Plano conectado pela tela leve do aluno.',
            )
            payment = self.create_initial_payment(
                enrollment,
                due_date=due_date,
                payment_method=payment_method,
                confirm_payment_now=confirm_payment_now,
                note='Primeira cobranca criada no fluxo leve do aluno.',
                amount=base_amount,
                reference=payment_reference,
                billing_strategy=billing_strategy,
                installment_total=installment_total,
                recurrence_cycles=recurrence_cycles,
            )
            return {'enrollment': enrollment, 'payment': payment, 'movement': 'created'}

        if latest_enrollment.plan_id == selected_plan.id:
            latest_enrollment.plan = selected_plan
            latest_enrollment.status = enrollment_status
            if latest_enrollment.start_date is None:
                latest_enrollment.start_date = timezone.localdate()
            latest_enrollment.save(update_fields=['plan', 'status', 'start_date', 'updated_at'])
            payment = None
            if not latest_enrollment.payments.exists():
                payment = self.create_initial_payment(
                    latest_enrollment,
                    due_date=due_date,
                    payment_method=payment_method,
                    confirm_payment_now=confirm_payment_now,
                    note='Primeira cobranca criada no fluxo leve do aluno.',
                    amount=base_amount,
                    reference=payment_reference,
                    billing_strategy=billing_strategy,
                    installment_total=installment_total,
                    recurrence_cycles=recurrence_cycles,
                )
            return {'enrollment': latest_enrollment, 'payment': payment, 'movement': 'status_adjusted'}

        movement = self.describe_plan_change(latest_enrollment.plan, selected_plan)
        latest_enrollment.status = EnrollmentStatus.EXPIRED
        latest_enrollment.end_date = timezone.localdate()
        latest_enrollment.notes = '\n'.join(filter(None, [latest_enrollment.notes.strip(), f'Encerrada por {movement} na tela leve do aluno.']))
        latest_enrollment.save(update_fields=['status', 'end_date', 'notes', 'updated_at'])

        enrollment = Enrollment.objects.create(
            student=self.object,
            plan=selected_plan,
            status=enrollment_status,
            start_date=timezone.localdate(),
            notes=f'{movement.capitalize()} aplicada pela tela leve do aluno.',
        )
        payment = self.create_initial_payment(
            enrollment,
            due_date=due_date,
            payment_method=payment_method,
            confirm_payment_now=confirm_payment_now,
            note=f'Cobranca criada apos {movement} de plano.',
            amount=base_amount,
            reference=payment_reference,
            billing_strategy=billing_strategy,
            installment_total=installment_total,
            recurrence_cycles=recurrence_cycles,
        )
        return {'enrollment': enrollment, 'payment': payment, 'movement': movement}

    def create_initial_payment(
        self,
        enrollment,
        *,
        due_date,
        payment_method,
        confirm_payment_now,
        note,
        amount,
        reference,
        billing_strategy,
        installment_total,
        recurrence_cycles,
    ):
        billing_group = str(uuid4())
        created_payment = None

        if billing_strategy == 'installments':
            # Parcelamento precisa fechar exatamente o valor original, mesmo com arredondamento.
            total = max(installment_total, 1)
            normalized_amount = Decimal(amount)
            installment_amount = (normalized_amount / total).quantize(Decimal('0.01'))
            running_total = Decimal('0.00')
            for index in range(1, total + 1):
                current_amount = installment_amount if index < total else normalized_amount - running_total
                running_total += current_amount
                payment = Payment.objects.create(
                    student=self.object,
                    enrollment=enrollment,
                    due_date=self.advance_due_date(due_date, index - 1, enrollment.plan.billing_cycle),
                    amount=current_amount,
                    status=PaymentStatus.PAID if confirm_payment_now and index == 1 else PaymentStatus.PENDING,
                    method=payment_method,
                    paid_at=timezone.now() if confirm_payment_now and index == 1 else None,
                    reference=reference,
                    notes=note,
                    billing_group=billing_group,
                    installment_number=index,
                    installment_total=total,
                )
                created_payment = created_payment or payment
            return created_payment

        if billing_strategy == 'recurring':
            # Recorrencia reaproveita o mesmo valor e so desloca vencimentos dentro do mesmo grupo comercial.
            cycles = max(recurrence_cycles, 1)
            for index in range(1, cycles + 1):
                payment = Payment.objects.create(
                    student=self.object,
                    enrollment=enrollment,
                    due_date=self.advance_due_date(due_date, index - 1, enrollment.plan.billing_cycle),
                    amount=amount,
                    status=PaymentStatus.PAID if confirm_payment_now and index == 1 else PaymentStatus.PENDING,
                    method=payment_method,
                    paid_at=timezone.now() if confirm_payment_now and index == 1 else None,
                    reference=reference,
                    notes=note,
                    billing_group=billing_group,
                    installment_number=index,
                    installment_total=cycles,
                )
                created_payment = created_payment or payment
            return created_payment

        return Payment.objects.create(
            student=self.object,
            enrollment=enrollment,
            due_date=due_date,
            amount=amount,
            status=PaymentStatus.PAID if confirm_payment_now else PaymentStatus.PENDING,
            method=payment_method,
            paid_at=timezone.now() if confirm_payment_now else None,
            reference=reference,
            notes=note,
            billing_group=billing_group,
            installment_number=1,
            installment_total=1,
        )

    def advance_due_date(self, start_date, step, billing_cycle):
        if step == 0:
            return start_date
        if billing_cycle == BillingCycle.WEEKLY:
            return start_date + timezone.timedelta(days=7 * step)
        if billing_cycle == BillingCycle.QUARTERLY:
            return self.shift_month(start_date, step * 3)
        if billing_cycle == BillingCycle.YEARLY:
            return self.shift_month(start_date, step * 12)
        return self.shift_month(start_date, step)

    def shift_month(self, source_date, month_delta):
        month_index = source_date.month - 1 + month_delta
        year = source_date.year + month_index // 12
        month = month_index % 12 + 1
        return source_date.replace(year=year, month=month, day=1)

    def describe_plan_change(self, previous_plan, selected_plan):
        if selected_plan.price > previous_plan.price:
            return 'upgrade'
        if selected_plan.price < previous_plan.price:
            return 'downgrade'
        return 'troca de plano'

    def sync_intake_record(self, form):
        intake = form.cleaned_data.get('intake_record') or self.get_selected_intake()
        if intake is None:
            # Fallback por WhatsApp evita perder a ligacao quando o lead chegou antes da conversao formal.
            intake = StudentIntake.objects.filter(phone=self.object.phone, linked_student__isnull=True).order_by('-created_at').first()
        if intake is None:
            return None
        intake.linked_student = self.object
        intake.status = IntakeStatus.APPROVED
        intake.notes = '\n'.join(filter(None, [intake.notes.strip(), 'Convertido em aluno definitivo pela tela leve.']))
        intake.save(update_fields=['linked_student', 'status', 'notes', 'updated_at'])
        return intake

    def get_financial_overview(self):
        if not self.object:
            return {
                'has_student': False,
                'summary': 'Salve o aluno primeiro para conectar plano, matricula e rotina financeira.',
                'latest_enrollment': None,
                'enrollment_history': [],
                'payments': [],
                'metrics': {},
            }

        enrollments = self.object.enrollments.select_related('plan').order_by('-start_date', '-created_at')
        payments = self.object.payments.select_related('enrollment').order_by('-due_date', '-created_at')[:6]
        latest_enrollment = enrollments.first()

        return {
            'has_student': True,
            'summary': 'Aqui fica a leitura de plano, status comercial e ultimos movimentos financeiros do aluno.',
            'latest_enrollment': latest_enrollment,
            'enrollment_history': enrollments[:6],
            'payments': payments,
            'metrics': {
                'matriculas_ativas': enrollments.filter(status=EnrollmentStatus.ACTIVE).count(),
                'pagamentos_pendentes': self.object.payments.filter(status=PaymentStatus.PENDING).count(),
                'pagamentos_atrasados': self.object.payments.filter(status=PaymentStatus.OVERDUE).count(),
            },
        }

    def form_invalid(self, form):
        messages.error(self.request, 'O cadastro não foi salvo. Revise os campos destacados.')
        return super().form_invalid(form)


class StudentQuickCreateView(StudentQuickBaseView):
    page_mode = 'create'

    def form_valid(self, form):
        self.object = form.save()
        enrollment_sync = self.sync_student_enrollment(form)
        intake = self.sync_intake_record(form)
        log_audit_event(
            actor=self.request.user,
            action='student_quick_created',
            target=self.object,
            description='Aluno criado pela tela leve de cadastro.',
            metadata={
                'status': self.object.status,
                'enrollment_id': enrollment_sync['enrollment'].id if enrollment_sync['enrollment'] else None,
                'payment_id': enrollment_sync['payment'].id if enrollment_sync['payment'] else None,
                'movement': enrollment_sync['movement'],
                'intake_id': intake.id if intake else None,
            },
        )
        if enrollment_sync['payment'] is not None:
            log_audit_event(
                actor=self.request.user,
                action='student_quick_payment_created',
                target=enrollment_sync['payment'],
                description='Primeira cobranca criada pela tela leve do aluno.',
                metadata={'status': enrollment_sync['payment'].status, 'method': enrollment_sync['payment'].method},
            )
        if intake is not None:
            log_audit_event(
                actor=self.request.user,
                action='student_intake_converted',
                target=intake,
                description='Lead convertido em aluno pela tela leve.',
                metadata={'student_id': self.object.id},
            )
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
        self.object = form.save()
        enrollment_sync = self.sync_student_enrollment(form)
        intake = self.sync_intake_record(form)
        log_audit_event(
            actor=self.request.user,
            action='student_quick_updated',
            target=self.object,
            description='Aluno alterado pela tela leve de cadastro.',
            metadata={
                'changed_fields': changed_fields,
                'enrollment_id': enrollment_sync['enrollment'].id if enrollment_sync['enrollment'] else None,
                'payment_id': enrollment_sync['payment'].id if enrollment_sync['payment'] else None,
                'movement': enrollment_sync['movement'],
                'intake_id': intake.id if intake else None,
            },
        )
        if enrollment_sync['movement'] in ('upgrade', 'downgrade', 'troca de plano'):
            log_audit_event(
                actor=self.request.user,
                action='student_plan_changed',
                target=enrollment_sync['enrollment'],
                description='Troca de plano registrada pela tela leve do aluno.',
                metadata={'movement': enrollment_sync['movement']},
            )
        if enrollment_sync['payment'] is not None:
            log_audit_event(
                actor=self.request.user,
                action='student_quick_payment_created',
                target=enrollment_sync['payment'],
                description='Cobranca criada ou confirmada pela tela leve do aluno.',
                metadata={'status': enrollment_sync['payment'].status, 'method': enrollment_sync['payment'].method},
            )
        if intake is not None:
            log_audit_event(
                actor=self.request.user,
                action='student_intake_converted',
                target=intake,
                description='Lead vinculado ao aluno pela tela leve.',
                metadata={'student_id': self.object.id},
            )
        messages.success(self.request, f'Cadastro de {self.object.full_name} atualizado com sucesso.')
        return redirect(self.get_success_url())


class FinanceCenterView(CatalogBaseView, FormView):
    template_name = 'catalog/finance.html'
    form_class = MembershipPlanQuickForm
    allowed_roles = (ROLE_OWNER, ROLE_DEV, ROLE_MANAGER)

    def get_success_url(self):
        return reverse('finance-center')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_base_context())
        filter_form = self.get_filter_form()
        context['page_title'] = 'Financeiro'
        context['page_subtitle'] = 'Aqui o box ganha leitura comercial: planos, receita, retencao e sinais operacionais que depois conversam com a jornada do aluno.'
        context['can_manage_finance'] = context['current_role'].slug in (ROLE_OWNER, ROLE_MANAGER)
        context['finance_filter_form'] = filter_form
        context['finance_metrics'] = self.get_finance_metrics(filter_form)
        context['plan_portfolio'] = self.get_plan_portfolio(filter_form)
        context['plan_mix'] = self.get_plan_mix()
        context['monthly_comparison'] = self.get_monthly_comparison(filter_form)
        context['comparison_peaks'] = self.get_comparison_peaks(context['monthly_comparison'])
        context['financial_alerts'] = self.get_financial_alerts(filter_form)
        context['recent_movements'] = self.get_recent_movements(filter_form)
        return context

    def get_filter_form(self):
        return FinanceFilterForm(self.request.GET or None)

    def get_filter_values(self, filter_form):
        months = 6
        selected_plan = None
        payment_status = ''
        payment_method = ''
        if filter_form.is_valid():
            months = int(filter_form.cleaned_data.get('months') or 6)
            selected_plan = filter_form.cleaned_data.get('plan')
            payment_status = filter_form.cleaned_data.get('payment_status') or ''
            payment_method = filter_form.cleaned_data.get('payment_method') or ''
        return months, selected_plan, payment_status, payment_method

    def get_period_start(self, months):
        anchor = timezone.localdate().replace(day=1)
        return self.shift_month(anchor, -(months - 1))

    def apply_finance_filters(self, filter_form):
        months, selected_plan, payment_status, payment_method = self.get_filter_values(filter_form)
        start_date = self.get_period_start(months)
        # Todos os cards e graficos da tela partem da mesma base filtrada para evitar leituras conflitantes.
        payments = Payment.objects.select_related('student', 'enrollment__plan').filter(due_date__gte=start_date)
        enrollments = Enrollment.objects.select_related('student', 'plan').filter(start_date__gte=start_date)
        plans = MembershipPlan.objects.all()

        if selected_plan is not None:
            payments = payments.filter(enrollment__plan=selected_plan)
            enrollments = enrollments.filter(plan=selected_plan)
            plans = plans.filter(pk=selected_plan.id)
        if payment_status:
            payments = payments.filter(status=payment_status)
        if payment_method:
            payments = payments.filter(method=payment_method)

        return start_date, payments, enrollments, plans

    def form_valid(self, form):
        current_role = self.get_base_context()['current_role']
        if current_role.slug not in (ROLE_OWNER, ROLE_MANAGER):
            messages.error(self.request, 'Seu papel atual pode consultar o financeiro, mas nao criar planos por esta tela.')
            return redirect(self.get_success_url())

        plan = form.save()
        log_audit_event(
            actor=self.request.user,
            action='membership_plan_quick_created',
            target=plan,
            description='Plano criado pela central visual de financeiro.',
            metadata={'price': str(plan.price), 'billing_cycle': plan.billing_cycle},
        )
        messages.success(self.request, f'Plano {plan.name} cadastrado com sucesso.')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'O plano nao foi salvo. Revise os campos destacados.')
        return super().form_invalid(form)

    def get_finance_metrics(self, filter_form):
        today = timezone.localdate()
        _, payments, enrollments, _ = self.apply_finance_filters(filter_form)
        month_start = today.replace(day=1)
        previous_month_end = month_start - timezone.timedelta(days=1)
        previous_month_start = previous_month_end.replace(day=1)

        revenue_this_month = payments.filter(
            status=PaymentStatus.PAID,
            due_date__gte=month_start,
        ).aggregate(total=Coalesce(Sum('amount'), Decimal('0.00')))['total']
        revenue_previous_month = Payment.objects.filter(
            status=PaymentStatus.PAID,
            due_date__gte=previous_month_start,
            due_date__lte=previous_month_end,
        ).aggregate(total=Coalesce(Sum('amount'), Decimal('0.00')))['total']
        open_revenue = payments.filter(
            status__in=[PaymentStatus.PENDING, PaymentStatus.OVERDUE],
        ).aggregate(total=Coalesce(Sum('amount'), Decimal('0.00')))['total']
        paid_count = payments.filter(status=PaymentStatus.PAID, due_date__gte=month_start).count()
        active_growth = enrollments.filter(
            status=EnrollmentStatus.ACTIVE,
            start_date__gte=month_start,
        ).count()
        cancellations = enrollments.filter(
            status=EnrollmentStatus.CANCELED,
            updated_at__date__gte=month_start,
        ).count()
        overdue_students = payments.filter(
            status=PaymentStatus.OVERDUE,
        ).values('student_id').distinct().count()

        return {
            'faturamento_mes': {
                'value': revenue_this_month,
                'note': f'Mes anterior: R$ {revenue_previous_month}',
            },
            'receita_em_aberto': {
                'value': open_revenue,
                'note': 'Soma de pagamentos pendentes e atrasados.',
            },
            'novos_ativos_mes': {
                'value': active_growth,
                'note': 'Matriculas ativas iniciadas neste mes.',
            },
            'cancelamentos_mes': {
                'value': cancellations,
                'note': 'Matriculas canceladas registradas neste mes.',
            },
            'ticket_medio_pago': {
                'value': revenue_this_month / paid_count if paid_count else Decimal('0.00'),
                'note': 'Media dos pagamentos efetivamente recebidos no mes.',
            },
            'alunos_em_atraso': {
                'value': overdue_students,
                'note': 'Quantidade de alunos com pagamento vencido.',
            },
        }

    def get_plan_portfolio(self, filter_form):
        _, payments, enrollments, plans = self.apply_finance_filters(filter_form)
        month_start = timezone.localdate().replace(day=1)
        payment_ids = list(payments.values_list('id', flat=True))
        enrollment_ids = list(enrollments.values_list('id', flat=True))
        # O fallback com [-1] mantem o annotate estavel mesmo quando o recorte filtrado nao retorna ids.
        return plans.annotate(
            active_enrollments=Count(
                'enrollments',
                filter=Q(enrollments__status=EnrollmentStatus.ACTIVE, enrollments__id__in=enrollment_ids or [-1]),
                distinct=True,
            ),
            pending_enrollments=Count(
                'enrollments',
                filter=Q(enrollments__status=EnrollmentStatus.PENDING, enrollments__id__in=enrollment_ids or [-1]),
                distinct=True,
            ),
            revenue_this_month=Coalesce(
                Sum(
                    'enrollments__payments__amount',
                    filter=Q(
                        enrollments__payments__status=PaymentStatus.PAID,
                        enrollments__payments__due_date__gte=month_start,
                        enrollments__payments__id__in=payment_ids or [-1],
                    ),
                ),
                Decimal('0.00'),
            ),
        ).order_by('-active', 'price', 'name')

    def get_plan_mix(self):
        plans = list(self.get_plan_portfolio(self.get_filter_form()))
        total_active = sum(plan.active_enrollments for plan in plans) or 1
        mix = []
        for plan in plans:
            mix.append(
                {
                    'name': plan.name,
                    'active_enrollments': plan.active_enrollments,
                    'width': round((plan.active_enrollments / total_active) * 100, 1) if plan.active_enrollments else 6,
                    'revenue_this_month': plan.revenue_this_month,
                }
            )
        return mix[:6]

    def get_financial_alerts(self, filter_form):
        _, payments, _, _ = self.apply_finance_filters(filter_form)
        return payments.filter(
            status__in=[PaymentStatus.PENDING, PaymentStatus.OVERDUE],
        ).order_by('due_date', 'student__full_name')[:8]

    def get_recent_movements(self, filter_form):
        _, _, enrollments, _ = self.apply_finance_filters(filter_form)
        return enrollments.order_by('-updated_at', '-created_at')[:8]

    def get_monthly_comparison(self, filter_form):
        series = []
        months, selected_plan, payment_status, payment_method = self.get_filter_values(filter_form)
        month_anchor = timezone.localdate().replace(day=1)

        for offset in range(months - 1, -1, -1):
            start_date = self.shift_month(month_anchor, -offset)
            end_date = self.shift_month(start_date, 1) - timezone.timedelta(days=1)
            revenue_payments = Payment.objects.filter(
                status=PaymentStatus.PAID,
                due_date__gte=start_date,
                due_date__lte=end_date,
            )
            if selected_plan is not None:
                revenue_payments = revenue_payments.filter(enrollment__plan=selected_plan)
            if payment_method:
                revenue_payments = revenue_payments.filter(method=payment_method)
            if payment_status:
                revenue_payments = revenue_payments.filter(status=payment_status)
            revenue = revenue_payments.aggregate(total=Coalesce(Sum('amount'), Decimal('0.00')))['total']

            activations_query = Enrollment.objects.filter(
                status=EnrollmentStatus.ACTIVE,
                start_date__gte=start_date,
                start_date__lte=end_date,
            )
            cancellations_query = Enrollment.objects.filter(
                status=EnrollmentStatus.CANCELED,
                updated_at__date__gte=start_date,
                updated_at__date__lte=end_date,
            )
            if selected_plan is not None:
                activations_query = activations_query.filter(plan=selected_plan)
                cancellations_query = cancellations_query.filter(plan=selected_plan)
            activations = activations_query.count()
            cancellations = cancellations_query.count()
            series.append(
                {
                    'label': f'{month_abbr[start_date.month].upper()}/{str(start_date.year)[-2:]}',
                    'revenue': revenue,
                    'activations': activations,
                    'cancellations': cancellations,
                    'net_growth': activations - cancellations,
                }
            )
        return series

    def get_comparison_peaks(self, series):
        max_revenue = max((item['revenue'] for item in series), default=Decimal('0.00'))
        max_count = max((max(item['activations'], item['cancellations']) for item in series), default=0)
        return {
            'max_revenue': max_revenue or Decimal('1.00'),
            'max_count': max_count or 1,
        }

    def shift_month(self, source_date, month_delta):
        month_index = source_date.month - 1 + month_delta
        year = source_date.year + month_index // 12
        month = month_index % 12 + 1
        return source_date.replace(year=year, month=month, day=1)


class StudentPaymentActionView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = (ROLE_OWNER, ROLE_MANAGER)

    def post(self, request, student_id, *args, **kwargs):
        student = get_object_or_404(Student, pk=student_id)
        action = request.POST.get('action')
        payment = get_object_or_404(Payment, pk=request.POST.get('payment_id'), student=student)

        if action == 'update-payment':
            form = PaymentManagementForm(request.POST)
            if form.is_valid():
                payment.amount = form.cleaned_data['amount']
                payment.due_date = form.cleaned_data['due_date']
                payment.method = form.cleaned_data['method']
                payment.reference = form.cleaned_data['reference']
                payment.notes = form.cleaned_data['notes']
                payment.save(update_fields=['amount', 'due_date', 'method', 'reference', 'notes', 'updated_at'])
                log_audit_event(
                    actor=request.user,
                    action='student_payment_updated',
                    target=payment,
                    description='Cobranca atualizada pela tela do aluno.',
                    metadata={'status': payment.status},
                )
        elif action == 'mark-paid':
            payment.status = PaymentStatus.PAID
            payment.paid_at = timezone.now()
            payment.save(update_fields=['status', 'paid_at', 'updated_at'])
            log_audit_event(
                actor=request.user,
                action='student_payment_marked_paid',
                target=payment,
                description='Cobranca confirmada como paga pela tela do aluno.',
                metadata={'method': payment.method},
            )
        elif action == 'refund-payment':
            payment.status = PaymentStatus.REFUNDED
            payment.save(update_fields=['status', 'updated_at'])
            log_audit_event(
                actor=request.user,
                action='student_payment_refunded',
                target=payment,
                description='Pagamento estornado pela tela do aluno.',
                metadata={},
            )
        elif action == 'cancel-payment':
            payment.status = PaymentStatus.CANCELED
            payment.save(update_fields=['status', 'updated_at'])
            log_audit_event(
                actor=request.user,
                action='student_payment_canceled',
                target=payment,
                description='Cobranca cancelada pela tela do aluno.',
                metadata={},
            )
        elif action == 'regenerate-payment':
            due_date = payment.due_date
            enrollment = payment.enrollment or student.enrollments.order_by('-start_date', '-created_at').first()
            if enrollment is not None:
                # A nova cobranca preserva o grupo comercial para manter rastreabilidade de parcela/recorrencia.
                next_due = StudentQuickBaseView().advance_due_date(due_date, 1, enrollment.plan.billing_cycle)
                new_payment = Payment.objects.create(
                    student=student,
                    enrollment=enrollment,
                    due_date=next_due,
                    amount=payment.amount,
                    status=PaymentStatus.PENDING,
                    method=payment.method,
                    reference=payment.reference,
                    notes='Cobranca regenerada pela tela do aluno.',
                    billing_group=payment.billing_group or str(uuid4()),
                    installment_number=payment.installment_number + 1,
                    installment_total=max(payment.installment_total, payment.installment_number + 1),
                )
                log_audit_event(
                    actor=request.user,
                    action='student_payment_regenerated',
                    target=new_payment,
                    description='Nova cobranca gerada pela tela do aluno.',
                    metadata={'previous_payment_id': payment.id},
                )

        return redirect('student-quick-update', student_id=student.id)


class StudentEnrollmentActionView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = (ROLE_OWNER, ROLE_MANAGER)

    def post(self, request, student_id, *args, **kwargs):
        student = get_object_or_404(Student, pk=student_id)
        action = request.POST.get('action')
        form = EnrollmentManagementForm(request.POST)
        if not form.is_valid():
            return redirect('student-quick-update', student_id=student.id)

        enrollment = get_object_or_404(Enrollment, pk=form.cleaned_data['enrollment_id'], student=student)
        action_date = form.cleaned_data['action_date']
        reason = form.cleaned_data['reason']

        if action == 'cancel-enrollment':
            enrollment.status = EnrollmentStatus.CANCELED
            enrollment.end_date = action_date
            enrollment.notes = '\n'.join(filter(None, [enrollment.notes.strip(), f'Cancelada pela tela do aluno. Motivo: {reason or "nao informado"}.']))
            enrollment.save(update_fields=['status', 'end_date', 'notes', 'updated_at'])
            # Cancelar a matricula precisa encerrar tambem as cobrancas futuras que ainda nao foram liquidadas.
            enrollment.payments.filter(status=PaymentStatus.PENDING, due_date__gte=action_date).update(status=PaymentStatus.CANCELED)
            log_audit_event(
                actor=request.user,
                action='student_enrollment_canceled',
                target=enrollment,
                description='Matricula cancelada pela tela do aluno.',
                metadata={'reason': reason},
            )
        elif action == 'reactivate-enrollment':
            new_enrollment = Enrollment.objects.create(
                student=student,
                plan=enrollment.plan,
                status=EnrollmentStatus.ACTIVE,
                start_date=action_date,
                notes=f'Reativada pela tela do aluno. Motivo: {reason or "nao informado"}.',
            )
            # Reativacao nasce com uma nova matricula para preservar historico em vez de sobrescrever o ciclo anterior.
            Payment.objects.create(
                student=student,
                enrollment=new_enrollment,
                due_date=action_date,
                amount=new_enrollment.plan.price,
                status=PaymentStatus.PENDING,
                method=PaymentMethod.PIX,
                notes='Cobranca criada na reativacao da matricula.',
                billing_group=str(uuid4()),
                installment_number=1,
                installment_total=1,
            )
            log_audit_event(
                actor=request.user,
                action='student_enrollment_reactivated',
                target=new_enrollment,
                description='Matricula reativada pela tela do aluno.',
                metadata={'reason': reason},
            )

        return redirect('student-quick-update', student_id=student.id)


class MembershipPlanQuickUpdateView(FinanceCenterView):
    template_name = 'catalog/finance-plan-form.html'
    page_mode = 'update'
    object = None

    def dispatch(self, request, *args, **kwargs):
        self.object = get_object_or_404(MembershipPlan, pk=kwargs['plan_id'])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = self.object
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Editar plano'
        context['page_subtitle'] = 'Ajuste valor, ciclo e proposta comercial sem sair do centro financeiro.'
        context['plan_object'] = self.object
        context['billing_cycle_options'] = BillingCycle
        context['payment_method_options'] = PaymentMethod
        return context

    def form_valid(self, form):
        changed_fields = list(form.changed_data)
        plan = form.save()
        log_audit_event(
            actor=self.request.user,
            action='membership_plan_quick_updated',
            target=plan,
            description='Plano alterado pela central visual de financeiro.',
            metadata={'changed_fields': changed_fields},
        )
        messages.success(self.request, f'Plano {plan.name} atualizado com sucesso.')
        return redirect(self.get_success_url())


class ClassGridView(CatalogBaseView):
    template_name = 'catalog/class-grid.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_base_context())

        start_date = context['today']
        end_date = start_date + timezone.timedelta(days=13)
        sessions = (
            ClassSession.objects.filter(scheduled_at__date__gte=start_date, scheduled_at__date__lte=end_date)
            .select_related('coach')
            .annotate(occupied_slots=Count('attendances'))
            .order_by('scheduled_at')
        )

        grouped_sessions = OrderedDict()
        for session in sessions:
            day = timezone.localtime(session.scheduled_at).date()
            grouped_sessions.setdefault(day, []).append(session)

        context['grouped_sessions'] = grouped_sessions.items()
        context['class_metrics'] = {
            'aulas_14_dias': sessions.count(),
            'dias_com_aula': len(grouped_sessions),
            'aulas_lotadas': sum(1 for session in sessions if session.occupied_slots >= session.capacity),
        }
        context['class_focus'] = [
            'Esta grade existe para te dar uma visão visual da agenda antes de aprofundar regras mais pesadas.',
            'Ela ajuda a separar mentalmente grade, ocupação e rotina de coach do restante do sistema.',
            'Quando a operação crescer, esta tela pode virar um centro mais forte de planejamento de aulas.',
        ]
        return context