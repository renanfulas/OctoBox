"""Fachada publica dos workflows de agenda do catalogo."""

from operations.facade import run_class_schedule_create


def run_class_schedule_create_workflow(*, actor, form):
	result = run_class_schedule_create(actor=actor, form=form)
	return {
		'created_sessions': result.created_sessions,
		'skipped_slots': result.skipped_slots,
	}


__all__ = ['run_class_schedule_create_workflow']