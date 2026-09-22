"""
ARQUIVO: login proprio da area interna do Curva (Renan e Giovanna).

POR QUE ELE EXISTE:
- public_workouts nao e' um produto multi-tenant do OctoBox (sem Box, sem
  Membership) — as duas unicas contas que precisam das telas internas do
  corredor nao cabem no sistema de papeis do OctoBox (access/roles/),
  entao nao usam auth.User nem RoleRequiredMixin. Credenciais vem de
  PUBLIC_WORKOUT_STAFF_CREDENTIALS (config/settings/base.py).

PONTOS CRITICOS:
- Senha nunca em texto puro em lugar nenhum (config, log, sessao) — so' o
  hash gerado com django.contrib.auth.hashers.make_password.
- Sessao guarda so' o username autenticado, nunca senha nem hash.
- POST em /login/... ja' ganha rate limit automatico do
  RequestSecurityMiddleware (scope 'login', por prefixo de path,
  shared_support/security/__init__.py) — sem throttle proprio aqui.
- authenticate_staff roda check_password mesmo pra usuario inexistente
  (contra um hash valido fixo) pra nao vazar por timing quais usernames
  existem na config.
"""

from __future__ import annotations

from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.shortcuts import redirect
from django.urls import reverse

SESSION_KEY = 'curva_staff_username'

# Hash valido e fixo (nunca comparado de verdade contra credencial real) —
# so' pra manter o tempo de resposta igual quando o username nao existe.
_DUMMY_HASH = make_password('curva-staff-auth-timing-safety-dummy')


def authenticate_staff(username: str, password: str) -> str | None:
    """Devolve o username normalizado se as credenciais baterem, senao None."""
    credentials = getattr(settings, 'PUBLIC_WORKOUT_STAFF_CREDENTIALS', {}) or {}
    normalized = (username or '').strip().lower()
    password_hash = credentials.get(normalized, _DUMMY_HASH)
    if check_password(password or '', password_hash) and normalized in credentials:
        return normalized
    return None


def is_staff_authenticated(request) -> bool:
    username = request.session.get(SESSION_KEY)
    if not username:
        return False
    credentials = getattr(settings, 'PUBLIC_WORKOUT_STAFF_CREDENTIALS', {}) or {}
    # Revalida contra a config atual: credencial removida/trocada depois
    # do login invalida a sessao velha na proxima requisicao.
    return username in credentials


class CurvaStaffLoginRequiredMixin:
    def dispatch(self, request, *args, **kwargs):
        if not is_staff_authenticated(request):
            login_url = reverse('public-workout-staff-login')
            return redirect(f'{login_url}?{urlencode({"next": request.get_full_path()})}')
        return super().dispatch(request, *args, **kwargs)


__all__ = [
    'CurvaStaffLoginRequiredMixin', 'SESSION_KEY', 'authenticate_staff', 'is_staff_authenticated',
]
