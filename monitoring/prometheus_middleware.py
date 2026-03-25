"""
Django middleware para expor métricas básicas via prometheus_client.
Instalação: pip install prometheus_client
Adicionar em settings.py:
MIDDLEWARE = [
    ...
    'monitoring.prometheus_middleware.PrometheusBeforeMiddleware',
    ...
]
E adicionar uma view para expor métricas (veja README).
"""
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from django.utils.deprecation import MiddlewareMixin
from django.http import HttpResponse
import time

REQUEST_LATENCY = Histogram('http_server_request_latency_seconds', 'Latency of HTTP requests in seconds', ['method', 'endpoint', 'status'])
REQUEST_COUNT = Counter('http_server_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])

class PrometheusBeforeMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request._start_time = time.time()

    def process_response(self, request, response):
        try:
            start = getattr(request, '_start_time', None)
            if start is None:
                return response
            latency = time.time() - start
            method = request.method
            endpoint = (request.resolver_match.view_name if hasattr(request, 'resolver_match') and request.resolver_match else request.path)
            status = str(response.status_code)
            REQUEST_LATENCY.labels(method=method, endpoint=endpoint, status=status).observe(latency)
            REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=status).inc()
        except Exception:
            pass
        return response

# Helper view para expor métricas
from django.views.decorators.http import require_http_methods

@require_http_methods(["GET"])
def metrics_view(request):
    data = generate_latest()
    return HttpResponse(data, content_type=CONTENT_TYPE_LATEST)
