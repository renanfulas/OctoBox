"""
Django middleware para expor metricas basicas via prometheus_client.
Instalacao: pip install prometheus_client
Adicionar em settings.py:
MIDDLEWARE = [
    ...
    'monitoring.prometheus_middleware.PrometheusBeforeMiddleware',
    ...
]
E adicionar uma view para expor metricas.
"""

import os
import time

from django.http import HttpResponse
from django.utils.crypto import constant_time_compare
from django.utils.deprecation import MiddlewareMixin
from django.views.decorators.http import require_http_methods
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest


REQUEST_LATENCY = Histogram(
    "http_server_request_latency_seconds",
    "Latency of HTTP requests in seconds",
    ["method", "endpoint", "status"],
)
REQUEST_COUNT = Counter(
    "http_server_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)


class PrometheusBeforeMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request._start_time = time.time()

    def process_response(self, request, response):
        try:
            start = getattr(request, "_start_time", None)
            if start is None:
                return response
            latency = time.time() - start
            method = request.method
            endpoint = (
                request.resolver_match.view_name
                if hasattr(request, "resolver_match") and request.resolver_match
                else request.path
            )
            status = str(response.status_code)
            REQUEST_LATENCY.labels(method=method, endpoint=endpoint, status=status).observe(latency)
            REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=status).inc()
        except Exception:
            pass
        return response


@require_http_methods(["GET"])
def metrics_view(request):
    token = os.getenv("PROMETHEUS_METRICS_TOKEN")
    auth_header = request.headers.get("Authorization", "")
    is_token_valid = token and constant_time_compare(auth_header, f"Bearer {token}")

    # Em producao, exigimos token. Sem token configurado, limitamos o endpoint ao host local.
    is_local = request.META.get("REMOTE_ADDR") in ["127.0.0.1", "::1"]

    if token:
        if not is_token_valid:
            return HttpResponse("Unauthorized", status=401)
    elif not is_local:
        return HttpResponse("Forbidden: Metrics accessible only via local or token.", status=403)

    data = generate_latest()
    return HttpResponse(data, content_type=CONTENT_TYPE_LATEST)
