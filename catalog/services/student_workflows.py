"""Fachada publica dos workflows rapidos de aluno do catalogo."""

from boxcore.catalog.services.student_workflows import run_student_quick_create_workflow, run_student_quick_update_workflow

__all__ = ['run_student_quick_create_workflow', 'run_student_quick_update_workflow']