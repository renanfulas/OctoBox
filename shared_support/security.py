"""
ARQUIVO: guardas transversais de seguranca HTTP.

POR QUE ELE EXISTE:
- aplica contencao basica contra rajadas e varredura de rotas sensiveis antes da view tocar no banco.

O QUE ESTE ARQUIVO FAZ:
1. limita tentativas no login.
2. limita trafego para o admin em rota nao publica.
3. limita repeticao em rotas mutaveis que escrevem no sistema.

PONTOS CRITICOS:
- limites muito baixos podem bloquear operacao legitima.
- limites muito altos reduzem a eficacia contra abuso por repeticao.
"""

from __future__ import annotations

from dataclasses import dataclass
from ipaddress import ip_address, ip_network
from logging import getLogger

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse


SECURITY_LOGGER = getLogger('octobox.security')
WRITE_METHODS = {'POST', 'PUT', 'PATCH', 'DELETE'}
WRITE_PATH_PREFIXES = (
    '/operacao/',
    '/alunos/',
    '/financeiro/',
    '/grade-aulas/',
)
EXPORT_PATH_RULES = (
    ('/alunos/exportar/', 'student-directory-export'),
    ('/financeiro/exportar/', 'finance-report-export'),
)
HEAVY_READ_PATH_RULES = (
    ('/dashboard/', 'dashboard-read'),
    ('/alunos/', 'student-directory-read'),
    ('/financeiro/', 'finance-center-read'),
    ('/grade-aulas/', 'class-grid-read'),
    ('/operacao/owner/', 'operations-owner-read'),
    ('/operacao/dev/', 'operations-dev-read'),
    ('/operacao/manager/', 'operations-manager-read'),
    ('/operacao/coach/', 'operations-coach-read'),
    ('/operacao/recepcao/', 'operations-reception-read'),
)


@dataclass(frozen=True, slots=True)
class RateLimitRule:
    scope: str
    limit: int
    window_seconds: int


def _coerce_ip(value: str):
    try:
        return ip_address((value or '').strip())
    except ValueError:
        return None


def _ip_matches_patterns(ip_value: str, patterns) -> bool:
    current_ip = _coerce_ip(ip_value)
    if current_ip is None:
        return False

    for pattern in patterns or []:
        raw_pattern = (pattern or '').strip()
        if not raw_pattern:
            continue
        try:
            if '/' in raw_pattern:
                if current_ip in ip_network(raw_pattern, strict=False):
                    return True
            elif current_ip == ip_address(raw_pattern):
                return True
        except ValueError:
            continue
    return False


def _get_client_ip(request) -> str:
    remote_addr = (request.META.get('REMOTE_ADDR') or '').strip()
    trusted_proxy_patterns = getattr(settings, 'SECURITY_TRUSTED_PROXY_IPS', ())

    if remote_addr and _ip_matches_patterns(remote_addr, trusted_proxy_patterns):
        for header_name in ('HTTP_CF_CONNECTING_IP', 'HTTP_X_FORWARDED_FOR'):
            header_value = (request.META.get(header_name) or '').strip()
            if not header_value:
                continue
            candidate_ip = header_value.split(',')[0].strip()
            if _coerce_ip(candidate_ip) is not None:
                SECURITY_LOGGER.debug('client_ip resolved from header %s -> %s', header_name, candidate_ip)
                return candidate_ip

    if _coerce_ip(remote_addr) is not None:
        SECURITY_LOGGER.debug('client_ip using REMOTE_ADDR -> %s', remote_addr)
        return remote_addr
    return 'unknown'


def _get_actor_token(request) -> str:
    if getattr(request, 'user', None) is not None and request.user.is_authenticated:
        return f'user:{request.user.pk}'
    return f'ip:{_get_client_ip(request)}'


def _consume_rate_limit(*, scope: str, token: str, limit: int, window_seconds: int) -> tuple[bool, int]:
    cache_key = f'rate-limit:{scope}:{token}'
    added = cache.add(cache_key, 1, timeout=window_seconds)
    if added:
        return True, window_seconds

    try:
        current_value = cache.incr(cache_key)
    except ValueError:
        cache.set(cache_key, 1, timeout=window_seconds)
        current_value = 1

    if current_value <= limit:
        return True, window_seconds
    return False, window_seconds


def _build_blocked_response(client_ip: str) -> HttpResponse:
    SECURITY_LOGGER.warning('security_ip_blocked client_ip=%s', client_ip)
    return HttpResponse('A origem desta requisicao esta bloqueada pela politica de seguranca.', status=403)


def _log_rate_limit_event(*, scope: str, request, client_ip: str, retry_after: int):
    user_id = getattr(getattr(request, 'user', None), 'id', None)
    SECURITY_LOGGER.warning(
        'security_rate_limit_triggered scope=%s client_ip=%s path=%s method=%s user_id=%s retry_after=%s',
        scope,
        client_ip,
        request.path,
        request.method,
        user_id,
        retry_after,
    )


class RequestSecurityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        blocked_response = self._block_when_needed(request)
        if blocked_response is not None:
            return blocked_response
        return self.get_response(request)

    def _block_when_needed(self, request):
        client_ip = _get_client_ip(request)
        blocked_patterns = [
            *getattr(settings, 'SECURITY_BLOCKED_IPS', ()),
            *getattr(settings, 'SECURITY_BLOCKED_IP_RANGES', ()),
        ]
        if _ip_matches_patterns(client_ip, blocked_patterns):
            return _build_blocked_response(client_ip)

        rule = self._resolve_rule(request)
        if rule is None:
            return None

        allowed, retry_after = _consume_rate_limit(
            scope=rule.scope,
            token=_get_actor_token(request),
            limit=rule.limit,
            window_seconds=rule.window_seconds,
        )
        SECURITY_LOGGER.debug('rate_limit check scope=%s token=%s allowed=%s', rule.scope, _get_actor_token(request), allowed)
        # debug via logger only
        if allowed:
            return None

        _log_rate_limit_event(scope=rule.scope, request=request, client_ip=client_ip, retry_after=retry_after)

        response = HttpResponse('Muitas requisicoes em pouco tempo. Aguarde antes de tentar novamente.', status=429)
        response['Retry-After'] = str(retry_after)
        return response

    def _resolve_rule(self, request) -> RateLimitRule | None:
        path = request.path
        admin_path = f'/{settings.ADMIN_URL_PATH.lstrip("/")}'

        if request.method == 'POST' and path.startswith('/login/'):
            return RateLimitRule(
                scope='login',
                limit=settings.LOGIN_RATE_LIMIT_MAX_REQUESTS,
                window_seconds=settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS,
            )

        if path.startswith(admin_path):
            return RateLimitRule(
                scope='admin',
                limit=settings.ADMIN_RATE_LIMIT_MAX_REQUESTS,
                window_seconds=settings.ADMIN_RATE_LIMIT_WINDOW_SECONDS,
            )

        if request.method in WRITE_METHODS and any(path.startswith(prefix) for prefix in WRITE_PATH_PREFIXES):
            return RateLimitRule(
                scope='write',
                limit=settings.WRITE_RATE_LIMIT_MAX_REQUESTS,
                window_seconds=settings.WRITE_RATE_LIMIT_WINDOW_SECONDS,
            )

        if request.method == 'GET':
            for prefix, scope in EXPORT_PATH_RULES:
                if path.startswith(prefix):
                    return RateLimitRule(
                        scope=scope,
                        limit=settings.EXPORT_RATE_LIMIT_MAX_REQUESTS,
                        window_seconds=settings.EXPORT_RATE_LIMIT_WINDOW_SECONDS,
                    )

            if path.startswith('/api/v1/students/autocomplete/'):
                return RateLimitRule(
                    scope='student-autocomplete',
                    limit=settings.AUTOCOMPLETE_RATE_LIMIT_MAX_REQUESTS,
                    window_seconds=settings.AUTOCOMPLETE_RATE_LIMIT_WINDOW_SECONDS,
                )

            for exact_path, scope in HEAVY_READ_PATH_RULES:
                if path == exact_path:
                    limit = settings.DASHBOARD_RATE_LIMIT_MAX_REQUESTS if scope == 'dashboard-read' else settings.HEAVY_READ_RATE_LIMIT_MAX_REQUESTS
                    window_seconds = settings.DASHBOARD_RATE_LIMIT_WINDOW_SECONDS if scope == 'dashboard-read' else settings.HEAVY_READ_RATE_LIMIT_WINDOW_SECONDS
                    return RateLimitRule(
                        scope=scope,
                        limit=limit,
                        window_seconds=window_seconds,
                    )

        return None


def check_export_quota(*, user_id: int, scope: str, limit: int = 2) -> tuple[bool, int]:
    """
    Verifica se o usuário pode realizar uma exportação no escopo (ex: 'annual').
    Cota padrão: 2 exportações por janela de 7 dias (604800 segundos).
    Retorna (permitido, contagem_atual).
    """
    cache_key = f'export_quota:{user_id}:{scope}'
    current_count = cache.get(cache_key, 0)
    window = 604800  # 7 dias

    if current_count >= limit:
        SECURITY_LOGGER.warning('export_quota_exceeded user_id=%s scope=%s count=%s', user_id, scope, current_count)
        return False, int(current_count)

    if current_count == 0:
        cache.set(cache_key, 1, timeout=window)
    else:
        cache.incr(cache_key)

    return True, int(current_count) + 1


__all__ = ['RequestSecurityMiddleware', 'check_export_quota']