"""
ARQUIVO: fachada publica das actions operacionais por papel.

POR QUE ELE EXISTE:
- Permite que runtime e testes dependam do app real operations sem entrar por boxcore.operations.

O QUE ESTE ARQUIVO FAZ:
1. Reexporta os handlers operacionais historicos enquanto a implementacao concreta ainda vive em boxcore.operations.actions.

PONTOS CRITICOS:
- Este arquivo estabiliza a fronteira de importacao do dominio, mas nao deve reacoplar comportamento novo ao namespace historico.
"""

from boxcore.operations.actions import (
    apply_attendance_action,
    create_technical_behavior_note,
    handle_attendance_action,
    handle_payment_enrollment_link_action,
    handle_technical_behavior_note_action,
    link_payment_to_active_enrollment,
)

__all__ = [
    'apply_attendance_action',
    'create_technical_behavior_note',
    'handle_attendance_action',
    'handle_payment_enrollment_link_action',
    'handle_technical_behavior_note_action',
    'link_payment_to_active_enrollment',
]