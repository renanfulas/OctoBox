"""
ARQUIVO: exportador legado e transitório dos modelos do boxcore.

POR QUE ELE EXISTE:
- Preserva compatibilidade com imports históricos enquanto a aplicação migra para superfícies de domínio explícitas.

O QUE ESTE ARQUIVO FAZ:
1. Reexporta models e enums históricos ainda ancorados no estado de boxcore.
2. Evita quebra imediata em imports antigos durante a transição.

PONTOS CRITICOS:
- Este arquivo não deve ser tratado como API pública principal para código novo.
- Código novo deve importar de students.models, finance.models, operations.models, auditing.models, onboarding.models ou communications.models.
- Os exports daqui só devem diminuir quando a compatibilidade histórica deixar de ser necessária.
"""

from .base import TimeStampedModel
from .audit import AuditEvent
from .communications import (
    MessageDirection,
    MessageKind,
    WhatsAppContact,
    WhatsAppContactStatus,
    WhatsAppMessageLog,
)
from .finance import (
    BillingCycle,
    Enrollment,
    EnrollmentStatus,
    MembershipPlan,
    Payment,
    PaymentMethod,
    PaymentStatus,
)
from .onboarding import IntakeSource, IntakeStatus, StudentIntake
from .operations import (
    Attendance,
    AttendanceStatus,
    BehaviorCategory,
    BehaviorNote,
    ClassSession,
    LeadImportDeclaredRange,
    LeadImportJob,
    LeadImportJobStatus,
    LeadImportProcessingMode,
    LeadImportSourceType,
    SessionStatus,
)
from .students import HealthIssueStatus, Student, StudentGender, StudentStatus

__all__ = [
    'AuditEvent',
    'Attendance',
    'AttendanceStatus',
    'BehaviorCategory',
    'BehaviorNote',
    'BillingCycle',
    'ClassSession',
    'Enrollment',
    'EnrollmentStatus',
    'IntakeSource',
    'IntakeStatus',
    'LeadImportDeclaredRange',
    'LeadImportJob',
    'LeadImportJobStatus',
    'LeadImportProcessingMode',
    'LeadImportSourceType',
    'MessageDirection',
    'MessageKind',
    'MembershipPlan',
    'Payment',
    'PaymentMethod',
    'PaymentStatus',
    'SessionStatus',
    'Student',
    'StudentGender',
    'HealthIssueStatus',
    'StudentIntake',
    'StudentStatus',
    'TimeStampedModel',
    'WhatsAppContact',
    'WhatsAppContactStatus',
    'WhatsAppMessageLog',
]
