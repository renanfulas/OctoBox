"""
ARQUIVO: regras puras de conversão de intake.

POR QUE ELE EXISTE:
- Centraliza a anotação padrão de conversão sem depender de ORM ou da camada web.

O QUE ESTE ARQUIVO FAZ:
1. Define a observação padrão de conversão do lead.

PONTOS CRITICOS:
- Mudanças aqui afetam o histórico comercial do intake convertido.
"""

DEFAULT_INTAKE_CONVERSION_NOTE = 'Convertido em aluno definitivo pela tela leve.'


__all__ = ['DEFAULT_INTAKE_CONVERSION_NOTE']
