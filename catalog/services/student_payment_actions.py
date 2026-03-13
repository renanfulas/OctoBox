"""Fachada publica das actions de pagamento do catalogo."""

from boxcore.catalog.services.student_payment_actions import handle_student_payment_action

__all__ = ['handle_student_payment_action']