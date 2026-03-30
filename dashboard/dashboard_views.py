"""
ARQUIVO: view do dashboard principal.

POR QUE ELE EXISTE:
- centraliza a camada HTTP do painel principal do sistema no app real dashboard.

O QUE ESTE ARQUIVO FAZ:
1. injeta o papel atual do usuario no painel.
2. consome o snapshot consolidado do dashboard.

PONTOS CRITICOS:
- alteracoes erradas aqui podem quebrar o painel principal ou o layout autenticado.
"""

import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from access.permissions.mixins import RoleRequiredMixin
from access.roles import ROLE_COACH, ROLE_DEV, ROLE_MANAGER, ROLE_OWNER, ROLE_RECEPTION, get_user_role
from shared_support.page_payloads import attach_page_payload
from .models import DashboardLayoutPreference
from .presentation import build_dashboard_layout, build_dashboard_page
from .dashboard_snapshot_queries import build_dashboard_snapshot


class DashboardView(LoginRequiredMixin, RoleRequiredMixin, TemplateView):
    allowed_roles = (ROLE_OWNER, ROLE_DEV, ROLE_MANAGER, ROLE_RECEPTION, ROLE_COACH)
    template_name = 'dashboard/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()
        month_start = today.replace(day=1)
        current_role = get_user_role(self.request.user)
        role_slug = getattr(current_role, 'slug', '')
        snapshot = build_dashboard_snapshot(today=today, month_start=month_start, role_slug=role_slug)
        preference = DashboardLayoutPreference.objects.filter(user=self.request.user, role_slug=role_slug).only('layout').first()
        context['current_role'] = current_role
        page_payload = build_dashboard_page(
            request_user=self.request.user,
            role_slug=role_slug,
            snapshot=snapshot,
            stored_layout_state=preference.layout if preference else None,
        )
        attach_page_payload(context, payload_key='dashboard_page', payload=page_payload)
        return context


class DashboardLayoutPreferenceView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = (ROLE_OWNER, ROLE_DEV, ROLE_MANAGER, ROLE_RECEPTION, ROLE_COACH)
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        try:
            payload = json.loads(request.body.decode('utf-8') or '{}')
        except json.JSONDecodeError:
            return JsonResponse({'ok': False, 'error': 'invalid-json'}, status=400)

        current_role = get_user_role(request.user)
        role_slug = getattr(current_role, 'slug', '')
        base_layout = build_dashboard_layout(role_slug, stored_layout_state=None)

        if payload.get('reset'):
            DashboardLayoutPreference.objects.filter(user=request.user, role_slug=role_slug).delete()
            return JsonResponse({'ok': True, 'layout': base_layout['layout_state']})

        raw_slots = payload.get('slots')
        raw_collapsed_blocks = payload.get('collapsed_blocks', [])
        raw_hidden_blocks = payload.get('hidden_blocks', [])
        if not isinstance(raw_slots, dict):
            return JsonResponse({'ok': False, 'error': 'invalid-layout'}, status=400)
        if not isinstance(raw_collapsed_blocks, list):
            return JsonResponse({'ok': False, 'error': 'invalid-collapse-state'}, status=400)
        if not isinstance(raw_hidden_blocks, list):
            return JsonResponse({'ok': False, 'error': 'invalid-hidden-state'}, status=400)

        normalized_layout = build_dashboard_layout(
            role_slug,
            stored_layout_state={
                'slots': raw_slots,
                'collapsed_blocks': raw_collapsed_blocks,
                'hidden_blocks': raw_hidden_blocks,
            },
        )['layout_state']

        raw_block_ids = []
        for block_ids in raw_slots.values():
            if isinstance(block_ids, list):
                raw_block_ids.extend(block_ids)
        raw_visible_block_ids = set(raw_block_ids)
        raw_hidden_block_ids = set(raw_hidden_blocks)
        expected_movable_block_ids = sorted(
            block['id']
            for block in base_layout['block_registry']
            if block['movable']
        )
        required_visible_block_ids = {
            block['id']
            for block in base_layout['block_registry']
            if block['movable'] and not block['removable']
        }
        if raw_visible_block_ids & raw_hidden_block_ids:
            return JsonResponse({'ok': False, 'error': 'invalid-blocks'}, status=400)
        if not required_visible_block_ids.issubset(raw_visible_block_ids):
            return JsonResponse({'ok': False, 'error': 'invalid-blocks'}, status=400)
        if sorted(raw_visible_block_ids | raw_hidden_block_ids) != expected_movable_block_ids:
            return JsonResponse({'ok': False, 'error': 'invalid-blocks'}, status=400)

        if sorted(set(raw_collapsed_blocks)) != sorted(set(normalized_layout['collapsed_blocks'])):
            return JsonResponse({'ok': False, 'error': 'invalid-collapsed-blocks'}, status=400)
        if sorted(set(raw_hidden_blocks)) != sorted(set(normalized_layout['hidden_blocks'])):
            return JsonResponse({'ok': False, 'error': 'invalid-hidden-blocks'}, status=400)

        DashboardLayoutPreference.objects.update_or_create(
            user=request.user,
            role_slug=role_slug,
            defaults={'layout': normalized_layout},
        )
        return JsonResponse({'ok': True, 'layout': normalized_layout})
