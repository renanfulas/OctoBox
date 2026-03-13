"""
ARQUIVO: fachada historica do workflow recorrente da grade.

POR QUE ELE EXISTE:
- preserva a API antiga enquanto a entrada publica real passa a morar em operations.facade.class_grid.

O QUE ESTE ARQUIVO FAZ:
1. encaminha a criacao recorrente para a facade publica de class grid.
2. adapta o resultado novo para o formato historico esperado por chamadores legados.

PONTOS CRITICOS:
- novos entrypoints devem preferir operations.facade.class_grid diretamente.
"""

from operations.facade import run_class_schedule_create


def run_class_schedule_create_workflow(*, actor, form):
    result = run_class_schedule_create(actor=actor, form=form)
    return {
        'created_sessions': result.created_sessions,
        'skipped_slots': result.skipped_slots,
    }