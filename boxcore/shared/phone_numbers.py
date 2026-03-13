"""
ARQUIVO: fachada legada da normalizacao de telefones dentro de boxcore.

POR QUE ELE EXISTE:
- Mantem compatibilidade com imports antigos enquanto a implementacao real vive em shared_support.phone_numbers.

O QUE ESTE ARQUIVO FAZ:
1. Reexporta os helpers de telefone usados no runtime atual.

PONTOS CRITICOS:
- Este arquivo nao deve voltar a concentrar implementacao nova.
"""

from shared_support.phone_numbers import build_phone_match_candidates, normalize_phone_number


__all__ = ['build_phone_match_candidates', 'normalize_phone_number']