"""
ARQUIVO: fachada Django do fluxo rapido de aluno.

POR QUE ELE EXISTE:
- Mantem a interface publica atual do catalogo enquanto a superfície canônica vive em catalog.services.student_workflows.

O QUE ESTE ARQUIVO FAZ:
1. Reexporta os workflows públicos atuais do aluno.

PONTOS CRITICOS:
- Este arquivo nao deve voltar a concentrar regra de negocio do fluxo principal.
"""

from catalog.services.student_workflows import (
    build_student_flow_payload,
    build_student_workflow_payload,
    run_student_quick_create_workflow,
    run_student_quick_update_workflow,
)


__all__ = [
    'build_student_flow_payload',
    'build_student_workflow_payload',
    'run_student_quick_create_workflow',
    'run_student_quick_update_workflow',
]