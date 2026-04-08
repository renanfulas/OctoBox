"""Fachada publica dos workflows rapidos de aluno do catalogo."""

from communications.models import StudentIntake
from finance.models import Enrollment, Payment
from shared_support.manager_event_stream import publish_manager_stream_event
from shared_support.student_event_stream import publish_student_stream_event
from shared_support.student_snapshot_versions import build_profile_version, build_student_snapshot_version
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
	workflow_result = _build_legacy_workflow_result(result)
	publish_student_stream_event(
		student_id=workflow_result['student'].id,
		event_type='student.profile.updated',
		snapshot_version=build_student_snapshot_version(student=workflow_result['student']),
		profile_version=build_profile_version(workflow_result['student']),
		meta={
			'action': 'create',
			'changed_fields': sorted(form.cleaned_data.keys()),
		},
	)
	publish_manager_stream_event(
		event_type='student.profile.updated',
		meta={
			'student_id': workflow_result['student'].id,
			'action': 'create',
			'changed_fields': sorted(form.cleaned_data.keys()),
		},
	)
	if workflow_result['intake'] is not None:
		publish_manager_stream_event(
			event_type='intake.updated',
			meta={
				'intake_id': workflow_result['intake'].id,
				'action': 'linked-to-student',
				'status': workflow_result['intake'].status,
				'student_id': workflow_result['student'].id,
			},
		)
	return workflow_result


def run_student_express_create_workflow(*, actor, form):
	from django.utils import timezone
	
	cleaned_data = form.cleaned_data.copy()
	# Preenchimento padrao rapido
	cleaned_data['status'] = 'active'
	cleaned_data['enrollment_status'] = 'pending'
	cleaned_data['payment_method'] = 'pix'
	cleaned_data['confirm_payment_now'] = False
	cleaned_data['payment_due_date'] = timezone.localdate()
	cleaned_data['billing_strategy'] = 'single'
	cleaned_data['installment_total'] = 1
	cleaned_data['recurrence_cycles'] = 1
	
	result = run_student_quick_create(
		actor_id=getattr(actor, 'id', None),
		cleaned_data=cleaned_data,
		selected_intake_id=None,
	)
	workflow_result = _build_legacy_workflow_result(result)
	publish_student_stream_event(
		student_id=workflow_result['student'].id,
		event_type='student.profile.updated',
		snapshot_version=build_student_snapshot_version(student=workflow_result['student']),
		profile_version=build_profile_version(workflow_result['student']),
		meta={
			'action': 'express-create',
			'changed_fields': sorted(cleaned_data.keys()),
		},
	)
	publish_manager_stream_event(
		event_type='student.profile.updated',
		meta={
			'student_id': workflow_result['student'].id,
			'action': 'express-create',
			'changed_fields': sorted(cleaned_data.keys()),
		},
	)
	return workflow_result


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
	workflow_result = _build_legacy_workflow_result(result)
	publish_student_stream_event(
		student_id=workflow_result['student'].id,
		event_type='student.profile.updated',
		snapshot_version=build_student_snapshot_version(student=workflow_result['student']),
		profile_version=build_profile_version(workflow_result['student']),
		meta={
			'action': 'update',
			'changed_fields': sorted(changed_fields),
		},
	)
	publish_manager_stream_event(
		event_type='student.profile.updated',
		meta={
			'student_id': workflow_result['student'].id,
			'action': 'update',
			'changed_fields': sorted(changed_fields),
		},
	)
	if workflow_result['intake'] is not None:
		publish_manager_stream_event(
			event_type='intake.updated',
			meta={
				'intake_id': workflow_result['intake'].id,
				'action': 'linked-to-student',
				'status': workflow_result['intake'].status,
				'student_id': workflow_result['student'].id,
			},
		)
	if workflow_result['enrollment_sync']['enrollment'] is not None:
		publish_manager_stream_event(
			event_type='student.enrollment.updated',
			meta={
				'student_id': workflow_result['student'].id,
				'enrollment_id': workflow_result['enrollment_sync']['enrollment'].id,
				'action': 'sync-after-profile',
			},
		)
	return workflow_result


__all__ = [
	'build_student_flow_payload',
	'build_student_workflow_payload',
	'run_student_express_create_workflow',
	'run_student_quick_create_workflow',
	'run_student_quick_update_workflow',
]
