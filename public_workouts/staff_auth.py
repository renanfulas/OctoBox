"""
ARQUIVO: login proprio da area interna do Curva (Renan e Giovanna).

POR QUE ELE EXISTE:
- public_workouts nao e' um produto multi-tenant do OctoBox (sem Box, sem
  Membership) — as duas unicas contas que precisam das telas internas do
  corredor nao cabem no sistema de papeis do OctoBox (access/roles/),
  entao nao usam auth.User nem RoleRequiredMixin. Credenciais vem de
  PublicWorkoutStaffCredential (models.py) — a MESMA tabela usada pelo
  cockpit de analytics (student_identity/public_workout_views.py), pra
  Renan/Giovanna terem uma senha so' pras duas telas internas do corredor,
  com um lugar so' pra revogar acesso (desativar a linha no Admin, sem
  precisar de deploy).

PONTOS CRITICOS:
- Senha nunca em texto puro em lugar nenhum (banco, log, sessao) — so' o
  hash gerado com django.contrib.auth.hashers.make_password.
- Sessao guarda so' o username autenticado, nunca senha nem hash.
- POST em /login/... ja' ganha rate limit automatico do
  RequestSecurityMiddleware (scope 'login', por prefixo de path,
  shared_support/security/__init__.py) — sem throttle proprio aqui.
- authenticate_staff roda check_password mesmo pra usuario inexistente
  (contra um hash valido fixo) pra nao vazar por timing quais usernames
  existem na tabela.
"""

from __future__ import annotations

from urllib.parse import urlencode

from django.contrib.auth.hashers import check_password, make_password
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone

SESSION_KEY = 'curva_staff_username'

# Hash valido e fixo (nunca comparado de verdade contra credencial real) —
# so' pra manter o tempo de resposta igual quando o username nao existe.
_DUMMY_HASH = make_password('curva-staff-auth-timing-safety-dummy')


def authenticate_staff(username: str, password: str) -> str | None:
    """Devolve o username normalizado se as credenciais baterem, senao None."""
    from .models import PublicWorkoutStaffCredential

    normalized = (username or '').strip().lower()
    credential = PublicWorkoutStaffCredential.objects.filter(username=normalized, is_active=True).first()
    password_hash = credential.password_hash if credential else _DUMMY_HASH
    if not check_password(password or '', password_hash) or credential is None:
        return None
    PublicWorkoutStaffCredential.objects.filter(pk=credential.pk).update(
        last_login_at=timezone.now(), updated_at=timezone.now(),
    )
    return normalized


def is_staff_authenticated(request) -> bool:
    username = request.session.get(SESSION_KEY)
    if not username:
        return False
    from .models import PublicWorkoutStaffCredential

    # Revalida contra a tabela atual: credencial desativada/removida depois
    # do login invalida a sessao velha na proxima requisicao.
    return PublicWorkoutStaffCredential.objects.filter(username=username, is_active=True).exists()


class CurvaStaffLoginRequiredMixin:
    def dispatch(self, request, *args, **kwargs):
        if not is_staff_authenticated(request):
            login_url = reverse('public-workout-staff-login')
            return redirect(f'{login_url}?{urlencode({"next": request.get_full_path()})}')
        return super().dispatch(request, *args, **kwargs)


__all__ = [
    'CurvaStaffLoginRequiredMixin', 'SESSION_KEY', 'authenticate_staff', 'is_staff_authenticated',
]
