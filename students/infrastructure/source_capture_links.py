"""
ARQUIVO: tokens e links seguros para captura declarada de origem do aluno.

POR QUE ELE EXISTE:
- permite coletar origem declarada fora da area autenticada sem expor ids crus.
- prepara links reutilizaveis para mensagens, automacoes e formularios leves.
"""

from django.core import signing


SOURCE_CAPTURE_SALT = 'students.source_capture'


def build_student_source_capture_token(*, student_id: int) -> str:
    return signing.dumps({'student_id': student_id}, salt=SOURCE_CAPTURE_SALT)


def read_student_source_capture_token(*, token: str, max_age: int = 60 * 60 * 24 * 30) -> int:
    payload = signing.loads(token, salt=SOURCE_CAPTURE_SALT, max_age=max_age)
    return int(payload['student_id'])


__all__ = ['build_student_source_capture_token', 'read_student_source_capture_token']
