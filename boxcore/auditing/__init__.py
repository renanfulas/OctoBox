"""
ARQUIVO: ponto de entrada do módulo de auditoria.

POR QUE ELE EXISTE:
- Centraliza o acesso aos utilitários de auditoria do projeto.

O QUE ESTE ARQUIVO FAZ:
1. Expõe a função principal de registro de eventos.
"""

from .services import log_audit_event

__all__ = ['log_audit_event']