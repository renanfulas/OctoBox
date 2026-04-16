"""
ARQUIVO: views de integracao da API v1.

POR QUE ELE EXISTE:
- separa endpoints de integracao e webhooks da base neutra da API.
- normaliza correlation id e payload de entrada antes de acionar a malha.
"""

import json
import os

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from integrations.mesh import classify_invalid_payload, classify_unauthorized, build_correlation_id
from integrations.whatsapp.contracts import WhatsAppInboundPollVote
from integrations.whatsapp.services import process_poll_vote_webhook


def _resolve_request_correlation_id(request, data: dict | None = None) -> str:
    return getattr(request, 'octobox_correlation_id', '') or build_correlation_id(
        request.headers.get('X-Correlation-ID')
        or request.headers.get('X-Request-ID')
        or (data or {}).get('correlation_id')
        or ''
    )


@method_decorator(csrf_exempt, name='dispatch')
class WhatsAppPollWebhookView(View):
    """Recebe votos de enquete do WhatsApp de um robo externo."""

    def post(self, request, *args, **kwargs):
        provided_token = request.headers.get('X-OctoBox-Webhook-Token')
        expected_token = os.getenv('WHATSAPP_WEBHOOK_SECRET')
        if not expected_token or provided_token != expected_token:
            failure = classify_unauthorized(reason='webhook-token-mismatch')
            response = JsonResponse(
                {
                    'accepted': False,
                    'reason': 'Unauthorized Configuration or Token',
                    'failure_kind': failure.kind,
                    'retryable': failure.retryable,
                    'retry_action': 'contain',
                },
                status=401,
            )
            response['X-OctoBox-Correlation-Id'] = _resolve_request_correlation_id(request)
            return response

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            failure = classify_invalid_payload(reason='invalid-json')
            response = JsonResponse(
                {
                    'accepted': False,
                    'reason': 'Invalid JSON',
                    'failure_kind': failure.kind,
                    'retryable': failure.retryable,
                    'retry_action': 'give_up',
                },
                status=400,
            )
            response['X-OctoBox-Correlation-Id'] = _resolve_request_correlation_id(request)
            return response

        correlation_id = _resolve_request_correlation_id(request, data)
        voter_phone = data.get('voter_phone')
        poll_name = data.get('poll_name')
        option_text = data.get('option_text')
        event_id = data.get('event_id') or data.get('message_id') or data.get('vote_id') or ''

        if not all([voter_phone, poll_name, option_text]):
            failure = classify_invalid_payload(reason='missing-required-fields')
            response = JsonResponse(
                {
                    'accepted': False,
                    'reason': 'Missing required fields: voter_phone, poll_name, option_text',
                    'correlation_id': correlation_id,
                    'failure_kind': failure.kind,
                    'retryable': failure.retryable,
                    'retry_action': 'give_up',
                },
                status=400,
            )
            response['X-OctoBox-Correlation-Id'] = correlation_id
            return response

        vote = WhatsAppInboundPollVote(
            phone=voter_phone,
            poll_title=poll_name,
            option_voted=option_text,
            external_id=event_id,
            event_id=event_id,
            raw_payload=data,
        )
        result = process_poll_vote_webhook(poll_vote=vote)
        status_code = 200 if result.accepted else (503 if result.retryable else 400)
        response = JsonResponse(
            {
                'accepted': result.accepted,
                'reason': result.reason,
                'correlation_id': correlation_id,
                'failure_kind': result.failure_kind,
                'retryable': result.retryable,
                'retry_action': result.retry_action,
                'attempt_number': result.attempt_number,
                'max_attempts': result.max_attempts,
                'next_retry_at': result.next_retry_at,
            },
            status=status_code,
        )
        response['X-OctoBox-Correlation-Id'] = correlation_id
        return response
