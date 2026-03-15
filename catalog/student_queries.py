"""
ARQUIVO: leituras de alunos do catalogo.

POR QUE ELE EXISTE:
- centraliza snapshots e filtros da area de alunos no app real do catalogo.

O QUE ESTE ARQUIVO FAZ:
1. monta o snapshot do diretorio de alunos com filtros e funil.
2. monta o snapshot financeiro da ficha do aluno.

PONTOS CRITICOS:
- mudancas aqui afetam listagens, busca comercial e leitura financeira por aluno.
"""

from django.db.models import Case, CharField, Exists, OuterRef, Q, Subquery, Value, When

from finance.models import Enrollment, EnrollmentStatus, Payment, PaymentStatus
from onboarding.queries import count_pending_intakes, get_intake_conversion_queue
from students.models import Student, StudentStatus

from catalog.forms import StudentDirectoryFilterForm


def build_student_directory_snapshot(params=None):
	latest_enrollment_status = Enrollment.objects.filter(student=OuterRef('pk')).order_by('-start_date', '-created_at').values('status')[:1]
	latest_plan_name = Enrollment.objects.filter(student=OuterRef('pk')).order_by('-start_date', '-created_at').values('plan__name')[:1]
	latest_payment_status = Payment.objects.filter(student=OuterRef('pk')).order_by('-due_date', '-created_at').values('status')[:1]
	overdue_payment_exists = Payment.objects.filter(student=OuterRef('pk'), status=PaymentStatus.OVERDUE)
	pending_payment_exists = Payment.objects.filter(student=OuterRef('pk'), status=PaymentStatus.PENDING)

	students = Student.objects.annotate(
		latest_enrollment_status=Subquery(latest_enrollment_status),
		latest_plan_name=Subquery(latest_plan_name),
		latest_payment_status=Subquery(latest_payment_status),
		has_overdue_payment=Exists(overdue_payment_exists),
		has_pending_payment=Exists(pending_payment_exists),
	).annotate(
		operational_payment_status=Case(
			When(has_overdue_payment=True, then=Value(PaymentStatus.OVERDUE)),
			When(has_pending_payment=True, then=Value(PaymentStatus.PENDING)),
			default=Subquery(latest_payment_status),
			output_field=CharField(),
		),
	).order_by('full_name')
	filter_form = StudentDirectoryFilterForm(params or None)

	if filter_form.is_valid():
		query = (filter_form.cleaned_data.get('query') or '').strip()
		student_status = filter_form.cleaned_data.get('student_status')
		commercial_status = filter_form.cleaned_data.get('commercial_status')
		payment_status = filter_form.cleaned_data.get('payment_status')

		if query:
			normalized_query = query.lower()
			students = students.filter(
				Q(full_name__icontains=query)
				| Q(phone__icontains=query)
				| Q(cpf__icontains=query)
				| Q(email__icontains=query)
				| Q(enrollments__plan__name__icontains=query)
				| Q(enrollments__id__iexact=query)
				| Q(payments__id__iexact=query)
				| Q(status__icontains=normalized_query)
				| Q(enrollments__status__icontains=normalized_query)
				| Q(payments__status__icontains=normalized_query)
			).distinct()
		if student_status:
			students = students.filter(status=student_status)
		if commercial_status:
			students = students.filter(latest_enrollment_status=commercial_status)
		if payment_status:
			students = students.filter(operational_payment_status=payment_status)

	total_students = students.count()
	active_students = students.filter(status=StudentStatus.ACTIVE).count()
	lead_students = students.filter(status=StudentStatus.LEAD).count()
	students_with_active_plan = students.filter(latest_enrollment_status=EnrollmentStatus.ACTIVE).count()
	overdue_students = students.filter(operational_payment_status=PaymentStatus.OVERDUE).count()
	pending_intakes_count = count_pending_intakes()
	intake_queue = list(get_intake_conversion_queue(limit=6))

	priority_students = students.filter(
		Q(operational_payment_status=PaymentStatus.OVERDUE)
		| Q(status=StudentStatus.LEAD)
		| Q(latest_enrollment_status=EnrollmentStatus.PENDING)
	).order_by('full_name')[:6]

	return {
		'students': students,
		'filter_form': filter_form,
		'metrics': {
			'Base cadastrada': {
				'value': total_students,
				'note': 'Pessoas ja registradas para atendimento e acompanhamento.',
			},
			'Alunos ativos': {
				'value': active_students,
				'note': 'Base que ja deveria estar rodando com presenca e cobranca ativas.',
			},
			'Leads em aberto': {
				'value': lead_students,
				'note': 'Contatos que ainda pedem conversao ou fechamento.',
			},
			'Com plano ativo': {
				'value': students_with_active_plan,
				'note': 'Alunos com matricula ativa neste recorte.',
			},
		},
		'funnel': {
			'Entradas para converter': {
				'value': pending_intakes_count,
				'note': 'Leads e entradas provisorias pedindo acao rapida da recepcao.',
			},
			'Financeiro em atraso': {
				'value': overdue_students,
				'note': 'Alunos que pedem contato financeiro ou revisao de rotina.',
			},
			'Sem plano ativo': {
				'value': max(total_students - students_with_active_plan, 0),
				'note': 'Base que exige leitura comercial, ajuste de plano ou reativacao.',
			},
		},
		'priority_students': priority_students,
		'intake_queue': intake_queue,
	}


def build_student_financial_snapshot(student):
	if not student:
		return {
			'has_student': False,
			'summary': 'Salve o aluno primeiro para conectar plano, matricula e rotina financeira.',
			'latest_enrollment': None,
			'enrollment_history': [],
			'payments': [],
			'metrics': {},
		}

	enrollments = student.enrollments.select_related('plan').order_by('-start_date', '-created_at')
	payments = student.payments.select_related('enrollment').order_by('-due_date', '-created_at')[:6]
	latest_enrollment = enrollments.first()

	return {
		'has_student': True,
		'summary': 'Aqui fica a leitura de plano, status comercial e ultimos movimentos financeiros do aluno.',
		'latest_enrollment': latest_enrollment,
		'enrollment_history': enrollments[:6],
		'payments': payments,
		'metrics': {
			'matriculas_ativas': enrollments.filter(status=EnrollmentStatus.ACTIVE).count(),
			'pagamentos_pendentes': student.payments.filter(status=PaymentStatus.PENDING).count(),
			'pagamentos_atrasados': student.payments.filter(status=PaymentStatus.OVERDUE).count(),
		},
	}


__all__ = ['build_student_directory_snapshot', 'build_student_financial_snapshot']