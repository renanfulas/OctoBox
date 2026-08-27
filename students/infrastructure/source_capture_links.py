"""
ARQUIVO: tokens e links seguros para captura declarada de origem do aluno.

POR QUE ELE EXISTE:
- permite coletar origem declarada fora da area autenticada sem expor ids crus.
- prepara links reutilizaveis para mensagens, automacoes e formularios leves.

Onda 6 (docs/plans/ondas-correcao-tenancy-billing-2026-08-25.md, ver ADR-014):
o token passou a carregar box_root_slug alem do student_id. Student vive em
TENANT_APP — sem o schema embutido, resolver o tenant certo pra ler o token
dependia do fallback SINGLE_ACTIVE_BOX (so funciona com 1 box ATIVO no
sistema). Campo opcional: tokens emitidos ANTES desta mudanca (ate 30 dias
em voo, ver max_age) nao tem box_root_slug — read_student_source_capture_token_payload
devolve string vazia nesse caso, e o caller decide o fallback.
"""

from dataclasses import dataclass

from django.core import signing


SOURCE_CAPTURE_SALT = 'students.source_capture'


@dataclass(frozen=True, slots=True)
class SourceCaptureTokenPayload:
    student_id: int
    box_root_slug: str = ''


def build_student_source_capture_token(*, student_id: int, box_root_slug: str = '') -> str:
    payload = {'student_id': student_id}
    if box_root_slug:
        payload['box_root_slug'] = box_root_slug
    return signing.dumps(payload, salt=SOURCE_CAPTURE_SALT)


def read_student_source_capture_token_payload(
    *, token: str, max_age: int = 60 * 60 * 24 * 30,
) -> SourceCaptureTokenPayload:
    payload = signing.loads(token, salt=SOURCE_CAPTURE_SALT, max_age=max_age)
    return SourceCaptureTokenPayload(
        student_id=int(payload['student_id']),
        box_root_slug=(payload.get('box_root_slug') or '').strip(),
    )


def read_student_source_capture_token(*, token: str, max_age: int = 60 * 60 * 24 * 30) -> int:
    """Mantido por compatibilidade — devolve só o student_id.

    Callers que precisam resolver tenant ANTES de ler o Student (caso real
    de catalog/views/student_views.py::StudentSourceCaptureView) devem usar
    read_student_source_capture_token_payload em vez desta função.
    """
    return read_student_source_capture_token_payload(token=token, max_age=max_age).student_id


__all__ = [
    'SourceCaptureTokenPayload',
    'build_student_source_capture_token',
    'read_student_source_capture_token',
    'read_student_source_capture_token_payload',
]
