"""
ARQUIVO: handlers compativeis das acoes operacionais por papel.

POR QUE ELE EXISTE:
- mantem imports historicos funcionando enquanto a implementacao canonica vive em operations.actions.

O QUE ESTE ARQUIVO FAZ:
1. reexporta os handlers publicos atuais de operations.actions.

PONTOS CRITICOS:
- qualquer renomeacao aqui pode quebrar chamadas legadas ou testes antigos.
"""

from operations.actions import (
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