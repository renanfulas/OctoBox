"""
ARQUIVO: exportador central dos modelos do boxcore.

POR QUE ELE EXISTE:
- Permite importar modelos a partir de um único lugar, sem lembrar o arquivo interno de cada domínio.

O QUE ESTE ARQUIVO FAZ:
1. Reexporta modelos de alunos, financeiro, operação e auditoria.
2. Deixa imports mais limpos no resto do projeto.

PONTOS CRITICOS:
- Se um modelo deixar de ser exportado aqui, imports em admin, views e testes podem quebrar.
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