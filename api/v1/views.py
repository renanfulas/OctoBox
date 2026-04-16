"""
ARQUIVO: views base e neutras da API v1.

POR QUE ELE EXISTE:
- Mantem as entradas mais estaveis e pequenas da v1 em um modulo simples de descoberta.

O QUE ESTE ARQUIVO FAZ:
1. Publica o manifesto da versao v1.
2. Publica um endpoint de saude estavel.
3. Publica o autocomplete de busca global de alunos.
4. Publica o webhook do Resend para convites do app do aluno.

PONTOS CRITICOS:
- Este modulo nao deve voltar a virar corredor misto de integracoes, debug e financeiro.
- Endpoints versionados devem permanecer previsiveis e pequenos.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import JsonResponse
from django.urls import reverse
from django.views import View

from shared_support.box_runtime import get_box_runtime_namespace, get_box_runtime_slug
from student_identity.resend_webhooks import (
    ResendWebhookHeaders,
    ResendWebhookVerificationError,
    process_resend_webhook,
)
from students.models import Student


class ApiV1ManifestView(View):
    def get(self, request, *args, **kwargs):
        return JsonResponse(
            {
                'version': 'v1',
                'status': 'active',
                'resources': {
                    'health': reverse('api-v1-health'),
                    'student_autocomplete': reverse('api-v1-student-autocomplete'),
                    'whatsapp_poll_webhook': reverse('api-v1-whatsapp-poll-webhook'),
                    'student_invitation_resend_webhook': reverse('api-v1-resend-student-invitations-webhook'),
                },
                'scope': [
                    'foundation',
                    'mobile-ready-boundary',
                    'integration-ready-boundary',
                ],
            }
        )


class ApiV1HealthView(View):
    def get(self, request, *args, **kwargs):
        return JsonResponse(
            {
                'status': 'ok',
                'version': 'v1',
                'product': 'OctoBox Control',
                'api_boundary': 'stable-entrypoint',
                'runtime_slug': get_box_runtime_slug(),
                'runtime_namespace': get_box_runtime_namespace(),
            }
        )


class StudentAutocompleteView(LoginRequiredMixin, View):
    """Retorna ate 10 alunos cujo nome, telefone ou CPF contem o termo digitado."""

    def get(self, request, *args, **kwargs):
        query = request.GET.get('q', '').strip()
        if len(query) > 100:
            query = query[:100]

        if len(query) < 1:
            return JsonResponse({'results': []})

        students = (
            Student.objects
            .filter(
                Q(full_name__icontains=query)
                | Q(phone__icontains=query)
                | Q(cpf__icontains=query)
            )
            .order_by('full_name')[:10]
        )

        results = [
            {
                'id': student.id,
                'name': student.full_name,
                'phone': student.phone,
                'status': student.get_status_display(),
                'status_raw': student.status,
                'url': reverse('student-quick-update', args=[student.id]),
            }
            for student in students
        ]

        return JsonResponse({'results': results})


class ResendInvitationWebhookView(View):
    def post(self, request, *args, **kwargs):
        headers = ResendWebhookHeaders(
            webhook_id=request.headers.get('svix-id', '').strip(),
            timestamp=request.headers.get('svix-timestamp', '').strip(),
            signature=request.headers.get('svix-signature', '').strip(),
        )
        if not headers.webhook_id or not headers.timestamp or not headers.signature:
            return JsonResponse({'accepted': False, 'reason': 'Missing Svix headers'}, status=400)

        try:
            result = process_resend_webhook(payload=request.body, headers=headers)
        except ResendWebhookVerificationError as exc:
            return JsonResponse({'accepted': False, 'reason': str(exc)}, status=400)

        return JsonResponse(result, status=200)
