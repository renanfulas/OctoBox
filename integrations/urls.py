"""
ARQUIVO: URLs do app de integrações.

POR QUE ELE EXISTE:
- Registra o painel de observabilidade da Signal Mesh e o endpoint de retry manual.
"""

from django.urls import path

from .views import WebhookPanelView, WebhookRetryView

app_name = 'integrations'

urlpatterns = [
    path('integrations/webhooks/', WebhookPanelView.as_view(), name='webhook-panel'),
    path('integrations/webhooks/<int:pk>/retry/', WebhookRetryView.as_view(), name='webhook-retry'),
]
