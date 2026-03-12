"""
ARQUIVO: normalizacao de telefones e canais.

POR QUE ELE EXISTE:
- Garante uma representacao previsivel do telefone antes de cruzar aluno, intake e contato de WhatsApp.

O QUE ESTE ARQUIVO FAZ:
1. Remove formatacao visual do telefone.
2. Mantem apenas digitos para comparacao e deduplicacao.
3. Centraliza a regra minima atual de identidade de canal.

PONTOS CRITICOS:
- Mudancas aqui afetam deduplicacao, importacao e reconciliacao de contatos.
"""


def normalize_phone_number(raw_value):
    digits = ''.join(character for character in str(raw_value or '') if character.isdigit())
    return digits


def build_phone_match_candidates(raw_value):
    digits = normalize_phone_number(raw_value)
    if not digits:
        return []

    candidates = {digits}
    if digits.startswith('55') and len(digits) > 11:
        candidates.add(digits[2:])
    elif len(digits) in (10, 11):
        candidates.add(f'55{digits}')

    return list(candidates)