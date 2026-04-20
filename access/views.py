"""
ARQUIVO: views do modulo de acesso.

POR QUE ELE EXISTE:
- Concentra as telas e redirecionamentos ligados ao login e aos papeis do sistema.

O QUE ESTE ARQUIVO FAZ:
1. Redireciona a raiz para login ou dashboard.
2. Monta a tela de visao geral de papeis e capacidades.

PONTOS CRITICOS:
- Alteracoes erradas nos redirecionamentos mudam o fluxo inicial do sistema.
- O contexto current_role e usado pelo layout e nao deve desaparecer.
"""

from django.apps import apps
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from django.views.decorators.csrf import ensure_csrf_cookie

from access.access_overview_context import build_access_overview_context
from access.access_profile_actions import (
    handle_access_profile_create,
    handle_access_profile_toggle,
    handle_access_profile_update,
)
from .roles import ROLE_DEV, ROLE_OWNER, ROLE_PERMISSION_MAP, get_user_role


def _ensure_role_group(role_slug):
    group, _ = Group.objects.get_or_create(name=role_slug)
    permission_map = ROLE_PERMISSION_MAP.get(role_slug, {})
    if not permission_map:
        return group

    model_index = {model._meta.model_name: model for model in apps.get_models()}
    permissions = []
    for model_name, actions in permission_map.items():
        model = model_index[model_name]
        content_type = ContentType.objects.get_for_model(model)
        codenames = [f'{action}_{model_name}' for action in actions]
        permissions.extend(Permission.objects.filter(content_type=content_type, codename__in=codenames))
    group.permissions.set(permissions)
    return group


from django.contrib.auth.views import LoginView
from .forms import AccessAuthenticationForm
from shared_support.security.anti_cheat_throttles import LoginBruteForceThrottle

class ThrottledLoginView(LoginView):
    template_name = 'access/login.html'
    authentication_form = AccessAuthenticationForm

    def post(self, request, *args, **kwargs):
        # A interceptacao L7 foca apenas em acoes de POST para contar tentativa de login,
        # impedindo botneteadores de credential stuffing. 
        throttle = LoginBruteForceThrottle()
        if not throttle.allow_request(request, self):
            throttle.on_throttle_exceeded(request, self)
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Multiplas requisicoes suspeitas. Conta temporariamente bloqueada (Cooldown: 10 min).")
            
        return super().post(request, *args, **kwargs)


@method_decorator(ensure_csrf_cookie, name='dispatch')
class AccessEntryHubView(TemplateView):
    template_name = 'access/login_hub.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        next_url = (self.request.GET.get('next') or '').strip()
        invite_token = (self.request.GET.get('invite') or '').strip()
        context['next'] = next_url
        context['invite_token'] = invite_token
        context['staff_login_url'] = reverse('login-staff')
        if next_url:
            context['staff_login_url'] = f"{context['staff_login_url']}?next={next_url}"
        context['student_google_url'] = reverse(
            'student-identity-oauth-start',
            kwargs={'provider': 'google'},
        )
        context['student_apple_url'] = reverse(
            'student-identity-oauth-start',
            kwargs={'provider': 'apple'},
        )
        if invite_token:
            context['student_google_url'] = f"{context['student_google_url']}?invite={invite_token}"
            context['student_apple_url'] = f"{context['student_apple_url']}?invite={invite_token}"
        return context

    def post(self, request, *args, **kwargs):
        """
        Mantem compatibilidade com clientes antigos e testes que ainda postam em /login/.
        """
        return ThrottledLoginView.as_view()(request, *args, **kwargs)


class HomeRedirectView(TemplateView):
    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('role-operations')
        return redirect('login')


class AccessOverviewView(LoginRequiredMixin, TemplateView):
    template_name = 'access/overview.html'

    def _can_manage_access_profiles(self):
        current_role = get_user_role(self.request.user)
        return getattr(current_role, 'slug', '') in (ROLE_OWNER, ROLE_DEV)

    def post(self, request, *args, **kwargs):
        if not self._can_manage_access_profiles():
            messages.error(request, 'Seu papel atual pode consultar acessos, mas nao gerenciar perfis por esta tela.')
            return redirect('access-overview')

        access_action = request.POST.get('access_action', 'create')
        if access_action == 'update':
            result = handle_access_profile_update(
                post_data=request.POST,
                ensure_role_group=_ensure_role_group,
            )
            if not result['ok']:
                if result['reason'] == 'invalid-form':
                    context = self.get_context_data(forms_by_user_id=result['forms_by_user_id'])
                    return self.render_to_response(context)
                messages.error(request, 'Perfil nao encontrado para atualizacao.')
                return redirect('access-overview')

            messages.success(request, f'Perfil de {result["user"].username} atualizado com sucesso.')
            return redirect('access-overview')

        if access_action == 'toggle_active':
            result = handle_access_profile_toggle(
                actor=request.user,
                post_data=request.POST,
            )
            if not result['ok']:
                if result['reason'] == 'self-disable-blocked':
                    messages.error(request, 'Nao e permitido desativar o proprio usuario por esta tela.')
                else:
                    messages.error(request, 'Perfil nao encontrado para alteracao de status.')
                return redirect('access-overview')

            status_label = 'ativado' if result['user'].is_active else 'desativado'
            messages.success(request, f'Perfil de {result["user"].username} {status_label} com sucesso.')
            return redirect('access-overview')

        result = handle_access_profile_create(
            post_data=request.POST,
            ensure_role_group=_ensure_role_group,
        )
        if not result['ok']:
            context = self.get_context_data(profile_create_form=result['form'])
            return self.render_to_response(context)

        messages.success(
            request,
            f'Perfil criado para {result["user"].get_full_name() or result["user"].username} com o papel {result["group"].name}.',
        )
        return redirect('access-overview')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return build_access_overview_context(
            self,
            context=context,
            profile_create_form=kwargs.get('profile_create_form'),
            forms_by_user_id=kwargs.get('forms_by_user_id'),
        )


