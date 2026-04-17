"""
ARQUIVO: guardrails leves de seguranca do fluxo do aluno.

POR QUE ELE EXISTE:
- protege o login social e o aceite de convite sem misturar essa logica com o fluxo principal das views.
- oferece fingerprint leve, throttle dedicado e gatilhos de anomalia para a superficie publica do aluno.

O QUE ESTE ARQUIVO FAZ:
1. resolve IP do cliente com suporte a proxy confiavel.
2. gera fingerprint leve do dispositivo para o cookie proprio do aluno.
3. aplica throttles dedicados para callback social e aceite de convite.
4. dispara alertas de anomalia com cooldown para evitar sirene infinita.

PONTOS CRITICOS:
- o fingerprint e leve e nao deve ser tratado como prova absoluta de identidade.
- limites baixos demais podem bloquear aluno legitimo trocando de rede.
- alertas precisam ser deduplicados para nao poluir auditoria em rajada.
"""

from __future__ import annotations

import hmac
from hashlib import sha256
from ipaddress import ip_address, ip_network
from logging import getLogger

from django.conf import settings
from django.core.cache import cache

from auditing.models import AuditEvent


SECURITY_LOGGER = getLogger('octobox.security')


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


def resolve_student_client_ip(request) -> str:
    remote_addr = (request.META.get('REMOTE_ADDR') or '').strip()
    trusted_proxy_patterns = getattr(settings, 'SECURITY_TRUSTED_PROXY_IPS', ())
    if remote_addr and _ip_matches_patterns(remote_addr, trusted_proxy_patterns):
        for header_name in ('HTTP_CF_CONNECTING_IP', 'HTTP_X_FORWARDED_FOR'):
            header_value = (request.META.get(header_name) or '').strip()
            if not header_value:
                continue
            candidate_ip = header_value.split(',')[0].strip()
            if _coerce_ip(candidate_ip) is not None:
                return candidate_ip
    if _coerce_ip(remote_addr) is not None:
        return remote_addr
    return 'unknown'


def build_student_device_fingerprint(request) -> str:
    client_ip = resolve_student_client_ip(request)
    if '.' in client_ip:
        ip_bucket = '.'.join(client_ip.split('.')[:3])
    else:
        ip_bucket = client_ip
    user_agent = (request.META.get('HTTP_USER_AGENT') or 'unknown').strip()
    accept_language = (request.META.get('HTTP_ACCEPT_LANGUAGE') or '').split(',')[0].strip().lower()
    payload = f'{ip_bucket}|{user_agent}|{accept_language}'.encode('utf-8')
    return hmac.new(settings.SECRET_KEY.encode('utf-8'), payload, digestmod=sha256).hexdigest()


def check_student_flow_rate_limit(*, scope: str, token: str, limit: int, window_seconds: int) -> tuple[bool, int]:
    cache_key = f'student-flow-rate-limit:{scope}:{token}'
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


def maybe_emit_student_anomaly_alert(
    *,
    scope: str,
    actor,
    actor_role: str,
    target_label: str,
    description: str,
    metadata: dict,
    dedupe_window_seconds: int,
) -> bool:
    dedupe_key = f'student-anomaly-alert:{scope}:{target_label}'
    if not cache.add(dedupe_key, 1, timeout=dedupe_window_seconds):
        return False
    AuditEvent.objects.create(
        actor=actor,
        actor_role=actor_role,
        action='student_security.anomaly_detected',
        target_model='student_identity.security',
        target_label=target_label,
        description=description,
        metadata={
            'scope': scope,
            **(metadata or {}),
        },
    )
    SECURITY_LOGGER.warning(
        'student_security_anomaly_detected scope=%s target=%s metadata=%s',
        scope,
        target_label,
        metadata,
    )
    return True

