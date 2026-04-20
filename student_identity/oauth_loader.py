"""
ARQUIVO: loader do callback OAuth do app do aluno.

POR QUE ELE EXISTE:
- tira da view a validacao de rajada e o bloqueio inicial do callback social.

O QUE ESTE ARQUIVO FAZ:
1. aplica o rate limit do callback OAuth.
2. registra auditoria quando o callback e bloqueado por rajada.
3. devolve a resposta HTTP de bloqueio pronta para a casca HTTP.

PONTOS CRITICOS:
- qualquer ajuste aqui altera a primeira barreira de protecao do fluxo de login do aluno.
- a resposta 429 e a auditoria precisam continuar identicas ao comportamento anterior.
"""

from django.conf import settings
from django.http import HttpResponse

from auditing.models import AuditEvent

from .security import check_student_flow_rate_limit, resolve_student_client_ip


def enforce_student_oauth_callback_rate_limit(*, request, provider: str):
    allowed, retry_after = check_student_flow_rate_limit(
        scope='student-oauth-callback',
        token=f'ip:{resolve_student_client_ip(request)}',
        limit=max(1, int(getattr(settings, 'STUDENT_OAUTH_CALLBACK_RATE_LIMIT_MAX_REQUESTS', 12))),
        window_seconds=max(1, int(getattr(settings, 'STUDENT_OAUTH_CALLBACK_RATE_LIMIT_WINDOW_SECONDS', 300))),
    )
    if allowed:
        return None

    AuditEvent.objects.create(
        actor=None,
        actor_role='',
        action='student_oauth_callback.rate_limited',
        target_model='student_identity.StudentOAuthCallback',
        target_label=provider,
        description='Callback social do aluno bloqueado por rajada.',
        metadata={
            'provider': provider,
            'client_ip': resolve_student_client_ip(request),
            'path': request.path,
        },
    )
    response = HttpResponse('Muitas tentativas de callback social em pouco tempo. Aguarde e tente novamente.', status=429)
    response['Retry-After'] = str(retry_after)
    return response


__all__ = ['enforce_student_oauth_callback_rate_limit']
