"""
ARQUIVO: fachada das actions de pagamento do aluno.

POR QUE ELE EXISTE:
- Mantem a interface publica atual enquanto a superfície canônica vive em catalog.services.student_payment_actions.

O QUE ESTE ARQUIVO FAZ:
1. Reexporta a action pública atual.

PONTOS CRITICOS:
- Este arquivo nao deve voltar a concentrar auditoria, ORM ou transacao.
"""

from catalog.services.student_payment_actions import handle_student_payment_action


__all__ = ['handle_student_payment_action']