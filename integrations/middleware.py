import json
import logging
from django.db.models import Q
from django.http import JsonResponse
from integrations.whatsapp.models import WebhookEvent, WebhookDeliveryStatus
from communications.infrastructure.django_inbound_idempotency import calculate_webhook_fingerprint

logger = logging.getLogger('octobox.integrations')

class WebhookIdempotencyMiddleware:
    """
    Middleware global para deduplicação de Webhooks.
    Procura por IDs únicos no payload ou headers e evita re-processamento.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Apenas monitoramos endpoints de integração via POST
        if request.method == 'POST' and '/api/v1/integrations/' in request.path:
            return self.process_webhook(request)
        
        return self.get_response(request)

    def process_webhook(self, request):
        event_id = None
        fingerprint = None
        
        # 1. Tentar extrair do Header (Padrão de mercado)
        event_id = request.headers.get('X-Idempotency-Key')
        
        # 2. Tentar extrair do Body JSON
        try:
            body_data = json.loads(request.body)
            if not event_id:
                event_id = (
                    body_data.get('event_id') or 
                    body_data.get('external_id') or 
                    body_data.get('id') or 
                    body_data.get('message_id')
                )
            # Gerar fingerprint determinístico do conteúdo
            fingerprint = calculate_webhook_fingerprint(body_data)
        except Exception:
            pass

        if not event_id and not fingerprint:
            return self.get_response(request)

        # 3. Verificar Deduplicação (ID ou Fingerprint)
        query = Q()
        if event_id:
            query |= Q(event_id=event_id)
        if fingerprint:
            query |= Q(webhook_fingerprint=fingerprint)

        existing_event = WebhookEvent.objects.filter(
            query, 
            status=WebhookDeliveryStatus.PROCESSED
        ).exists()

        if existing_event:
            logger.info(f"Deduplicação ativada: {event_id or fingerprint} filtrado em {request.path}")
            return JsonResponse({
                'accepted': True, 
                'reason': 'Duplicate event ignored (fingerprint layer)',
                'event_id': event_id,
                'fingerprint': fingerprint
            }, status=200)

        # 4. Prossiga com o processamento normal
        # Nota: O registro do evento em si é feito nas views específicas para maior controle
        # granular de sucesso/falha. Este middleware serve como o "Circuit Breaker" inicial.
        return self.get_response(request)
