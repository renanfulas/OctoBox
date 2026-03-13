"""Fachada publica das actions de matricula do catalogo."""

from boxcore.catalog.services.student_enrollment_actions import handle_student_enrollment_action

__all__ = ['handle_student_enrollment_action']