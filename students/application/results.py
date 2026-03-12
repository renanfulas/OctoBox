"""
ARQUIVO: resultados explicitos do fluxo rapido de aluno.

POR QUE ELE EXISTE:
- Evita que o caso de uso devolva models ORM ou dicionarios soltos como contrato publico.

O QUE ESTE ARQUIVO FAZ:
1. Define o retorno do write principal do aluno.
2. Define o retorno da sincronizacao comercial.
3. Define o resultado final do caso de uso.

PONTOS CRITICOS:
- Os resultados precisam ser estaveis para web, API e jobs reutilizarem a mesma logica.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class StudentRecord:
    id: int
    full_name: str


@dataclass(frozen=True, slots=True)
class EnrollmentSyncRecord:
    enrollment_id: int | None
    payment_id: int | None
    movement: str


@dataclass(frozen=True, slots=True)
class StudentQuickResult:
    student: StudentRecord
    enrollment_sync: EnrollmentSyncRecord
    intake_id: int | None = None
    changed_fields: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class StudentPaymentActionResult:
    student_id: int
    payment_id: int | None
    action: str


@dataclass(frozen=True, slots=True)
class StudentEnrollmentActionResult:
    student_id: int
    enrollment_id: int | None
    action: str


@dataclass(frozen=True, slots=True)
class StudentPaymentScheduleResult:
    student_id: int
    payment_id: int | None
    billing_group: str
    created_count: int


@dataclass(frozen=True, slots=True)
class StudentPaymentRegenerationResult:
    student_id: int
    payment_id: int | None
    enrollment_id: int | None


__all__ = [
    'EnrollmentSyncRecord',
    'StudentEnrollmentActionResult',
    'StudentPaymentActionResult',
    'StudentPaymentRegenerationResult',
    'StudentPaymentScheduleResult',
    'StudentQuickResult',
    'StudentRecord',
]
