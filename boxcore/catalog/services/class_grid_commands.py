"""
ARQUIVO: fachada historica dos comandos da grade de aulas.

POR QUE ELE EXISTE:
- preserva a API antiga enquanto a entrada publica real passa a morar em catalog.services.class_grid_commands.

O QUE ESTE ARQUIVO FAZ:
1. Reexporta os comandos publicos atuais da grade.

PONTOS CRITICOS:
- novos entrypoints devem preferir catalog.services.class_grid_commands ou operations.facade.class_grid.
"""

