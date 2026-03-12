"""
ARQUIVO: estrutura base dos papeis de acesso.

POR QUE ELE EXISTE:
- Define o formato padrao que todo papel do sistema precisa seguir.

O QUE ESTE ARQUIVO FAZ:
1. Cria a estrutura RoleDefinition.
2. Padroniza label, resumo e capacidades dos papeis.

PONTOS CRITICOS:
- Alterar a estrutura do dataclass impacta owner, dev, manager, coach e telas de acesso.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class RoleDefinition:
    slug: str
    label: str
    summary: str
    capabilities: tuple[str, ...]
