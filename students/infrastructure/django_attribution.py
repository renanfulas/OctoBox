"""
ARQUIVO: adapters Django da fundacao de atribuicao comercial do aluno.

POR QUE ELE EXISTE:
- separa persistencia de declaracao de origem e reconciliacao do estado resolvido.
- prepara ingestao externa sem empurrar regra para view ou frontend.
"""

from dataclasses import dataclass

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from shared_support.acquisition import normalize_acquisition_channel
from students.domain.acquisition_resolution import resolve_acquisition_resolution
from students.models import Student, StudentSourceDeclaration


@dataclass(frozen=True, slots=True)
class StudentSourceDeclarationRecord:
    declaration_id: int
    student_id: int
    resolved_acquisition_source: str
    source_confidence: str
    source_conflict_flag: bool


def get_active_student_source_declaration(student: Student) -> StudentSourceDeclaration | None:
    return student.source_declarations.filter(is_active=True).order_by('-captured_at', '-created_at').first()


def refresh_student_acquisition_resolution(
    *,
    student: Student,
    declaration: StudentSourceDeclaration | None = None,
    actor_id: int | None = None,
    commit: bool = True,
):
    active_declaration = declaration or get_active_student_source_declaration(student)
    resolution = resolve_acquisition_resolution(
        operational_source=student.acquisition_source,
        operational_detail=student.acquisition_source_detail,
        operational_method=student.source_resolution_method,
        declared_source=getattr(active_declaration, 'declared_acquisition_source', ''),
        declared_detail=getattr(active_declaration, 'declared_source_detail', ''),
    )

    update_fields = []
    field_map = {
        'resolved_acquisition_source': resolution.resolved_acquisition_source,
        'resolved_source_detail': resolution.resolved_source_detail,
        'source_confidence': resolution.source_confidence,
        'source_conflict_flag': resolution.source_conflict_flag,
        'source_resolution_method': resolution.source_resolution_method,
        'source_resolution_reason': resolution.source_resolution_reason,
    }
    for field_name, value in field_map.items():
        if getattr(student, field_name) != value:
            setattr(student, field_name, value)
            update_fields.append(field_name)

    if active_declaration is not None and not student.acquisition_source and student.source_captured_at != active_declaration.captured_at:
        student.source_captured_at = active_declaration.captured_at
        update_fields.append('source_captured_at')

    if actor_id is not None and (
        resolution.source_resolution_method == 'declared_only' or resolution.source_conflict_flag
    ) and student.source_captured_by_id != actor_id:
        student.source_captured_by_id = actor_id
        update_fields.append('source_captured_by')

    if commit and update_fields:
        student.save(update_fields=[*update_fields, 'updated_at'])

    return resolution


def record_student_source_declaration(
    *,
    student_id: int,
    declared_acquisition_source: str,
    declared_source_detail: str = '',
    declared_source_channel: str = '',
    declared_source_response_id: str = '',
    captured_at=None,
    actor_id: int | None = None,
    raw_payload: dict | None = None,
) -> StudentSourceDeclarationRecord:
    declared_acquisition_source = normalize_acquisition_channel(declared_acquisition_source)
    if not declared_acquisition_source:
        raise ValueError('declared_acquisition_source is required.')

    captured_at = captured_at or timezone.now()
    declared_source_detail = (declared_source_detail or '').strip()
    declared_source_channel = (declared_source_channel or '').strip().lower()
    declared_source_response_id = (declared_source_response_id or '').strip()
    raw_payload = raw_payload or {}

    user_model = get_user_model()
    captured_by = user_model.objects.filter(pk=actor_id).first() if actor_id is not None else None

    with transaction.atomic():
        student = Student.objects.select_for_update().get(pk=student_id)
        student.source_declarations.filter(is_active=True).update(is_active=False)
        declaration = StudentSourceDeclaration.objects.create(
            student=student,
            declared_acquisition_source=declared_acquisition_source,
            declared_source_detail=declared_source_detail,
            declared_source_channel=declared_source_channel,
            declared_source_response_id=declared_source_response_id,
            captured_at=captured_at,
            captured_by=captured_by,
            is_active=True,
            raw_payload=raw_payload,
        )
        resolution = refresh_student_acquisition_resolution(
            student=student,
            declaration=declaration,
            actor_id=actor_id,
            commit=True,
        )

    return StudentSourceDeclarationRecord(
        declaration_id=declaration.id,
        student_id=student.id,
        resolved_acquisition_source=resolution.resolved_acquisition_source,
        source_confidence=resolution.source_confidence,
        source_conflict_flag=resolution.source_conflict_flag,
    )


__all__ = [
    'StudentSourceDeclarationRecord',
    'get_active_student_source_declaration',
    'record_student_source_declaration',
    'refresh_student_acquisition_resolution',
]
