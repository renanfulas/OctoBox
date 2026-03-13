"""
ARQUIVO: resultados das acoes do workspace operacional.

POR QUE ELE EXISTE:
- devolve saidas pequenas para as fachadas historicas e para a camada HTTP.

O QUE ESTE ARQUIVO FAZ:
1. representa o vinculo de pagamento com matricula.
2. representa ocorrencia tecnica criada.
3. representa mudanca de presenca aplicada.

PONTOS CRITICOS:
- os resultados nao devem carregar models ORM diretamente.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LinkedPaymentEnrollmentResult:
    payment_id: int
    enrollment_id: int


@dataclass(frozen=True, slots=True)
class TechnicalBehaviorNoteResult:
    note_id: int


@dataclass(frozen=True, slots=True)
class AttendanceActionResult:
    attendance_id: int
    status: str


__all__ = ['AttendanceActionResult', 'LinkedPaymentEnrollmentResult', 'TechnicalBehaviorNoteResult']