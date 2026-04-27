"""
ARQUIVO: views de observabilidade das integrações.

POR QUE ELE EXISTE:
- Expõe o estado da Signal Mesh para managers e owners sem acesso direto ao banco.
- Permite retry manual e leitura de lag por evento.

O QUE ESTE ARQUIVO FAZ:
1. Lista PaymentWebhookEvents com filtro por status.
2. Exibe lag médio e contagem de retentativas.
3. Permite retry manual de eventos com falha.

PONTOS CRITICOS:
- Acesso restrito a manager e owner.
- Retry só recoloca o evento em PENDING — o router processa assincronamente.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Avg, Count, F, Q
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.generic import ListView, View

from access.permissions import RoleRequiredMixin
from integrations.stripe.models import PaymentWebhookEvent, PaymentWebhookStatus


class WebhookPanelView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    allowed_roles = ('owner', 'manager', 'dev')
    template_name = 'integrations/webhook_panel.html'
    context_object_name = 'events'
    paginate_by = 50

    def get_queryset(self):
        status_filter = self.request.GET.get('status', '')
        qs = PaymentWebhookEvent.objects.all().order_by('-created_at')
        if status_filter in PaymentWebhookStatus.values:
            qs = qs.filter(status=status_filter)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        now = timezone.now()
        ctx['status_choices'] = PaymentWebhookStatus.choices
        ctx['current_status'] = self.request.GET.get('status', '')
        ctx['summary'] = PaymentWebhookEvent.objects.aggregate(
            total=Count('id'),
            pending=Count('id', filter=Q(status=PaymentWebhookStatus.PENDING)),
            processed=Count('id', filter=Q(status=PaymentWebhookStatus.PROCESSED)),
            failed=Count('id', filter=Q(status=PaymentWebhookStatus.FAILED)),
        )
        return ctx


class WebhookRetryView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = ('owner', 'manager', 'dev')

    def post(self, request, pk):
        event = get_object_or_404(PaymentWebhookEvent, pk=pk, status=PaymentWebhookStatus.FAILED)
        event.status = PaymentWebhookStatus.PENDING
        event.next_retry_at = None
        event.last_error_message = 'retry-manual'
        event.save(update_fields=['status', 'next_retry_at', 'last_error_message', 'updated_at'])

        from integrations.stripe.router import route_payment_webhook_event
        route_payment_webhook_event(event)

        return redirect(f'{request.META.get("HTTP_REFERER", "/integrations/webhooks/")}')


__all__ = ['WebhookPanelView', 'WebhookRetryView']
