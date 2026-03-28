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

from django.utils import timezone
from operations.models import Attendance
from finance.models import Enrollment, EnrollmentStatus, Payment, PaymentStatus
from onboarding.queries import count_pending_intakes, get_intake_conversion_queue
from students.models import Student, StudentStatus

from catalog.forms import StudentDirectoryFilterForm
from shared_support.redis_snapshots import get_student_snapshot, update_student_snapshot


def compute_fidalgometro_score(student):
    """
    Computa o score de saude (Fidalgometro) do aluno:
    - RED: Inadimplente (cobranca vencida).
    - YELLOW: Sumido (pago mas sem treino ha > 7 dias).
    - BLUE: Fiel (pago e treinou recentemente).
    """
    if not student:
        return {'code': 'gray', 'label': 'Sem dados', 'detail': 'Dados insuficientes.'}

    # 1. Inadimplência (Atraso Real)
    has_overdue = student.payments.filter(
        status__in=[PaymentStatus.PENDING, PaymentStatus.OVERDUE],
        due_date__lt=timezone.localdate()
    ).exists()

    if has_overdue:
        return {'code': 'red', 'label': 'Inadimplente', 'detail': 'Há cobranças vencidas.'}

    # 2. Engajamento (Treino)
    last_attendance = Attendance.objects.filter(student=student, check_in_at__isnull=False).order_by('-check_in_at').first()
    if not last_attendance:
        return {'code': 'orange', 'label': 'Sem Treino', 'detail': 'Ainda não registrou check-in no Box.'}

    days_ago = (timezone.now() - last_attendance.check_in_at).days
    if days_ago > 7:
        return {'code': 'yellow', 'label': f'Sumido ({days_ago} dias)', 'detail': 'Não treina há mais de uma semana.'}

    return {'code': 'blue', 'label': 'Fiel & Ativo', 'detail': 'Pagamentos em dia e treinou recentemente.'}


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
	).defer('cpf', 'notes', 'health_issue_status', 'created_at', 'updated_at').order_by('full_name')
	filter_form = StudentDirectoryFilterForm(params or None)

	if filter_form.is_valid():
		query = (filter_form.cleaned_data.get('query') or '').strip()
		student_status = filter_form.cleaned_data.get('student_status')
		commercial_status = filter_form.cleaned_data.get('commercial_status')
		payment_status = filter_form.cleaned_data.get('payment_status')

		if query:
			normalized_query = query.lower()
			clean_digits = ''.join(filter(str.isdigit, query))
			
			query_filter = Q(full_name__icontains=query) | Q(email__icontains=query)
			
			if clean_digits:
				query_filter |= Q(phone__icontains=clean_digits)
				query_filter |= Q(whatsapp__icontains=clean_digits)
				query_filter |= Q(cpf__icontains=clean_digits)
			
			# Plan and status search
			query_filter |= Q(enrollments__plan__name__icontains=query)
			query_filter |= Q(status__icontains=normalized_query)
			
			students = students.filter(query_filter).distinct()
		if student_status:
			students = students.filter(status=student_status)
		if commercial_status:
			students = students.filter(latest_enrollment_status=commercial_status)
		if payment_status:
			students = students.filter(operational_payment_status=payment_status)

	# 🚀 Performance AAA (Db-Bypass): Agregação Unificada de Elite
	from django.db.models import Count
	metrics = students.aggregate(
		total=Count('id'),
		em_dia=Count('id', filter=Q(status=StudentStatus.ACTIVE, operational_payment_status=PaymentStatus.PAID)),
		inadimplentes=Count('id', filter=Q(operational_payment_status=PaymentStatus.OVERDUE)),
		pendentes=Count('id', filter=Q(operational_payment_status=PaymentStatus.PENDING))
	)

	total_students = metrics['total']
	em_dia_count = metrics['em_dia']
	inadimplentes_count = metrics['inadimplentes']
	pendentes_count = metrics['pendentes']
	
	pending_intakes_count = count_pending_intakes()
	intake_queue = list(get_intake_conversion_queue(limit=6))

	priority_students = students.filter(
		Q(operational_payment_status=PaymentStatus.OVERDUE)
		| Q(status=StudentStatus.LEAD)
		| Q(latest_enrollment_status=EnrollmentStatus.PENDING)
	).order_by('full_name')[:6]

	return {
		'students': students,
		'total_students': total_students,
		'filter_form': filter_form,
		'interactive_kpis': [
			{
				'label': 'Total de Alunos',
				'display_value': total_students,
				'icon': 'users', # Representado por ícone no front
				'tone_class': 'kpi-blue',
				'data_action': 'open-tab-students-directory',
			},
			{
				'label': 'Em dia',
				'display_value': em_dia_count,
				'icon': 'check-circle',
				'tone_class': 'kpi-green',
				'data_action': 'filter-em-dia',
			},
			{
				'label': 'Inadimplentes',
				'display_value': inadimplentes_count,
				'icon': 'alert-circle',
				'tone_class': 'kpi-red',
				'data_action': 'filter-atrasados',
			},
			{
				'label': 'Pendentes',
				'display_value': pendentes_count,
				'icon': 'clock',
				'tone_class': 'kpi-orange',
				'data_action': 'filter-pendentes',
			},
		],
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
			'fidalgometro': compute_fidalgometro_score(None),
		}

	ghost = get_student_snapshot(student.id)
	if not ghost:
		ghost = update_student_snapshot(student.id)

	# 🚀 Performance AAA (Ghost Path): Se tivermos o Ghost, usamos ele para o status imediato.
	enrollments = student.enrollments.select_related('plan').order_by('-start_date', '-created_at')
	raw_payments = student.payments.select_related('enrollment').order_by('due_date', 'created_at')[:6]
	latest_enrollment = enrollments.first()

	# Smart Payment Action Visibility Logic (7-Day Window)
	today = timezone.localdate()
	seven_days_from_now = today + timezone.timedelta(days=7)
	
	proximos_vencimentos_count = 0
	payments_list = []
	for p in raw_payments:
		p.is_next_actionable = False
		if p.status == PaymentStatus.OVERDUE:
			p.is_next_actionable = True
		elif p.status == PaymentStatus.PENDING:
			# Só mostramos ação se estiver perto do vencimento (janela de 7 dias)
			if p.due_date <= seven_days_from_now:
				p.is_next_actionable = True
				proximos_vencimentos_count += 1
		payments_list.append(p)

	# Restore original order for UI (descending)
	payments_list.sort(key=lambda x: x.due_date, reverse=True)

	return {
		'has_student': True,
		'summary': 'Aqui fica a leitura de plano, status comercial e ultimos movimentos financeiros do aluno.',
		'latest_enrollment': latest_enrollment,
		'enrollment_history': enrollments[:6],
		'payments': payments_list,
		'fidalgometro': compute_fidalgometro_score(student),
		'metrics': {
			'matriculas_ativas': enrollments.filter(status=EnrollmentStatus.ACTIVE).count(),
			'pagamentos_pendentes': student.payments.filter(status=PaymentStatus.PENDING).count(),
			'pagamentos_atrasados': student.payments.filter(status=PaymentStatus.OVERDUE).count(),
			'proximos_vencimentos_count': proximos_vencimentos_count,
		},
	}


__all__ = ['build_student_directory_snapshot', 'build_student_financial_snapshot', 'compute_fidalgometro_score']