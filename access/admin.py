"""
ARQUIVO: politicas centrais de acesso ao Django admin.

POR QUE ELE EXISTE:
- impede que o admin vire rota operacional lateral para papeis que deveriam agir pela fachada principal.
- centraliza as URLs reais do admin para nao depender de caminhos hardcoded.

O QUE ESTE ARQUIVO FAZ:
1. define quem pode acessar o admin.
2. resolve URLs reais do admin com fallback seguro.
3. instala o gate principal no admin site do Django.

PONTOS CRITICOS:
- qualquer relaxamento aqui reabre a superficie tecnica do sistema.
- as URLs do admin precisam continuar corretas mesmo quando o caminho publico mudar.
"""

from django.contrib import admin
from django.urls import NoReverseMatch, reverse

from access.roles import ROLE_DEV, ROLE_OWNER, get_user_role


ADMIN_ALLOWED_ROLES = (ROLE_OWNER, ROLE_DEV)


def user_can_access_admin(user):
    if not getattr(user, 'is_authenticated', False):
        return False
    if not getattr(user, 'is_active', False):
        return False
    if not getattr(user, 'is_staff', False):
        return False
    if getattr(user, 'is_superuser', False):
        return True

    role = get_user_role(user)
    return getattr(role, 'slug', '') in ADMIN_ALLOWED_ROLES


def admin_url(name, *args, fallback=None):
    try:
        return reverse(name, args=args or None)
    except NoReverseMatch:
        return fallback


def admin_index_url():
    return admin_url('admin:index', fallback='/')


def admin_changelist_url(app_label, model_name):
    return admin_url(f'admin:{app_label}_{model_name}_changelist', fallback=admin_index_url())


def install_admin_site_gate():
    admin.site.has_permission = lambda request: user_can_access_admin(request.user)


__all__ = [
    'ADMIN_ALLOWED_ROLES',
    'admin_changelist_url',
    'admin_index_url',
    'admin_url',
    'install_admin_site_gate',
    'user_can_access_admin',
]