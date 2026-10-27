"""
ARQUIVO: views de integracao da API v1.

POR QUE ELE EXISTE:
- separa endpoints de integracao e webhooks da base neutra da API.
- normaliza correlation id e payload de entrada antes de acionar a malha.
"""

from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django_tenants.utils import get_public_schema_name, schema_context

from control.models import Box
from control.tenant_write_fence import TenantFenceTargetMissing, TenantWritesFrozen
from finance.notification_webhooks import (
    ResendPaymentWebhookConflict,
    ResendPaymentWebhookTenantUnresolved,
    process_resend_payment_notification_webhook,
)
from integrations.mesh import classify_invalid_payload, build_correlation_id
from integrations.whatsapp.contracts import WhatsAppInboundPollVote
from integrations.whatsapp.services import process_poll_vote_webhook
from integrations.whatsapp.webhook_auth import MAX_POLL_WEBHOOK_BODY_BYTES, authenticate_poll_webhook
from student_identity.resend_webhooks import ResendWebhookHeaders, ResendWebhookVerificationError


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
        content_length = request.META.get('CONTENT_LENGTH', '')
        if content_length.isdigit() and int(content_length) > MAX_POLL_WEBHOOK_BODY_BYTES:
            response = JsonResponse(
                {
                    'accepted': False,
                    'reason': 'payload-too-large',
                    'failure_kind': 'invalid_payload',
                    'retryable': False,
                    'retry_action': 'give_up',
                },
                status=413,
            )
            response['X-OctoBox-Correlation-Id'] = _resolve_request_correlation_id(request)
            return response

        route, auth_failure = authenticate_poll_webhook(
            headers=request.headers,
            raw_body=request.body,
            instances_json=settings.WHATSAPP_POLL_WEBHOOK_INSTANCES_JSON,
        )
        if auth_failure:
            response = JsonResponse(
                {
                    'accepted': False,
                    'reason': auth_failure.code,
                    'failure_kind': 'unauthorized' if auth_failure.http_status == 401 else 'invalid_payload',
                    'retryable': auth_failure.http_status == 503,
                    'retry_action': 'retry' if auth_failure.http_status == 503 else 'contain',
                },
                status=auth_failure.http_status,
            )
            if auth_failure.http_status == 503:
                response['Retry-After'] = '60'
            response['X-OctoBox-Correlation-Id'] = _resolve_request_correlation_id(request)
            return response

        data = route.payload
        correlation_id = _resolve_request_correlation_id(request)
        voter_phone = data.get('voter_phone')
        poll_name = data.get('poll_name')
        option_text = data.get('option_text')

        if (
            not all(isinstance(value, str) and value.strip() for value in (voter_phone, poll_name, option_text))
            or len(voter_phone) > 255
            or len(poll_name) > 255
            or len(option_text) > 64
        ):
            failure = classify_invalid_payload(reason='missing-required-fields')
            response = JsonResponse(
                {
                    'accepted': False,
                    'reason': failure.reason,
                    'correlation_id': correlation_id,
                    'failure_kind': failure.kind,
                    'retryable': failure.retryable,
                    'retry_action': 'give_up',
                },
                status=400,
            )
            response['X-OctoBox-Correlation-Id'] = correlation_id
            return response

        with schema_context(get_public_schema_name()):
            box = Box.objects.filter(schema_name=route.schema_name).only('status').first()
        if box is None:
            response = JsonResponse(
                {
                    'accepted': False,
                    'reason': 'webhook-instance-unavailable',
                    'failure_kind': 'unauthorized',
                    'retryable': False,
                    'retry_action': 'contain',
                },
                status=401,
            )
            response['X-OctoBox-Correlation-Id'] = correlation_id
            return response
        if box.status != Box.Status.ACTIVE:
            response = JsonResponse(
                {
                    'accepted': False,
                    'reason': 'box-not-active',
                    'failure_kind': 'retryable',
                    'retryable': True,
                    'retry_action': 'retry',
                },
                status=503,
            )
            response['Retry-After'] = '60'
            response['X-OctoBox-Correlation-Id'] = correlation_id
            return response

        vote = WhatsAppInboundPollVote(
            phone=voter_phone,
            poll_title=poll_name,
            option_voted=option_text,
            external_id=route.event_id,
            event_id=route.event_id,
        )
        result = process_poll_vote_webhook(
            poll_vote=vote,
            tenant_schema=route.schema_name,
        )
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
        if result.retryable:
            retry_at = parse_datetime(result.next_retry_at) if result.next_retry_at else None
            retry_seconds = 60
            if retry_at:
                if timezone.is_naive(retry_at):
                    retry_at = timezone.make_aware(retry_at)
                retry_seconds = max(1, int((retry_at - timezone.now()).total_seconds() + 0.999))
            response['Retry-After'] = str(retry_seconds)
        response['X-OctoBox-Correlation-Id'] = correlation_id
        return response


@method_decorator(csrf_exempt, name='dispatch')
class ResendPaymentNotificationWebhookView(View):
    """Accept only signed Resend receipts and resolve their tenant by send tags."""

    MAX_BODY_BYTES = 262144

    def post(self, request, *args, **kwargs):
        content_length = request.META.get('CONTENT_LENGTH', '')
        if content_length.isdigit() and int(content_length) > self.MAX_BODY_BYTES:
            return JsonResponse({'accepted': False, 'reason': 'payload-too-large'}, status=413)
        raw_body = request.body
        if len(raw_body) > self.MAX_BODY_BYTES:
            return JsonResponse({'accepted': False, 'reason': 'payload-too-large'}, status=413)

        headers = ResendWebhookHeaders(
            webhook_id=request.headers.get('svix-id', '').strip(),
            timestamp=request.headers.get('svix-timestamp', '').strip(),
            signature=request.headers.get('svix-signature', '').strip(),
        )
        if not headers.webhook_id or not headers.timestamp or not headers.signature:
            return JsonResponse({'accepted': False, 'reason': 'missing-signature-headers'}, status=400)
        try:
            result = process_resend_payment_notification_webhook(payload=raw_body, headers=headers)
        except ResendWebhookVerificationError as exc:
            return JsonResponse({'accepted': False, 'reason': str(exc)}, status=400)
        except ResendPaymentWebhookConflict as exc:
            return JsonResponse({'accepted': False, 'reason': str(exc)}, status=409)
        except (ResendPaymentWebhookTenantUnresolved, TenantFenceTargetMissing, TenantWritesFrozen):
            response = JsonResponse({'accepted': False, 'reason': 'tenant-temporarily-unavailable'}, status=503)
            response['Retry-After'] = '60'
            return response
        return JsonResponse(result, status=200)
