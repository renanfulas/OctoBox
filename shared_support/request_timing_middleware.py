"""
ARQUIVO: middleware de telemetria leve de request.

POR QUE ELE EXISTE:
- separa custo de view de custo de sessao, auth e shell no primeiro hit autenticado.
- publica uma trilha curta em `Server-Timing` sem depender de profiling pesado.

O QUE ESTE ARQUIVO FAZ:
1. mede o tempo total do request.
2. força a resolucao do usuario autenticado uma vez e mede esse custo.
3. publica metricas compactas no header `Server-Timing`.

PONTOS CRITICOS:
- deve permanecer leve e seguro para producao.
- nao deve acessar banco extra fora do custo natural da autenticacao.
"""

from __future__ import annotations

import time

from django.conf import settings


class RequestTimingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        started_at = time.perf_counter()
        request._octobox_request_perf = {
            'session_engine': getattr(settings, 'SESSION_ENGINE', ''),
            'session_cache_alias': getattr(settings, 'SESSION_CACHE_ALIAS', ''),
            'session_key_present': bool(getattr(request, 'session', None) and request.session.session_key),
        }

        auth_started_at = time.perf_counter()
        user_is_authenticated = bool(getattr(request.user, 'is_authenticated', False))
        request._octobox_request_perf['auth_user_resolution_ms'] = round(
            (time.perf_counter() - auth_started_at) * 1000, 2
        )
        request._octobox_request_perf['user_is_authenticated'] = user_is_authenticated

        response = self.get_response(request)

        total_request_ms = round((time.perf_counter() - started_at) * 1000, 2)
        request._octobox_request_perf['request_total_ms'] = total_request_ms

        server_timing_parts = [
            f'req-total;dur={total_request_ms}',
            f'auth-user;dur={request._octobox_request_perf["auth_user_resolution_ms"]}',
        ]
        shell_perf = request._octobox_request_perf.get('shell_counts') or {}
        if shell_perf:
            server_timing_parts.extend(
                [
                    f'shell-total;dur={shell_perf.get("total_ms", 0)}',
                    f'shell-cache;dur={shell_perf.get("cache_lookup_ms", 0)}',
                    f'shell-build;dur={shell_perf.get("build_ms", 0)}',
                    f'shell-overdue;dur={shell_perf.get("overdue_payments_ms", 0)}',
                    f'shell-overdue-students;dur={shell_perf.get("overdue_students_ms", 0)}',
                    f'shell-intakes;dur={shell_perf.get("pending_intakes_ms", 0)}',
                    f'shell-sessions;dur={shell_perf.get("sessions_today_ms", 0)}',
                    f'shell-students;dur={shell_perf.get("student_summary_ms", 0)}',
                    f'shell-enrollments;dur={shell_perf.get("active_enrollments_ms", 0)}',
                ]
            )

        response['Server-Timing'] = ', '.join(server_timing_parts)
        response['X-OctoBox-Session-Engine'] = request._octobox_request_perf.get('session_engine', '')
        response['X-OctoBox-Session-Key-Present'] = '1' if request._octobox_request_perf.get('session_key_present') else '0'
        response['X-OctoBox-User-Authenticated'] = '1' if user_is_authenticated else '0'
        if shell_perf:
            response['X-OctoBox-Shell-Cache-Hit'] = '1' if shell_perf.get('cache_hit') else '0'
        return response
