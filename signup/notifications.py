"""
ARQUIVO: templates do email de onboarding Early Adopter.

POR QUE ELE EXISTE:
- Concentra subject/body do email transacional pos-pagamento.
- Mantem o tom de voz da marca (acolhedor, premium, direto).
- Permite trocar prosa sem precisar mexer em service layer.

O QUE ESTE ARQUIVO FAZ:
1. Gera o subject do email com nome do box.
2. Gera o body em texto plano (multi-paragrafo) com URL de ativacao.

PONTOS CRITICOS:
- Texto plano apenas — gateway (SMTP/Resend) atual nao envia HTML.
- Nao incluir credenciais ou senhas no email (a senha e criada pelo cliente no link).
- Sem caracteres acentuados no subject pra evitar problema de encoding em alguns clientes.
"""
from __future__ import annotations


def build_owner_onboarding_subject(box_name: str) -> str:
    """Subject sem acentos pra maximizar compatibilidade com clientes legacy."""
    safe_box = box_name.strip() or 'seu box'
    return f'OctoBox · Ative sua conta e configure {safe_box}'


def build_owner_onboarding_body(
    *,
    full_name: str,
    box_name: str,
    plan_label: str,
    activation_url: str,
    expires_in_days: int = 7,
) -> str:
    """Corpo do email plain-text. Linhas curtas para boa leitura em mobile."""
    return (
        f'Bem-vindo ao OctoBox, {full_name}!\n'
        '\n'
        f'Recebemos seu pagamento do plano {plan_label} para o {box_name}.\n'
        '\n'
        'Para ativar sua conta e começar a configurar o sistema, clique no link abaixo:\n'
        '\n'
        f'{activation_url}\n'
        '\n'
        f'O link expira em {expires_in_days} dias.\n'
        '\n'
        'Em até 12 horas vamos te chamar no WhatsApp para acompanhar o setup juntos.\n'
        '\n'
        'Bem-vindo entre os 20 primeiros.\n'
        '\n'
        '— Time OctoBox\n'
        'octobox@octoboxfit.com.br\n'
    )


__all__ = [
    'build_owner_onboarding_subject',
    'build_owner_onboarding_body',
]
