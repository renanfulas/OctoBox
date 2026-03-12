"""
ARQUIVO: resultados explicitos dos workflows leves de plano.

POR QUE ELE EXISTE:
- Evita expor ModelForm ou retorno solto como contrato da camada de aplicacao.

O QUE ESTE ARQUIVO FAZ:
1. Define o retorno estavel da escrita de plano.

PONTOS CRITICOS:
- O resultado precisa continuar simples para web e testes atuais.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MembershipPlanRecord:
    id: int
    name: str


__all__ = ['MembershipPlanRecord']