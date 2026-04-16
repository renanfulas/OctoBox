"""
ARQUIVO: views internas e transitorias da API v1.

POR QUE ELE EXISTE:
- Isola endpoints internos sensiveis e explicitamente transitivos para nao poluir a base neutra da API.

O QUE ESTE ARQUIVO FAZ:
1. Hospeda endpoints internos de bootstrap controlado.
2. Mantem o risco concentrado em um modulo claramente sensivel.

PONTOS CRITICOS:
- Este modulo nao deve crescer como area generica de excecao.
- Endpoints daqui exigem postura fechada, criterio operacional e futura aposentadoria.
"""

import os

from django.contrib.auth.models import User
from django.core.management import call_command
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
def init_system_view(request):
    """
    Endpoint seguro para rodar migrates e criar usuario admin em ambiente controlado.
    """
    if os.getenv('DJANGO_ENV') == 'production':
        return JsonResponse({"status": "forbidden", "reason": "Init system disabled in production"}, status=403)

    if os.getenv('FEATURE_INIT_ENABLED') != 'true':
        return JsonResponse({"status": "forbidden", "reason": "Init system is strictly disabled by policy."}, status=403)

    secret = request.GET.get('secret')
    env_secret = os.getenv('INIT_SECRET')
    if not env_secret or secret != env_secret:
        return JsonResponse({"status": "forbidden", "reason": "Secret incorreto ou nao configurado no servidor."}, status=403)

    output = []
    try:
        call_command('migrate', interactive=False)
        output.append("Banco de Dados Migrado com Sucesso!")

        username = "admin"
        email = "admin@octobox.com"
        password = "adminpassword123"

        if not User.objects.filter(username=username).exists():
            User.objects.create_superuser(username, email, password)
            output.append(f"Usuario '{username}' criado com sucesso. Senha: '{password}'")
        else:
            output.append(f"Usuario '{username}' ja existe.")

        return JsonResponse({"status": "success", "steps": output})
    except Exception as exc:
        return JsonResponse({"status": "error", "error": str(exc)}, status=500)
