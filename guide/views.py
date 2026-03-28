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
from django.shortcuts import redirect
from django.views.generic import TemplateView

from access.permissions import RoleRequiredMixin
from access.roles import ROLE_DEV, ROLE_OWNER
from shared_support.page_payloads import attach_page_payload
from shared_support.operational_settings import set_operational_whatsapp_repeat_block_hours

from .presentation import build_operational_settings_page, build_system_map_page
from operations.services.contact_importer import import_contacts_from_stream


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

from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.http import JsonResponse
from django.views import View
from operations.services.contact_importer import import_contacts_from_list

@method_decorator(csrf_exempt, name='dispatch')
class OperationalSettingsAutoImportApiView(View):  # Removido LoginRequiredMixin por ser API Token
    """
    Endpoint para ingestão de contatos via JSON (Automação WhatsApp).
    Usa OCTOBOX_INTERNAL_API_TOKEN para segurança em vez de sessão/CSRF.
    """
    def post(self, request, *args, **kwargs):
        # 🚀 Segurança de Elite (Ghost Hardening): Constant Time Compare
        from django.utils.crypto import constant_time_compare
        
        auth_header = request.headers.get('Authorization', '')
        allowed_token = os.getenv('OCTOBOX_INTERNAL_API_TOKEN')

        is_token_valid = allowed_token and constant_time_compare(auth_header, f"Bearer {allowed_token}")

        if not is_token_valid:
            return JsonResponse({'error': 'Acesso negado. Token inválido ou ausente.'}, status=403)
            
        # 🚀 Segurança de Elite (Epic 8 Hardening): IP Allowlist
        # Se a variável OCTOBOX_INTERNAL_API_IPS existir, verificamos o Range
        client_ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', '')).split(',')[0].strip()
        allowed_ips = os.getenv('OCTOBOX_INTERNAL_API_IPS')
        if allowed_ips:
            safe_ips = [ip.strip() for ip in allowed_ips.split(',') if ip.strip()]
            if client_ip not in safe_ips:
                return JsonResponse({'error': f'Acesso negado. IP ({client_ip}) não autorizado por política.'}, status=403)
            
        try:
            data = json.loads(request.body)
            # Suporta {'contacts': [...]} ou [...] direto
            contact_list = data.get('contacts', []) if isinstance(data, dict) else data
            source = data.get('source_platform', 'whatsapp') if isinstance(data, dict) else 'whatsapp'
            
            if not isinstance(contact_list, list):
                return JsonResponse({'error': 'Formato inválido. Esperava uma lista.'}, status=400)
                
            # Como a API agora é externa via Token, usamos o primeiro SuperUser ou None se não houver
            from django.contrib.auth.models import User
            actor = User.objects.filter(is_superuser=True).first()
            
            report = import_contacts_from_list(contact_list, source_platform=source, actor=actor)
            return JsonResponse(report)
            
        except json.JSONDecodeError:
            return JsonResponse({'error': 'JSON Inválido'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


class OperationalSettingsView(LoginRequiredMixin, RoleRequiredMixin, TemplateView):
    allowed_roles = (ROLE_OWNER, ROLE_DEV)
    template_name = 'guide/operational-settings.html'

    def post(self, request, *args, **kwargs):
        # 1. Importação de Contatos
        if 'contacts_file' in request.FILES:
            file_obj = request.FILES['contacts_file']
            source = request.POST.get('source_platform', 'whatsapp')
            report = import_contacts_from_stream(file_obj.file, source_platform=source, actor=request.user)
            
            if report['success'] > 0:
                messages.success(request, f"{report['success']} contatos importados com sucesso.")
            if report['duplicates'] > 0:
                messages.warning(request, f"{report['duplicates']} contatos já existiam no banco e foram ignorados.")
            if report['errors'] > 0:
                error_list = report['details'][:3]
                error_msg = f"Houve {report['errors']} erros de processamento: " + "; ".join(error_list)
                if len(report['details']) > 3:
                     error_msg += f" (...mais {len(report['details']) - 3} falhas)"
                messages.error(request, error_msg)
                
            if report['success'] == 0 and report['duplicates'] == 0 and report['errors'] == 0:
                messages.info(request, "Nenhum contato encontrado para processar no arquivo.")
                
            return redirect('operational-settings')

        # 2. Bloqueio do WhatsApp (original)
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