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
from access.permissions.mixins import RoleRequiredMixin
from access.roles import ROLE_COACH, ROLE_DEV, ROLE_MANAGER, ROLE_OWNER, ROLE_RECEPTION
from control.tenant_write_fence import TenantWritesFrozen

from shared_support.box_runtime import (
    get_box_runtime_namespace,
    get_box_runtime_slug,
    get_deployed_commit_sha,
    get_loaded_release_sha,
)
from student_identity.resend_webhooks import (
    ResendWebhookHeaders,
    ResendWebhookTenantUnresolved,
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
    """Healthcheck público (roda em public schema — sem tenant).

    Sprint 4: adicionado tenants_active para observabilidade do control plane.
    Rota listada em PUBLIC_SCHEMA_PATHS do TenantBySessionMiddleware.

    2026-08-27: adicionado deployed_sha. Producao ficou 17 dias rodando codigo
    velho porque nada comparava "o que esta no ar" com "o que devia estar" —
    ver get_deployed_commit_sha() e o job check-deployed-version em
    .github/workflows/deploy-vps.yml.
    """

    def get(self, request, *args, **kwargs):
        tenants_active = 0
        try:
            from control.models import Box
            tenants_active = Box.objects.filter(status=Box.Status.ACTIVE).count()
        except Exception:
            pass
        deployed_sha = get_deployed_commit_sha()
        loaded_sha = get_loaded_release_sha()
        release_consistent = (
            deployed_sha is None and loaded_sha is None
        ) or bool(deployed_sha and loaded_sha and deployed_sha == loaded_sha)
        return JsonResponse(
            {
                'version': 'v1',
                'product': 'OctoBox Control',
                'api_boundary': 'stable-entrypoint',
                'runtime': 'control',
                'runtime_slug': get_box_runtime_slug(),
                'runtime_namespace': get_box_runtime_namespace(),
                'tenants_active': tenants_active,
                'deployed_sha': deployed_sha,
                'loaded_sha': loaded_sha,
                'healthy': release_consistent,
                'release_consistent': release_consistent,
                'status': 'ok' if release_consistent else 'degraded',
            }
        )


class ApiV1TenantHealthView(LoginRequiredMixin, View):
    """Healthcheck autenticado — reporta o tenant resolvido para o request atual.

    Sprint 4: endpoint `/api/v1/health/tenant/` para smoke test por tenant.
    Requer autenticacao (LoginRequiredMixin) pois precisa de tenant resolvido.
    """

    def get(self, request, *args, **kwargs):
        from django.db import connection
        schema = getattr(connection, 'schema_name', 'public')
        tenant = getattr(request, 'tenant', None)
        return JsonResponse(
            {
                'status': 'ok',
                'tenant': schema,
                'tenant_slug': tenant.slug if tenant else '',
                'healthy': schema not in ('public', 'control'),
            }
        )


class StudentAutocompleteView(LoginRequiredMixin, RoleRequiredMixin, View):
    """Retorna ate 10 alunos cujo nome, telefone ou CPF contem o termo digitado."""

    allowed_roles = (ROLE_OWNER, ROLE_DEV, ROLE_MANAGER, ROLE_RECEPTION, ROLE_COACH)

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
        except TenantWritesFrozen:
            response = JsonResponse(
                {'accepted': False, 'reason': 'tenant-temporarily-paused'},
                status=503,
            )
            response['Retry-After'] = '60'
            response['X-Octobox-Tenant-Frozen'] = '1'
            return response
        except ResendWebhookTenantUnresolved:
            response = JsonResponse(
                {'accepted': False, 'reason': 'tenant-association-unresolved'},
                status=503,
            )
            response['Retry-After'] = '300'
            response['X-Octobox-Webhook-Deferred'] = '1'
            return response

        return JsonResponse(result, status=200)
