from __future__ import annotations

from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse

from auditing.models import AuditEvent
from student_identity.infrastructure.session import get_student_session_cookie_name, read_student_session_value
from student_identity.security import resolve_student_client_ip

_PUBLIC_PREFIXES = (
    '/aluno/auth/',
    '/aluno/offline',
    '/aluno/manifest.webmanifest',
    '/aluno/sw.js',
)

_PENDING_ONBOARDING_SESSION_KEY = 'student_pending_onboarding'


def _is_public_path(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in _PUBLIC_PREFIXES)




def _resolve_student_tenant(request, session_payload: dict) -> None:
    # Sprint 2: resolve tenant ativo para /aluno/* via box_id do cookie do aluno.
    # box_id (FK control.Box) tem prioridade; fallback para box_root_slug legado.
    from django.db import connection
    active_box_id = session_payload.get('active_box_id') or session_payload.get('box_id')
    if active_box_id:
        try:
            from control.models import Box
            box = Box.objects.filter(pk=active_box_id, status=Box.Status.ACTIVE).first()
            if box:
                connection.set_tenant(box)
                request.tenant = box
                return
        except Exception:
            pass
    # Legado: sem box_id no cookie (sessao antiga), usa box_root_slug
    box_root_slug = session_payload.get('active_box_root_slug') or session_payload.get('box_root_slug')
    if box_root_slug:
        try:
            from control.models import Box
            box = Box.objects.filter(slug=box_root_slug, status=Box.Status.ACTIVE).first()
            if box:
                connection.set_tenant(box)
                request.tenant = box
        except Exception:
            pass


def _has_active_membership(request, session_payload: dict) -> bool:
    """Sprint 4 / §3.5.4: verifica StudentBoxMembership.status=ACTIVE para o tenant resolvido.

    Usado pelo StudentAuthMiddleware para bloquear acesso de alunos cujo membership
    foi suspenso, revogado ou ainda esta pendente de aprovacao.

    Retorna True em caso de duvida (sessao legada sem identity_id, nenhum tenant resolvido)
    para evitar lockout de usuarios em migracao gradual.
    """
    identity_id = session_payload.get('identity_id')
    if not identity_id:
        return True  # sessao legada sem identity_id — nao bloquear
    tenant = getattr(request, 'tenant', None)
    if tenant is None:
        return True  # sem tenant resolvido — nao bloquear (evita loop de redirect)
    try:
        from student_identity.models import StudentBoxMembership, StudentBoxMembershipStatus
        return StudentBoxMembership.objects.filter(
            identity_id=identity_id,
            box_root_slug=tenant.slug,
            status=StudentBoxMembershipStatus.ACTIVE,
        ).exists()
    except Exception:
        return True  # falha ao consultar — nao bloquear

class StudentAuthMiddleware:
    def __init__(self, get_response):
        self._get_response = get_response
        self._student_prefix = getattr(settings, 'STUDENT_APP_URL_PREFIX', '/aluno/')
        self._login_url = getattr(settings, 'STUDENT_LOGIN_URL', '/aluno/auth/login/')

    def __call__(self, request):
        if (
            request.path.startswith(self._student_prefix)
            and not _is_public_path(request.path)
        ):
            cookie_name = get_student_session_cookie_name()
            session_payload = read_student_session_value(request.COOKIES.get(cookie_name))
            has_pending_onboarding = bool(request.session.get(_PENDING_ONBOARDING_SESSION_KEY))
            # Sprint 2: resolve tenant do box do aluno via cookie.
            if session_payload is not None:
                _resolve_student_tenant(request, session_payload)
                # Sprint 4 / §3.5.4: bloqueia acesso se membership nao esta ACTIVE.
                if not _has_active_membership(request, session_payload):
                    return redirect(reverse('student-app-no-active-box'))

            if session_payload is None and not has_pending_onboarding:
                AuditEvent.objects.create(
                    actor=None,
                    actor_role='',
                    action='student_app.anonymous_access_redirected',
                    target_model='student_app.AnonymousAccess',
                    target_label=request.path[:120],
                    description='Acesso anonimo a rota protegida do app do aluno redirecionado para login.',
                    metadata={
                        'path': request.path,
                        'method': request.method,
                        'ip_hash': __import__('hashlib').sha256(
                            resolve_student_client_ip(request).encode()
                        ).hexdigest()[:8],
                    },
                )
                messages.warning(
                    request,
                    'Para acessar esta pagina, entre com sua conta Google ou Apple primeiro.',
                )
                return redirect(self._login_url)
        return self._get_response(request)
