"""
ARQUIVO: facade publica da atribuicao comercial do aluno.

POR QUE ELE EXISTE:
- oferece um ponto de entrada pequeno para ingestao declarada e reconciliacao.
- prepara integracoes externas sem expor ORM ou adapters Django para fora.
"""

from dataclasses import dataclass
from datetime import datetime

from students.infrastructure.django_attribution import record_student_source_declaration


@dataclass(frozen=True, slots=True)
class StudentSourceDeclarationFacadeResult:
    declaration_id: int
    student_id: int
    resolved_acquisition_source: str
    source_confidence: str
    source_conflict_flag: bool


def run_student_source_declaration_record(
    *,
    student_id: int,
    declared_acquisition_source: str,
    declared_source_detail: str = '',
    declared_source_channel: str = '',
    declared_source_response_id: str = '',
    captured_at: datetime | None = None,
    actor_id: int | None = None,
    raw_payload: dict | None = None,
) -> StudentSourceDeclarationFacadeResult:
    result = record_student_source_declaration(
        student_id=student_id,
        declared_acquisition_source=declared_acquisition_source,
        declared_source_detail=declared_source_detail,
        declared_source_channel=declared_source_channel,
        declared_source_response_id=declared_source_response_id,
        captured_at=captured_at,
        actor_id=actor_id,
        raw_payload=raw_payload,
    )
    return StudentSourceDeclarationFacadeResult(
        declaration_id=result.declaration_id,
        student_id=result.student_id,
        resolved_acquisition_source=result.resolved_acquisition_source,
        source_confidence=result.source_confidence,
        source_conflict_flag=result.source_conflict_flag,
    )


__all__ = ['StudentSourceDeclarationFacadeResult', 'run_student_source_declaration_record']
