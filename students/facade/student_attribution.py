"""
ARQUIVO: facade publica da atribuicao comercial do aluno.

POR QUE ELE EXISTE:
- oferece um ponto de entrada pequeno para ingestao declarada e reconciliacao.
- prepara integracoes externas sem expor ORM ou adapters Django para fora.
"""

from dataclasses import dataclass
from datetime import datetime

from students.infrastructure.django_attribution import record_student_source_declaration
from students.infrastructure.source_capture_links import (
    SourceCaptureTokenPayload,
    build_student_source_capture_token,
    read_student_source_capture_token,
    read_student_source_capture_token_payload,
)


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


def run_student_source_capture_token_build(*, student_id: int, box_root_slug: str = '') -> str:
    return build_student_source_capture_token(student_id=student_id, box_root_slug=box_root_slug)


def run_student_source_capture_token_read(*, token: str, max_age: int = 60 * 60 * 24 * 30) -> int:
    return read_student_source_capture_token(token=token, max_age=max_age)


def run_student_source_capture_token_read_payload(
    *, token: str, max_age: int = 60 * 60 * 24 * 30,
) -> SourceCaptureTokenPayload:
    return read_student_source_capture_token_payload(token=token, max_age=max_age)


__all__ = [
    'StudentSourceDeclarationFacadeResult',
    'SourceCaptureTokenPayload',
    'run_student_source_capture_token_build',
    'run_student_source_capture_token_read',
    'run_student_source_capture_token_read_payload',
    'run_student_source_declaration_record',
]
