import json
import logging

from django.db.models import Q
from django.http import JsonResponse

from integrations.mesh import build_correlation_id, calculate_signal_fingerprint, resolve_idempotency_key
from integrations.whatsapp.models import WebhookDeliveryStatus, WebhookEvent

logger = logging.getLogger('octobox.integrations')


class WebhookIdempotencyMiddleware:
    """
    Middleware global para deduplicacao de webhooks.
    Procura IDs unicos no payload ou headers e evita reprocessamento.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == 'POST' and '/api/v1/integrations/' in request.path:
            return self.process_webhook(request)

        return self.get_response(request)

    def process_webhook(self, request):
        fingerprint = None
        correlation_id = build_correlation_id(
            request.headers.get('X-Correlation-ID') or request.headers.get('X-Request-ID') or ''
        )
        request.octobox_correlation_id = correlation_id
        explicit_key = request.headers.get('X-Idempotency-Key', '')

        try:
            body_data = json.loads(request.body)
            fingerprint = calculate_signal_fingerprint(body_data)
            idempotency_key = resolve_idempotency_key(
                explicit_key=explicit_key,
                event_id=body_data.get('event_id', ''),
                external_id=body_data.get('external_id', ''),
                message_id=body_data.get('message_id', ''),
                provider_reference=body_data.get('id', ''),
                fingerprint=fingerprint,
            )
        except Exception:
            body_data = None
            idempotency_key = resolve_idempotency_key(explicit_key=explicit_key, fingerprint=fingerprint)

        if not idempotency_key and not fingerprint:
            response = self.get_response(request)
            response['X-OctoBox-Correlation-Id'] = correlation_id
            return response

        query = Q()
        if idempotency_key:
            query |= Q(event_id=idempotency_key)
        if fingerprint:
            query |= Q(webhook_fingerprint=fingerprint)

        existing_event = WebhookEvent.objects.filter(
            query,
            status=WebhookDeliveryStatus.PROCESSED,
        ).exists()

        if existing_event:
            logger.info('Deduplicacao ativada: %s filtrado em %s', idempotency_key or fingerprint, request.path)
            response = JsonResponse(
                {
                    'accepted': True,
                    'reason': 'Duplicate event ignored (fingerprint layer)',
                    'event_id': idempotency_key,
                    'idempotency_key': idempotency_key,
                    'fingerprint': fingerprint,
                    'correlation_id': correlation_id,
                },
                status=200,
            )
            response['X-OctoBox-Correlation-Id'] = correlation_id
            return response

        response = self.get_response(request)
        response['X-OctoBox-Correlation-Id'] = correlation_id
        return response
