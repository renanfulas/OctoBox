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

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView

from access.permissions import RoleRequiredMixin
from access.roles import ROLE_DEV, ROLE_OWNER
from operations.models import LeadImportDeclaredRange, LeadImportJobStatus, LeadImportProcessingMode, LeadImportSourceType
from operations.services.contact_importer import import_contacts_from_list, import_contacts_from_stream
from operations.services.lead_import_orchestrator import orchestrate_lead_import_submission
from operations.tasks import run_lead_import_job
from shared_support.page_payloads import attach_page_payload
from shared_support.operational_settings import set_operational_whatsapp_repeat_block_hours

from .presentation import build_operational_settings_page, build_system_map_page


SOURCE_PLATFORM_TO_IMPORT_SOURCE = {
    'whatsapp': LeadImportSourceType.WHATSAPP_LIST,
    'tecnofit': LeadImportSourceType.TECNOFIT_EXPORT,
    'nextfit': LeadImportSourceType.NEXTFIT_EXPORT,
    'ios_vcard': LeadImportSourceType.IPHONE_VCF,
}

DECLARED_RANGE_FORM_TO_MODEL = {
    'up_to_200': LeadImportDeclaredRange.UP_TO_200,
    'from_201_to_500': LeadImportDeclaredRange.FROM_201_TO_500,
    'from_501_to_2000': LeadImportDeclaredRange.FROM_501_TO_2000,
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

    def _apply_sync_import_job(self, *, job, source_platform):
        with open(job.file_path, 'rb') as stream:
            report = import_contacts_from_stream(
                stream,
                source_platform=source_platform,
                actor=job.created_by,
            )

        job.success_count = report['success']
        job.duplicate_count = report['duplicates']
        job.error_count = report['errors']
        job.duplicate_details = report.get('duplicate_details', [])
        job.error_details = report.get(
            'error_details',
            [{'reason_message': detail} for detail in report.get('details', [])],
        )
        job.status = (
            LeadImportJobStatus.COMPLETED_WITH_WARNINGS
            if report['duplicates'] > 0 or report['errors'] > 0
            else LeadImportJobStatus.COMPLETED
        )
        job.finished_at = timezone.now()
        job.save(
            update_fields=[
                'success_count',
                'duplicate_count',
                'error_count',
                'duplicate_details',
                'error_details',
                'status',
                'finished_at',
                'updated_at',
            ]
        )
        return report

    def _emit_sync_import_messages(self, *, request, report):
        if report['success'] > 0:
            messages.success(request, f"{report['success']} contatos importados com sucesso.")
        if report['duplicates'] > 0:
            messages.warning(request, f"{report['duplicates']} contatos ja existiam no banco e foram ignorados.")
        if report['errors'] > 0:
            error_list = report['details'][:3]
            error_msg = f"Houve {report['errors']} erros de processamento: " + "; ".join(error_list)
            if len(report['details']) > 3:
                error_msg += f" (...mais {len(report['details']) - 3} falhas)"
            messages.error(request, error_msg)
        if report['success'] == 0 and report['duplicates'] == 0 and report['errors'] == 0:
            messages.info(request, 'Nenhum contato encontrado para processar no arquivo.')

    def _dispatch_async_now_import(self, *, job):
        run_lead_import_job.delay(job.id)

    def post(self, request, *args, **kwargs):
        if 'contacts_file' in request.FILES:
            file_obj = request.FILES['contacts_file']
            source_platform = request.POST.get('source_platform', 'whatsapp')
            source_type = SOURCE_PLATFORM_TO_IMPORT_SOURCE.get(source_platform, LeadImportSourceType.WHATSAPP_LIST)
            declared_range = DECLARED_RANGE_FORM_TO_MODEL.get(
                request.POST.get('declared_range', LeadImportDeclaredRange.UP_TO_200),
                LeadImportDeclaredRange.UP_TO_200,
            )

            orchestration = orchestrate_lead_import_submission(
                file_obj=file_obj,
                source_type=source_type,
                declared_range=declared_range,
                actor=request.user,
            )

            if not orchestration.policy_decision.allowed:
                messages.error(request, orchestration.policy_decision.reason_message)
                return redirect('operational-settings')

            if orchestration.job.processing_mode == LeadImportProcessingMode.SYNC:
                report = self._apply_sync_import_job(
                    job=orchestration.job,
                    source_platform=source_platform,
                )
                self._emit_sync_import_messages(request=request, report=report)
            elif orchestration.job.processing_mode == LeadImportProcessingMode.ASYNC_NOW:
                self._dispatch_async_now_import(job=orchestration.job)
                messages.info(
                    request,
                    'Sua importacao foi enviada para processamento em background. Voce pode continuar navegando normalmente.',
                )
            elif orchestration.job.processing_mode == LeadImportProcessingMode.ASYNC_NIGHT:
                messages.info(
                    request,
                    'Sua importacao foi agendada para processamento economico noturno.',
                )

            return redirect('operational-settings')

        raw_value = request.POST.get('repeat_block_hours', '')
        try:
            set_operational_whatsapp_repeat_block_hours(hours=raw_value, actor=request.user)
        except ValueError:
            messages.error(request, 'Escolha apenas 24h, 12h ou 0h para a janela do WhatsApp.')
        else:
            messages.success(request, 'Janela de bloqueio do WhatsApp atualizada com sucesso.')
        return redirect('operational-settings')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        page_payload = build_operational_settings_page()
        attach_page_payload(
            context,
            payload_key='operational_settings_page',
            payload=page_payload,
        )
        return context
