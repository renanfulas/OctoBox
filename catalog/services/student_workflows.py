"""Fachada publica dos workflows rapidos de aluno do catalogo."""

from communications.models import StudentIntake
from finance.models import Enrollment, Payment
from students.facade import run_student_quick_create, run_student_quick_update
from students.models import Student


def build_student_workflow_payload(*, student, form):
	selected_plan = form.cleaned_data.get('selected_plan')
	return {
		'student': student,
		'selected_plan': selected_plan,
		'enrollment_status': form.cleaned_data.get('enrollment_status'),
		'due_date': form.cleaned_data.get('payment_due_date'),
		'payment_method': form.cleaned_data.get('payment_method'),
		'confirm_payment_now': bool(form.cleaned_data.get('confirm_payment_now')),
		'payment_reference': form.cleaned_data.get('payment_reference') or '',
		'billing_strategy': form.cleaned_data.get('billing_strategy') or 'single',
		'installment_total': form.cleaned_data.get('installment_total') or 1,
		'recurrence_cycles': form.cleaned_data.get('recurrence_cycles') or 1,
		'initial_payment_amount': form.cleaned_data.get('initial_payment_amount'),
	}


build_student_flow_payload = build_student_workflow_payload


def _build_legacy_workflow_result(result):
	student = Student.objects.get(pk=result.student_id)
	enrollment = Enrollment.objects.filter(pk=result.enrollment_id).first()
	payment = Payment.objects.filter(pk=result.payment_id).first()
	intake = StudentIntake.objects.filter(pk=result.intake_id).first()
	return {
		'student': student,
		'enrollment_sync': {
			'enrollment': enrollment,
			'payment': payment,
			'movement': result.movement,
		},
		'intake': intake,
	}


def run_student_quick_create_workflow(*, actor, form, selected_intake=None):
	result = run_student_quick_create(
		actor_id=getattr(actor, 'id', None),
		cleaned_data=form.cleaned_data,
		selected_intake_id=getattr(selected_intake, 'id', None),
	)
	return _build_legacy_workflow_result(result)


def run_student_quick_update_workflow(*, actor, form, changed_fields, selected_intake=None):
	student_id = getattr(getattr(form, 'instance', None), 'id', None)
	if student_id is None and hasattr(form, 'save'):
		student_id = getattr(form.save(), 'id', None)

	result = run_student_quick_update(
		actor_id=getattr(actor, 'id', None),
		cleaned_data=form.cleaned_data,
		student_id=student_id,
		selected_intake_id=getattr(selected_intake, 'id', None),
		changed_fields=tuple(changed_fields),
	)
	return _build_legacy_workflow_result(result)


__all__ = [
	'build_student_flow_payload',
	'build_student_workflow_payload',
	'run_student_quick_create_workflow',
	'run_student_quick_update_workflow',
]