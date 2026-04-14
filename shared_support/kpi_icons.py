"""
ARQUIVO: icones compartilhados dos KPI cards.

POR QUE ELE EXISTE:
- padroniza a familia visual dos SVGs usados nos KPI de alunos, entradas e financeiro.
- evita que cada dominio mantenha um dialeto proprio de icones.
"""


_KPI_ICONS = frozenset(
    (
        'active',
        'alert',
        'trend',
        'inactive',
        'queue',
        'conversation',
        'today',
        'owners',
        'portfolio',
        'filters',
    )
)


def build_kpi_icon(name):
    if name not in _KPI_ICONS:
        return ''
    return name


__all__ = ['build_kpi_icon']
