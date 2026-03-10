"""
ARQUIVO: registrador central do admin do boxcore.

POR QUE ELE EXISTE:
- Garante que as configurações de admin sejam carregadas quando o app sobe.

O QUE ESTE ARQUIVO FAZ:
1. Importa os módulos de admin por assunto.
2. Ativa o registro de telas do backoffice.

PONTOS CRITICOS:
- Se um import sair daqui, a tela correspondente pode desaparecer do admin.
"""

from .audit import AuditEventAdmin
from .finance import EnrollmentAdmin, MembershipPlanAdmin, PaymentAdmin
from .onboarding import StudentIntakeAdmin, WhatsAppContactAdmin, WhatsAppMessageLogAdmin
from .operations import AttendanceAdmin, BehaviorNoteAdmin, ClassSessionAdmin
from .students import StudentAdmin

__all__ = [
    'AuditEventAdmin',
    'AttendanceAdmin',
    'BehaviorNoteAdmin',
    'ClassSessionAdmin',
    'EnrollmentAdmin',
    'MembershipPlanAdmin',
    'PaymentAdmin',
    'StudentIntakeAdmin',
    'StudentAdmin',
    'WhatsAppContactAdmin',
    'WhatsAppMessageLogAdmin',
]