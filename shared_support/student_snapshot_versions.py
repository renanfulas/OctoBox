"""
ARQUIVO: versoes canonicas de snapshot da ficha do aluno.

POR QUE ELE EXISTE:
- centraliza uma noção leve e consistente de versao para snapshot, eventos SSE
  e conflito de escrita da ficha.

O QUE ESTE ARQUIVO FAZ:
1. serializa timestamps em formato estavel.
2. calcula a versao do perfil.
3. calcula a versao agregada da ficha (perfil + financeiro principal).

PONTOS CRITICOS:
- esta versao e temporal e suficiente para conciliacao operacional do drawer.
- nao substitui locks; ela complementa a concorrencia otimista.
"""

from __future__ import annotations

from datetime import datetime


def serialize_version_value(value) -> str:
    if not value:
        return ''
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def build_profile_version(student) -> str:
    return serialize_version_value(getattr(student, 'updated_at', None))


def build_student_snapshot_version(*, student, latest_enrollment=None, latest_payment=None) -> str:
    candidates = [
        getattr(student, 'updated_at', None),
        getattr(latest_enrollment, 'updated_at', None) if latest_enrollment else None,
        getattr(latest_payment, 'updated_at', None) if latest_payment else None,
    ]
    candidates = [candidate for candidate in candidates if candidate is not None]
    if not candidates:
        return ''
    return serialize_version_value(max(candidates))


__all__ = [
    'build_profile_version',
    'build_student_snapshot_version',
    'serialize_version_value',
]
