"""
ARQUIVO: views iniciais da API v1.

POR QUE ELE EXISTE:
- Fornece endpoints minimos de saude e manifesto para preparar clientes externos e app mobile.

O QUE ESTE ARQUIVO FAZ:
1. Publica o manifesto da versao v1.
2. Publica um endpoint de saude estavel.
3. Publica o autocomplete de busca global de alunos.

PONTOS CRITICOS:
- Endpoints versionados devem permanecer previsiveis e pequenos.
- O autocomplete limita resultados a 10 e exige autenticacao.
"""

import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from integrations.whatsapp.contracts import WhatsAppInboundPollVote
from integrations.whatsapp.services import process_poll_vote_webhook
from students.models import Student


class ApiV1ManifestView(View):
    def get(self, request, *args, **kwargs):
        return JsonResponse(
            {
                'version': 'v1',
                'status': 'active',
                'resources': {
                    'health': '/api/v1/health/',
                    'student_autocomplete': '/api/v1/students/autocomplete/',
                    'whatsapp_poll_webhook': '/api/v1/integrations/whatsapp/webhook/poll-vote/',
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
            }
        )


class StudentAutocompleteView(LoginRequiredMixin, View):
    """Retorna ate 10 alunos cujo nome, telefone ou CPF contem o termo digitado."""

    def get(self, request, *args, **kwargs):
        query = request.GET.get('q', '').strip()
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
                'id': s.id,
                'name': s.full_name,
                'phone': s.phone,
                'status': s.get_status_display(),
                'status_raw': s.status,
                'url': f'/alunos/{s.id}/editar/',
            }
            for s in students
        ]

        return JsonResponse({'results': results})


@method_decorator(csrf_exempt, name='dispatch')
class WhatsAppPollWebhookView(View):
    """
    Recebe votos de enquete do WhatsApp de um robo externo.
    """

    def post(self, request, *args, **kwargs):
        # 🛡️ Token-based security for incoming webhooks (Epic 8)
        # Falha fechada: Se o servidor não tiver o segredo configurado, negamos o acesso.
        provided_token = request.headers.get('X-OctoBox-Webhook-Token')
        expected_token = os.getenv('WHATSAPP_WEBHOOK_SECRET')
        if not expected_token or provided_token != expected_token:
            return JsonResponse({'accepted': False, 'reason': 'Unauthorized Configuration or Token'}, status=401)

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'accepted': False, 'reason': 'Invalid JSON'}, status=400)

        # Mapeia payload para o contrato
        voter_phone = data.get('voter_phone')
        poll_name = data.get('poll_name')
        option_text = data.get('option_text')

        if not all([voter_phone, poll_name, option_text]):
            return JsonResponse(
                {
                    'accepted': False,
                    'reason': 'Missing required fields: voter_phone, poll_name, option_text',
                },
                status=400,
            )

        vote = WhatsAppInboundPollVote(
            phone=voter_phone,
            poll_title=poll_name,
            option_voted=option_text,
            raw_payload=data,
        )

        result = process_poll_vote_webhook(poll_vote=vote)

        status_code = 200 if result.accepted else 400
        return JsonResponse({'accepted': result.accepted, 'reason': result.reason}, status=status_code)


from django.core.management import call_command
from django.contrib.auth.models import User
import os

@csrf_exempt
def init_system_view(request):
    """
    Endpoint seguro para rodar migrates e criar usuario admin na Vercel.
    """
    if os.getenv('DJANGO_ENV') == 'production':
        return JsonResponse({"status": "forbidden", "reason": "Init system disabled in production"}, status=403)

    # 🚀 Segurança de Elite (Epic 8 Hardening)
    # Exige que FEATURE_INIT_ENABLED seja 'true' explicitamente (Padrão: False/Bloqueado)
    if os.getenv('FEATURE_INIT_ENABLED') != 'true':
        return JsonResponse({"status": "forbidden", "reason": "Init system is strictly disabled by policy."}, status=403)

    secret = request.GET.get('secret')
    env_secret = os.getenv('INIT_SECRET')
    
    if not env_secret or secret != env_secret:
        return JsonResponse({"status": "forbidden", "reason": "Secret incorreto ou não configurado no servidor."}, status=403)

    output = []
    try:
        # 1. Rodas Migrations
        call_command('migrate', interactive=False)
        output.append("✅ Banco de Dados Migrado com Sucesso!")

        # 2. Criar Admin
        username = "admin"
        email = "admin@octobox.com"
        password = "adminpassword123"

        if not User.objects.filter(username=username).exists():
            User.objects.create_superuser(username, email, password)
            output.append(f"✅ Usuário '{username}' criado com sucesso! Senha: '{password}'")
        else:
            output.append(f"ℹ️ Usuário '{username}' já existe.")

        return JsonResponse({"status": "success", "steps": output})

    except Exception as e:
        return JsonResponse({"status": "error", "error": str(e)}, status=500)
