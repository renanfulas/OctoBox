"""
ARQUIVO: fachada historica do workflow recorrente da grade.

POR QUE ELE EXISTE:
- preserva a API antiga enquanto a entrada publica real passa a morar em catalog.services.class_schedule_workflows.

O QUE ESTE ARQUIVO FAZ:
1. Reexporta o workflow publico atual da grade.

PONTOS CRITICOS:
- novos entrypoints devem preferir catalog.services.class_schedule_workflows ou operations.facade.class_grid diretamente.
"""

