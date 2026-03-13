"""
ARQUIVO: normalizacao neutra de telefones e candidatos de reconciliacao.

POR QUE ELE EXISTE:
- Move a regra operacional de telefone para fora do namespace historico boxcore sem alterar comportamento.

O QUE ESTE ARQUIVO FAZ:
1. Normaliza telefones para comparacao e deduplicacao.
2. Gera candidatos com e sem prefixo 55 para reconciliacao gradual.

PONTOS CRITICOS:
- Mudancas aqui afetam importacao, matching de intake e identidade de canal.
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


__all__ = ['build_phone_match_candidates', 'normalize_phone_number']