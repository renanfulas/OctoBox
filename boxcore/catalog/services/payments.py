"""
ARQUIVO: fachada do motor de cobrança do catálogo.

POR QUE ELE EXISTE:
- Mantem a interface interna historica enquanto a superfície canônica vive em catalog.services.payments.

O QUE ESTE ARQUIVO FAZ:
1. Reexporta os helpers públicos atuais de pagamento.

PONTOS CRITICOS:
- Este arquivo nao deve voltar a concentrar ORM nem regra de calculo financeiro.
"""

from catalog.services.payments import advance_due_date, create_payment_schedule, regenerate_payment, shift_month