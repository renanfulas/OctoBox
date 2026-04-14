"""
ARQUIVO: icones compartilhados dos KPI cards.

POR QUE ELE EXISTE:
- padroniza a familia visual dos SVGs usados nos KPI de alunos, entradas e financeiro.
- evita que cada dominio mantenha um dialeto proprio de icones.
"""

from django.utils.safestring import SafeString


_KPI_ICONS = {
    'active': (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
        'aria-hidden="true"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>'
        '<polyline points="22 4 12 14.01 9 11.01"/></svg>'
    ),
    'alert': (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
        'aria-hidden="true"><circle cx="12" cy="12" r="10"/>'
        '<line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>'
    ),
    'trend': (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
        'aria-hidden="true"><path d="M3 17l6-6 4 4 8-8"/><path d="M14 7h7v7"/></svg>'
    ),
    'inactive': (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
        'aria-hidden="true"><circle cx="12" cy="12" r="10"/>'
        '<line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>'
    ),
    'queue': (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
        'aria-hidden="true"><path d="M3 12h7"/><path d="M3 6h11"/><path d="M3 18h5"/>'
        '<path d="m15 15 3 3 3-3"/><path d="M18 6v12"/></svg>'
    ),
    'conversation': (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
        'aria-hidden="true"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>'
    ),
    'today': (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
        'aria-hidden="true"><path d="M8 2v4"/><path d="M16 2v4"/><rect x="3" y="4" width="18" height="18" rx="2"/>'
        '<path d="M3 10h18"/><path d="M8 14h.01"/><path d="M12 14h.01"/><path d="M16 14h.01"/></svg>'
    ),
    'owners': (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
        'aria-hidden="true"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/>'
        '<circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/>'
        '<path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>'
    ),
    'portfolio': (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
        'aria-hidden="true"><rect x="2" y="7" width="20" height="14" rx="2"/>'
        '<path d="M16 3v4"/><path d="M8 3v4"/><path d="M2 11h20"/></svg>'
    ),
    'filters': (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
        'aria-hidden="true"><path d="M4 6h16"/><path d="M7 12h10"/><path d="M10 18h4"/></svg>'
    ),
}


def build_kpi_icon(name):
    icon = _KPI_ICONS.get(name, '')
    if not icon:
        return ''
    return SafeString(icon)


__all__ = ['build_kpi_icon']
