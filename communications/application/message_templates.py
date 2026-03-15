"""
ARQUIVO: templates puros de mensagem operacional.

POR QUE ELE EXISTE:
- Centraliza o texto comercial sugerido sem depender de ORM ou services legados.

O QUE ESTE ARQUIVO FAZ:
1. Gera mensagem de vencimento.
2. Gera mensagem de atraso.
3. Gera mensagem de reativação.

PONTOS CRITICOS:
- Mudanças aqui alteram diretamente a comunicação operacional sugerida para o time.
"""


def build_operational_message_body(*, action_kind, first_name, payment_due_date=None, payment_amount=None, plan_name=None):
    if action_kind == 'upcoming':
        return (
            f'Oi, {first_name}. Seu pagamento do box vence em '
            f'{payment_due_date:%d/%m/%Y}, no valor de R$ {payment_amount}. Se quiser, ja te ajudamos por aqui.'
        )
    if action_kind == 'overdue':
        return (
            f'Oi, {first_name}. Vimos um pagamento do box em aberto, vencido em '
            f'{payment_due_date:%d/%m/%Y}, no valor de R$ {payment_amount}. Se quiser regularizar, te atendemos por aqui.'
        )
    return (
        f'Oi, {first_name}. Sentimos sua falta no box. Se fizer sentido retomar, conseguimos te ajudar '
        f'a reativar o plano {plan_name} com a melhor configuração para voltar ao ritmo.'
    )


__all__ = ['build_operational_message_body']