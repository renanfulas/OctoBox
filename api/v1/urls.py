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

from .finance_views import PaymentLinkView, StudentFreezeView
from .integrations_views import WhatsAppPollWebhookView
from .internal_views import init_system_view
from .jobs_views import SecureExportDownloadView
from knowledge.views import (
    ProjectKnowledgeAnswerView,
    ProjectKnowledgeHealthView,
    ProjectKnowledgeReindexView,
    ProjectKnowledgeSearchView,
)
from .views import (
    ApiV1HealthView,
    ApiV1ManifestView,
    ResendInvitationWebhookView,
    StudentAutocompleteView,
)


urlpatterns = [
    path('', ApiV1ManifestView.as_view(), name='api-v1-manifest'),
    path('health/', ApiV1HealthView.as_view(), name='api-v1-health'),
    path('students/autocomplete/', StudentAutocompleteView.as_view(), name='api-v1-student-autocomplete'),
    path('finance/payment-link/<int:payment_id>/', PaymentLinkView.as_view(), name='api-v1-payment-link'),
    path('finance/freeze-student/', StudentFreezeView.as_view(), name='api-v1-finance-freeze'),
    path('integrations/whatsapp/webhook/poll-vote/', WhatsAppPollWebhookView.as_view(), name='api-v1-whatsapp-poll-webhook'),
    path('integrations/resend/webhook/student-invitations/', ResendInvitationWebhookView.as_view(), name='api-v1-resend-student-invitations-webhook'),
    path('project-rag/health/', ProjectKnowledgeHealthView.as_view(), name='api-v1-project-rag-health'),
    path('project-rag/search/', ProjectKnowledgeSearchView.as_view(), name='api-v1-project-rag-search'),
    path('project-rag/answer/', ProjectKnowledgeAnswerView.as_view(), name='api-v1-project-rag-answer'),
    path('project-rag/reindex/', ProjectKnowledgeReindexView.as_view(), name='api-v1-project-rag-reindex'),
    path('debug/init-system/', init_system_view, name='api-v1-init-system'),
    path('exports/download/<str:filename>', SecureExportDownloadView.as_view(), name='api-v1-secure-export-download'),
]
