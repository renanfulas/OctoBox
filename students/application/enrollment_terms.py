"""
ARQUIVO: regras puras de matrícula do aluno.

POR QUE ELE EXISTE:
- Centraliza decisões de mudança comercial sem depender de ORM ou da camada web.

O QUE ESTE ARQUIVO FAZ:
1. Classifica mudança de plano em upgrade, downgrade ou troca.

PONTOS CRITICOS:
- Esta regra impacta auditoria comercial e mensagens operacionais.
"""


def describe_plan_change(*, previous_price, selected_price):
    if selected_price > previous_price:
        return 'upgrade'
    if selected_price < previous_price:
        return 'downgrade'
    return 'troca de plano'


__all__ = ['describe_plan_change']