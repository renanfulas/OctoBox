"""
ARQUIVO: helper compartilhado de links outbound de WhatsApp.

POR QUE ELE EXISTE:
- Evita duplicar montagem de link externo com telefone normalizado e mensagem codificada.

O QUE ESTE ARQUIVO FAZ:
1. Normaliza o telefone de destino.
2. Codifica a mensagem em formato seguro para URL.
3. Devolve o href pronto para abrir conversa no WhatsApp.

PONTOS CRITICOS:
- Se o telefone vier vazio ou invalido, a funcao devolve string vazia para a UI degradar sem quebrar.
"""

from urllib.parse import quote

from shared_support.phone_numbers import normalize_phone_number


def build_whatsapp_message_href(*, phone, message):
    normalized_phone = normalize_phone_number(phone)
    if not normalized_phone:
        return ''

    return f'https://wa.me/{normalized_phone}?text={quote(str(message or ""))}'


__all__ = ['build_whatsapp_message_href']