"""
ARQUIVO: fachada da ação de comunicação financeira do catálogo.

POR QUE ELE EXISTE:
- Mantém a entrada histórica da UI enquanto a superfície canônica vive em catalog.services.finance_communication_actions.

O QUE ESTE ARQUIVO FAZ:
1. Reexporta a action pública atual.

PONTOS CRITICOS:
- Este arquivo não deve voltar a resolver ORM nem registrar mensagem diretamente.
"""

from catalog.services.finance_communication_actions import handle_finance_communication_action


__all__ = ['handle_finance_communication_action']