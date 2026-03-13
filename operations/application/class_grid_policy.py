"""
ARQUIVO: fachada de compatibilidade da policy operacional da grade.

POR QUE ELE EXISTE:
- preserva imports historicos enquanto a regra real de sessao mora no dominio puro de operations.

O QUE ESTE ARQUIVO FAZ:
1. reexporta a policy publica da grade.
2. adapta o model historico para a assinatura pura baseada em primitivas.

PONTOS CRITICOS:
- novos chamadores devem preferir passar primitivas direto para operations.domain.
"""

from operations.domain import ClassGridSessionPolicy, build_class_grid_session_policy as build_domain_policy


def build_class_grid_session_policy(session):
    return build_domain_policy(
        initial_status=session.status,
        has_attendance=session.attendances.exists(),
    )


__all__ = ['ClassGridSessionPolicy', 'build_class_grid_session_policy']