"""
ARQUIVO: fachada de compatibilidade para regras puras de matricula.

POR QUE ELE EXISTE:
- Preserva imports historicos enquanto a regra comercial migra para a camada de dominio explicita.

O QUE ESTE ARQUIVO FAZ:
1. Reexporta a classificacao pura de mudanca de plano.

PONTOS CRITICOS:
- Nova regra deve nascer em students.domain, nao aqui.
"""

from students.domain import describe_plan_change

__all__ = ['describe_plan_change']