"""
ARQUIVO: rotas da API v1.

POR QUE ELE EXISTE:
- Organiza os endpoints da primeira versao da API em um bloco proprio.

O QUE ESTE ARQUIVO FAZ:
1. Publica o manifesto da v1.
2. Publica a rota de saude da v1.

PONTOS CRITICOS:
- Nomes e caminhos daqui viram contrato publico da API.
"""

from django.urls import path

from .views import (
    ApiV1HealthView,
    ApiV1ManifestView,
    PaymentLinkView,
    ResendInvitationWebhookView,
    StudentAutocompleteView,
    WhatsAppPollWebhookView,
    init_system_view,
)
from .finance_views import StudentFreezeView
from .jobs_views import SecureExportDownloadView


urlpatterns = [
    path('', ApiV1ManifestView.as_view(), name='api-v1-manifest'),
    path('health/', ApiV1HealthView.as_view(), name='api-v1-health'),
    path('students/autocomplete/', StudentAutocompleteView.as_view(), name='api-v1-student-autocomplete'),
    path('finance/payment-link/<int:payment_id>/', PaymentLinkView.as_view(), name='api-v1-payment-link'),
    path('finance/freeze-student/', StudentFreezeView.as_view(), name='api-v1-finance-freeze'),
    path('integrations/whatsapp/webhook/poll-vote/', WhatsAppPollWebhookView.as_view(), name='api-v1-whatsapp-poll-webhook'),
    path('integrations/resend/webhook/student-invitations/', ResendInvitationWebhookView.as_view(), name='api-v1-resend-student-invitations-webhook'),
    path('debug/init-system/', init_system_view, name='api-v1-init-system'),
    path('exports/download/<str:filename>', SecureExportDownloadView.as_view(), name='api-v1-secure-export-download'),
]
