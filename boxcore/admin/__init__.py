"""
ARQUIVO: agregador legado do admin dentro de boxcore.

POR QUE ELE EXISTE:
- Mantem a descoberta historica do admin funcionando enquanto os registros reais vivem nos apps de dominio.

O QUE ESTE ARQUIVO FAZ:
1. Importa as fachadas legadas do admin por assunto.
2. Preserva compatibilidade com o namespace historico do app.

PONTOS CRITICOS:
- Registros novos devem nascer nos apps reais, nao voltar para boxcore.
"""

from .audit import AuditEventAdmin
from .finance import EnrollmentAdmin, MembershipPlanAdmin, PaymentAdmin
from .onboarding import StudentIntakeAdmin, WhatsAppContactAdmin, WhatsAppMessageLogAdmin
from .operations import AttendanceAdmin, BehaviorNoteAdmin, ClassSessionAdmin, LeadImportJobAdmin
from .students import StudentAdmin

__all__ = [
    'AuditEventAdmin',
    'AttendanceAdmin',
    'BehaviorNoteAdmin',
    'ClassSessionAdmin',
    'EnrollmentAdmin',
    'LeadImportJobAdmin',
    'MembershipPlanAdmin',
    'PaymentAdmin',
    'StudentIntakeAdmin',
    'StudentAdmin',
    'WhatsAppContactAdmin',
    'WhatsAppMessageLogAdmin',
]
