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
                messages.info(request, 'Faca login para acessar o app.')
                return redirect(self._login_url)
        return self._get_response(request)
