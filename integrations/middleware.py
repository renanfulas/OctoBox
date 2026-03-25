import json
import logging
from django.http import JsonResponse
from integrations.whatsapp.models import WebhookEvent, WebhookDeliveryStatus

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
        
        # 1. Tentar extrair do Header (Padrão de mercado)
        event_id = request.headers.get('X-Idempotency-Key')
        
        # 2. Tentar extrair do Body JSON se o header falhar
        if not event_id:
            try:
                # O Django não permite ler o body duas vezes se não usarmos o stream com cuidado,
                # mas em middlewares de API costumamos ler o payload pequeno.
                body_data = json.loads(request.body)
                event_id = (
                    body_data.get('event_id') or 
                    body_data.get('external_id') or 
                    body_data.get('id') or 
                    body_data.get('message_id')
                )
            except Exception:
                pass

        if not event_id:
            # Se não houver ID, deixamos passar (mas avisamos no log para melhoria)
            logger.debug(f"Webhook sem Idempotency Key: {request.path}")
            return self.get_response(request)

        # 3. Verificar Deduplicação
        existing_event = WebhookEvent.objects.filter(
            event_id=event_id, 
            status=WebhookDeliveryStatus.PROCESSED
        ).exists()

        if existing_event:
            logger.info(f"Deduplicação ativada: {event_id} filtrado em {request.path}")
            return JsonResponse({
                'accepted': True, 
                'reason': 'Duplicate event ignored (idempotency layer)',
                'event_id': event_id
            }, status=200)

        # 4. Prossiga com o processamento normal
        # Nota: O registro do evento em si é feito nas views específicas para maior controle
        # granular de sucesso/falha. Este middleware serve como o "Circuit Breaker" inicial.
        return self.get_response(request)
