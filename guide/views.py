"""
ARQUIVO: views do guia interno do sistema.

POR QUE ELE EXISTE:
- traduz a arquitetura do projeto para uma visao visual e pedagogica dentro do app real guide.

O QUE ESTE ARQUIVO FAZ:
1. expoe a pagina Mapa do Sistema.
2. organiza modulos, fluxo, pontos de bug e ordem de leitura.
3. entrega uma visao navegavel para manutencao e estudo.

PONTOS CRITICOS:
- a navegacao por papel vem de context processor global e precisa continuar coerente aqui.
- a estrutura exibida aqui deve acompanhar a organizacao real do projeto.
"""

import json
import os

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView

from access.permissions import RoleRequiredMixin
from access.roles import ROLE_DEV, ROLE_OWNER
from guide.operational_settings_actions import (
    handle_operational_settings_import_submission,
    handle_operational_settings_repeat_window_update,
)
from guide.operational_settings_context import build_latest_lead_import_status
from operations.models import LeadImportDeclaredRange, LeadImportJobStatus, LeadImportSourceType
from operations.services.contact_importer import import_contacts_from_list
from operations.tasks import run_lead_import_job
from shared_support.page_payloads import attach_page_payload

from .presentation import build_operational_settings_page, build_system_map_page


SOURCE_PLATFORM_TO_IMPORT_SOURCE = {
    'whatsapp': LeadImportSourceType.WHATSAPP_LIST,
    'tecnofit': LeadImportSourceType.TECNOFIT_EXPORT,
    'nextfit': LeadImportSourceType.NEXTFIT_EXPORT,
    'ios_vcard': LeadImportSourceType.IPHONE_VCF,
}

LEAD_IMPORT_STATUS_TTL_HOURS = 24

DECLARED_RANGE_FORM_TO_MODEL = {
    'up_to_200': LeadImportDeclaredRange.UP_TO_200,
    'from_201_to_500': LeadImportDeclaredRange.FROM_201_TO_500,
    'from_501_to_2000': LeadImportDeclaredRange.FROM_501_TO_2000,
}

LEAD_IMPORT_STATUS_UI = {
    LeadImportJobStatus.RECEIVED: {
        'title': 'Arquivo de leads recebido',
        'summary': 'A lista foi recebida e esta entrando na trilha de validacao.',
        'tone': 'info',
    },
    LeadImportJobStatus.VALIDATING: {
        'title': 'Arquivo de leads sendo avaliado',
        'summary': 'O sistema esta conferindo volume e regra de processamento da lista.',
        'tone': 'info',
    },
    LeadImportJobStatus.QUEUED: {
        'title': 'Arquivo de leads na fila',
        'summary': 'A lista esta aguardando o worker iniciar o processamento.',
        'tone': 'info',
    },
    LeadImportJobStatus.SCHEDULED: {
        'title': 'Arquivo de leads agendado para a madrugada',
        'summary': 'A lista ficou na trilha economica noturna e sera processada na janela configurada.',
        'tone': 'info',
    },
    LeadImportJobStatus.RUNNING: {
        'title': 'Arquivo de leads sendo avaliado',
        'summary': 'O processamento da lista esta em andamento agora.',
        'tone': 'info',
    },
    LeadImportJobStatus.COMPLETED: {
        'title': 'Importacao de leads concluida',
        'summary': 'A ultima lista terminou sem alertas operacionais.',
        'tone': 'success',
    },
    LeadImportJobStatus.COMPLETED_WITH_WARNINGS: {
        'title': 'Importacao de leads concluida com alertas',
        'summary': 'A lista terminou, mas houve duplicatas ou avisos para revisar.',
        'tone': 'warning',
    },
    LeadImportJobStatus.REJECTED: {
        'title': 'Importacao de leads bloqueada',
        'summary': 'A ultima tentativa nao entrou no pipeline por causa da policy ou do volume.',
        'tone': 'warning',
    },
    LeadImportJobStatus.FAILED: {
        'title': 'Importacao de leads falhou',
        'summary': 'A lista entrou no pipeline, mas a execucao nao terminou com sucesso.',
        'tone': 'danger',
    },
}


class SystemMapView(LoginRequiredMixin, TemplateView):
    template_name = 'guide/system-map.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        page_payload = build_system_map_page()
        attach_page_payload(
            context,
            payload_key='system_map_page',
            payload=page_payload,
        )
        return context


@method_decorator(csrf_exempt, name='dispatch')
class OperationalSettingsAutoImportApiView(View):
    """
    Endpoint para ingestao de contatos via JSON (Automacao WhatsApp).
    Usa OCTOBOX_INTERNAL_API_TOKEN para seguranca em vez de sessao/CSRF.
    """

    def post(self, request, *args, **kwargs):
        from django.utils.crypto import constant_time_compare

        auth_header = request.headers.get('Authorization', '')
        allowed_token = os.getenv('OCTOBOX_INTERNAL_API_TOKEN')

        is_token_valid = allowed_token and constant_time_compare(auth_header, f"Bearer {allowed_token}")

        if not is_token_valid:
            return JsonResponse({'error': 'Acesso negado. Token invalido ou ausente.'}, status=403)

        client_ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', '')).split(',')[0].strip()
        allowed_ips = os.getenv('OCTOBOX_INTERNAL_API_IPS')
        if allowed_ips:
            safe_ips = [ip.strip() for ip in allowed_ips.split(',') if ip.strip()]
            if client_ip not in safe_ips:
                return JsonResponse({'error': f'Acesso negado. IP ({client_ip}) nao autorizado por politica.'}, status=403)

        try:
            data = json.loads(request.body)
            contact_list = data.get('contacts', []) if isinstance(data, dict) else data
            source = data.get('source_platform', 'whatsapp') if isinstance(data, dict) else 'whatsapp'

            if not isinstance(contact_list, list):
                return JsonResponse({'error': 'Formato invalido. Esperava uma lista.'}, status=400)

            from django.contrib.auth.models import User

            actor = User.objects.filter(is_superuser=True).first()
            report = import_contacts_from_list(contact_list, source_platform=source, actor=actor)
            return JsonResponse(report)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'JSON invalido'}, status=400)
        except Exception as exc:
            return JsonResponse({'error': str(exc)}, status=500)


class OperationalSettingsView(LoginRequiredMixin, RoleRequiredMixin, TemplateView):
    allowed_roles = (ROLE_OWNER, ROLE_DEV)
    template_name = 'guide/operational-settings.html'

    def post(self, request, *args, **kwargs):
        if 'contacts_file' in request.FILES:
            file_obj = request.FILES['contacts_file']
            source_platform = request.POST.get('source_platform', 'whatsapp')
            source_type = SOURCE_PLATFORM_TO_IMPORT_SOURCE.get(source_platform, LeadImportSourceType.WHATSAPP_LIST)
            declared_range = DECLARED_RANGE_FORM_TO_MODEL.get(
                request.POST.get('declared_range', LeadImportDeclaredRange.UP_TO_200),
                LeadImportDeclaredRange.UP_TO_200,
            )

            handle_operational_settings_import_submission(
                request=request,
                file_obj=file_obj,
                source_platform=source_platform,
                source_type=source_type,
                declared_range=declared_range,
                dispatch_async_now_import_fn=lambda job: run_lead_import_job.delay(job.id),
            )
            return redirect('operational-settings')

        handle_operational_settings_repeat_window_update(
            request=request,
            raw_value=request.POST.get('repeat_block_hours', ''),
        )
        return redirect('operational-settings')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        page_payload = build_operational_settings_page(
            latest_lead_import_status=build_latest_lead_import_status(
                request=self.request,
                status_ttl_hours=LEAD_IMPORT_STATUS_TTL_HOURS,
                status_ui=LEAD_IMPORT_STATUS_UI,
            ),
        )
        attach_page_payload(
            context,
            payload_key='operational_settings_page',
            payload=page_payload,
        )
        return context
