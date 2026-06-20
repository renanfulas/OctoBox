"""
ARQUIVO: views do modulo de acesso.

POR QUE ELE EXISTE:
- Concentra as telas e redirecionamentos ligados ao login e aos papeis do sistema.

O QUE ESTE ARQUIVO FAZ:
1. Redireciona a raiz para login ou dashboard.
2. Monta a tela de visao geral de papeis e capacidades.
3. Captura intencao de plano (Early Adopters) escolhido na landing.

PONTOS CRITICOS:
- Alteracoes erradas nos redirecionamentos mudam o fluxo inicial do sistema.
- O contexto current_role e usado pelo layout e nao deve desaparecer.
- O parametro `plan` da landing alimenta o checkout pos-login. Aceita apenas
  valores da whitelist (monthly | annual). Qualquer outro valor e ignorado
  silenciosamente para evitar redirect smuggling via querystring.
"""

from urllib.parse import urlencode, urlsplit

from django.apps import apps
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
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


VALID_LANDING_PLANS = ('monthly', 'annual')
LANDING_PLAN_SESSION_KEY = 'landing_intended_plan'


def _normalize_plan(raw_value):
    if not raw_value:
        return ''
    candidate = raw_value.strip().lower()
    return candidate if candidate in VALID_LANDING_PLANS else ''


def _normalized_request_host(request):
    return request.get_host().split(':', 1)[0].strip().lower()


def _configured_app_host():
    configured_base_url = getattr(settings, 'STUDENT_OAUTH_PUBLIC_BASE_URL', '').strip()
    if not configured_base_url:
        return ''
    return (urlsplit(configured_base_url).hostname or '').strip().lower()


def _is_local_host(host):
    return host in {'localhost', '127.0.0.1', 'testserver'}


def _build_app_base_url(request):
    configured_base_url = getattr(settings, 'STUDENT_OAUTH_PUBLIC_BASE_URL', '').strip()
    if configured_base_url:
        return configured_base_url.rstrip('/')

    host = _normalized_request_host(request)
    if _is_local_host(host):
        return ''

    if host.startswith('www.'):
        host = f"app.{host[4:]}"
    elif not host.startswith('app.'):
        host = f'app.{host}'

    scheme = 'https' if request.is_secure() else 'http'
    return f'{scheme}://{host}'


def _build_app_url(request, path):
    app_base_url = _build_app_base_url(request)
    if not app_base_url:
        return path
    return f'{app_base_url}{path}'


def _append_query(url, params):
    if not params:
        return url
    separator = '&' if '?' in url else '?'
    return f"{url}{separator}{urlencode(params)}"


def _request_targets_app_host(request):
    host = _normalized_request_host(request)
    if _is_local_host(host):
        return True

    configured_app_host = _configured_app_host()
    if configured_app_host:
        return host == configured_app_host

    return host.startswith('app.')


class AppHostRequiredMixin:
    def dispatch(self, request, *args, **kwargs):
        if _request_targets_app_host(request):
            return super().dispatch(request, *args, **kwargs)
        return redirect(_build_app_url(request, request.get_full_path()))

class ThrottledLoginView(LoginView):
    # O throttle de login agora vive no RequestSecurityMiddleware (scope 'login',
    # IP confiavel via SECURITY_TRUSTED_PROXY_IPS + RED_FLAG forense deduplicado).
    # A view nao precisa mais de uma camada propria (que era redundante e usava
    # IP spoofavel). Nome mantido por compatibilidade de import/URL.
    template_name = 'access/login.html'
    authentication_form = AccessAuthenticationForm


class AppHostThrottledLoginView(AppHostRequiredMixin, ThrottledLoginView):
    pass


@method_decorator(ensure_csrf_cookie, name='dispatch')
class AccessEntryHubView(AppHostRequiredMixin, TemplateView):
    template_name = 'access/login_hub.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        next_url = (self.request.GET.get('next') or '').strip()
        invite_token = (self.request.GET.get('invite') or '').strip()
        intended_plan = _normalize_plan(self.request.GET.get('plan'))
        if intended_plan:
            self.request.session[LANDING_PLAN_SESSION_KEY] = intended_plan
        else:
            intended_plan = self.request.session.get(LANDING_PLAN_SESSION_KEY, '')
        context['next'] = next_url
        context['invite_token'] = invite_token
        context['intended_plan'] = intended_plan
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
    template_name = 'access/landing.html'

    def get(self, request, *args, **kwargs):
        if _request_targets_app_host(request):
            if request.user.is_authenticated:
                return redirect('role-operations')
            return redirect('login')

        if request.user.is_authenticated:
            return redirect(_build_app_url(request, reverse('role-operations')))
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        login_url = _build_app_url(self.request, reverse('login'))
        context['login_url'] = login_url
        context['login_url_monthly'] = _append_query(login_url, {'plan': 'monthly'})
        context['login_url_annual'] = _append_query(login_url, {'plan': 'annual'})
        context['staff_login_url'] = _build_app_url(self.request, reverse('login-staff'))
        return context


class LandingPreviewView(HomeRedirectView):
    """Renderiza a landing publica em ambiente local sem o redirect de app host.

    EXISTE APENAS PARA DEV/PREVIEW. A rota e registrada em access/urls.py somente
    quando settings.DEBUG e True, evitando exposicao em producao. Util para
    designers e devs que precisam ver a landing sem editar o hosts file.
    """

    def get(self, request, *args, **kwargs):
        return TemplateView.get(self, request, *args, **kwargs)


class ProductPageView(TemplateView):
    """Pagina /produto/ — vitrine comercial de capabilities reais do OctoBox.

    Conteudo construido a partir de auditoria do codigo: cada feature listada
    aqui tem implementacao real em algum dos apps (operations, finance, students,
    student_app, communications, integrations).
    """

    template_name = 'access/product.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['login_url'] = _build_app_url(self.request, reverse('login'))
        return context


class AccessOverviewView(AppHostRequiredMixin, LoginRequiredMixin, TemplateView):
    template_name = 'access/overview.html'

    def _can_manage_access_profiles(self):
        current_role = get_user_role(self.request.user)
        return getattr(current_role, 'slug', '') in (ROLE_OWNER, ROLE_DEV)

    def post(self, request, *args, **kwargs):
        if not self._can_manage_access_profiles():
            messages.error(request, 'Seu papel atual pode consultar acessos, mas não gerenciar perfis por esta tela.')
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
                messages.error(request, 'Perfil não encontrado para atualização.')
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
                    messages.error(request, 'Não é permitido desativar o próprio usuário por esta tela.')
                else:
                    messages.error(request, 'Perfil não encontrado para alteração de status.')
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


class BoxSwitchView(AppHostRequiredMixin, LoginRequiredMixin, TemplateView):
    """Seletor de box para staff com acesso a multiplos boxes (ex.: superdev).

    Roda em public schema (a rota /box/ esta em PUBLIC_SCHEMA_PATHS), pois o
    usuario ainda nao tem tenant resolvido ao escolher. Lista apenas boxes onde
    ele tem Membership ativo — para o superdev (Membership em todos), e a lista
    completa. Ao escolher, seta session['active_box_id'] e manda pro painel.
    """

    template_name = 'access/box_switch.html'

    def _accessible_boxes(self):
        from control.models import Box, Membership

        box_ids = (
            Membership.objects
            .filter(user=self.request.user, box__status=Box.Status.ACTIVE)
            .values_list('box_id', flat=True)
        )
        return (
            Box.objects
            .filter(pk__in=list(box_ids), status=Box.Status.ACTIVE)
            .order_by('display_name')
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['boxes'] = self._accessible_boxes()
        context['active_box_id'] = self.request.session.get('active_box_id')
        context['next'] = (self.request.GET.get('next') or '').strip()
        return context

    def post(self, request, *args, **kwargs):
        from control.models import Box, Membership

        box_id = (request.POST.get('box_id') or '').strip()
        if not box_id.isdigit():
            messages.error(request, 'Selecione um box válido.')
            return redirect('box-switch')

        box = Box.objects.filter(pk=int(box_id), status=Box.Status.ACTIVE).first()
        # Mesma checagem que o TenantBySessionMiddleware faz ao honrar active_box_id:
        # exige Membership real. Superuser sem Membership na box e barrado aqui (e
        # o seria pelo middleware tambem) — o superdev passa porque tem Membership.
        if box is None or not Membership.objects.filter(user=request.user, box=box).exists():
            messages.error(request, 'Você não tem acesso a esse box.')
            return redirect('box-switch')

        request.session['active_box_id'] = box.pk
        messages.success(request, f'Box ativo: {box.display_name}.')

        next_url = (request.POST.get('next') or '').strip()
        if next_url and url_has_allowed_host_and_scheme(
            next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            return redirect(next_url)
        return redirect('role-operations')


