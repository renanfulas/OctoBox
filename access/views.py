"""
ARQUIVO: views do modulo de acesso.

POR QUE ELE EXISTE:
- Concentra as telas e redirecionamentos ligados ao login e aos Papéis do sistema.

O QUE ESTE ARQUIVO FAZ:
1. Redireciona a raiz para login ou dashboard.
2. Monta a tela de visao geral de Papéis e capacidades.

PONTOS CRITICOS:
- Alteracoes erradas nos redirecionamentos mudam o fluxo inicial do sistema.
- O contexto current_role e usado pelo layout e nao deve desaparecer.
"""

from django.apps import apps
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.shortcuts import redirect
from django.views.generic import TemplateView

from access.admin import admin_changelist_url, user_can_access_admin
from access.shell_actions import attach_shell_action_buttons
from shared_support.page_payloads import build_page_hero
from .forms import AccessProfileCreateForm, AccessProfileUpdateForm
from .roles import ROLE_DEFINITIONS, ROLE_DEV, ROLE_OWNER, ROLE_PERMISSION_MAP, get_user_capabilities, get_user_role


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


def _split_full_name(full_name):
    chunks = full_name.split()
    if not chunks:
        return '', ''
    if len(chunks) == 1:
        return chunks[0], ''
    return chunks[0], ' '.join(chunks[1:])


def _build_full_name(user):
    full_name = user.get_full_name().strip()
    return full_name or user.username


from django.contrib.auth.views import LoginView
from .forms import AccessAuthenticationForm
from shared_support.security.anti_cheat_throttles import LoginBruteForceThrottle

class ThrottledLoginView(LoginView):
    template_name = 'access/login.html'
    authentication_form = AccessAuthenticationForm

    def post(self, request, *args, **kwargs):
        # A interceptação L7 foca apenas em ações de POST para contar tentativa de login, 
        # impedindo botneteadores de credential stuffing. 
        throttle = LoginBruteForceThrottle()
        if not throttle.allow_request(request, self):
            throttle.on_throttle_exceeded(request, self)
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Múltiplas requisições suspeitas. Conta temporariamente bloqueada (Cooldown: 10 min).")
            
        return super().post(request, *args, **kwargs)


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

    def _get_profile_queryset(self):
        user_model = get_user_model()
        return user_model.objects.order_by('-is_active', 'username').prefetch_related('groups')

    def _build_access_profiles(self, *, forms_by_user_id=None):
        profiles = []
        for user in self._get_profile_queryset():
            role = get_user_role(user)
            profile_form = None
            if forms_by_user_id and user.id in forms_by_user_id:
                profile_form = forms_by_user_id[user.id]
            else:
                profile_form = AccessProfileUpdateForm(
                    prefix=f'profile-{user.id}',
                    initial={
                        'full_name': _build_full_name(user),
                        'email': user.email,
                        'role': getattr(role, 'slug', ''),
                    },
                )
            profiles.append({
                'id': user.id,
                'username': user.username,
                'full_name': _build_full_name(user),
                'email': user.email,
                'role_label': getattr(role, 'label', 'Sem papel definido'),
                'role_slug': getattr(role, 'slug', ''),
                'is_active': user.is_active,
                'is_superuser': user.is_superuser,
                'is_current_user': user.pk == self.request.user.pk,
                'form': profile_form,
            })
        return profiles

    def post(self, request, *args, **kwargs):
        if not self._can_manage_access_profiles():
            messages.error(request, 'Seu papel atual pode consultar acessos, mas nao gerenciar perfis por esta tela.')
            return redirect('access-overview')

        access_action = request.POST.get('access_action', 'create')
        if access_action == 'update':
            profile_id = request.POST.get('target_profile_id', '').strip()
            form = AccessProfileUpdateForm(request.POST, prefix=f'profile-{profile_id}')
            if not form.is_valid():
                forms_by_user_id = {}
                if profile_id.isdigit():
                    forms_by_user_id[int(profile_id)] = form
                context = self.get_context_data(forms_by_user_id=forms_by_user_id)
                return self.render_to_response(context)

            user_model = get_user_model()
            target_user = user_model.objects.filter(pk=profile_id).first()
            if target_user is None:
                messages.error(request, 'Perfil nao encontrado para atualizacao.')
                return redirect('access-overview')

            role_slug = form.cleaned_data['role']
            first_name, last_name = _split_full_name(form.cleaned_data['full_name'])
            with transaction.atomic():
                target_user.first_name = first_name
                target_user.last_name = last_name
                target_user.email = form.cleaned_data['email']
                target_user.save(update_fields=['first_name', 'last_name', 'email'])
                group = _ensure_role_group(role_slug)
                target_user.groups.set([group])

            messages.success(request, f'Perfil de {target_user.username} atualizado com sucesso.')
            return redirect('access-overview')

        if access_action == 'toggle_active':
            profile_id = request.POST.get('target_profile_id', '').strip()
            user_model = get_user_model()
            target_user = user_model.objects.filter(pk=profile_id).first()
            if target_user is None:
                messages.error(request, 'Perfil nao encontrado para alteracao de status.')
                return redirect('access-overview')
            if target_user.pk == request.user.pk and target_user.is_active:
                messages.error(request, 'Nao e permitido desativar o proprio usuario por esta tela.')
                return redirect('access-overview')

            target_user.is_active = not target_user.is_active
            target_user.save(update_fields=['is_active'])
            status_label = 'ativado' if target_user.is_active else 'desativado'
            messages.success(request, f'Perfil de {target_user.username} {status_label} com sucesso.')
            return redirect('access-overview')

        form = AccessProfileCreateForm(request.POST)
        if not form.is_valid():
            context = self.get_context_data(profile_create_form=form)
            return self.render_to_response(context)

        user_model = get_user_model()
        username = form.cleaned_data['username']
        if user_model.objects.filter(username=username).exists():
            form.add_error('username', 'Ja existe um usuario com esse identificador.')
            context = self.get_context_data(profile_create_form=form)
            return self.render_to_response(context)

        role_slug = form.cleaned_data['role']
        first_name, last_name = _split_full_name(form.cleaned_data['full_name'])
        with transaction.atomic():
            user = user_model.objects.create_user(
                username=username,
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password'],
                first_name=first_name,
                last_name=last_name,
            )
            group = _ensure_role_group(role_slug)
            user.groups.set([group])

        messages.success(request, f'Perfil criado para {user.get_full_name() or user.username} com o papel {group.name}.')
        return redirect('access-overview')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        current_role = get_user_role(self.request.user)
        role_capabilities = get_user_capabilities(self.request.user)
        role_definitions = ROLE_DEFINITIONS
        can_manage_access_profiles = self._can_manage_access_profiles()
        access_profiles_panel_open = self.request.GET.get('manage_profiles') == '1' or bool(kwargs.get('forms_by_user_id'))

        context['current_role'] = current_role
        context['role_capabilities'] = role_capabilities
        context['role_definitions'] = role_definitions
        context['can_manage_access_profiles'] = can_manage_access_profiles
        context['access_profiles_panel_open'] = access_profiles_panel_open
        context['profile_create_form'] = kwargs.get('profile_create_form') or AccessProfileCreateForm()
        context['access_profiles'] = self._build_access_profiles(forms_by_user_id=kwargs.get('forms_by_user_id'))
        context['page_title'] = 'Papéis e acessos'
        context['page_subtitle'] = 'Quem decide o que e onde cada papel para.'
        context['hero_stats'] = [
            {'label': 'Papel atual', 'value': current_role.label},
            {'label': 'Capacidades do papel', 'value': len(role_capabilities)},
            {'label': 'Papéis formais', 'value': len(role_definitions)},
            {'label': 'Fronteira central', 'value': 'Governanca'},
        ]
        context['access_operational_focus'] = [
            {
                'label': 'Comece pelo seu proprio escopo',
                'chip_label': 'Papel',
                'summary': f'O papel {current_role.label} precisa ficar claro primeiro, para a leitura desta tela nao virar teoria solta sem utilidade operacional.',
                'pill_class': 'accent',
                'href': '#access-current-role',
                'href_label': 'Ver meu escopo',
            },
            {
                'label': 'Depois compare as fronteiras',
                'chip_label': 'Fronteiras',
                'summary': f'{len(role_definitions)} papel(is) ja desenham quem decide crescimento, manutencao, administracao e rotina tecnica sem mistura indevida.',
                'pill_class': 'info',
                'href': '#access-role-map',
                'href_label': 'Ver mapa de Papéis',
            },
            {
                'label': 'Feche com a governança prática',
                'chip_label': 'Governança',
                'summary': 'Grupos e permissoes devem sustentar o desenho do produto, nunca obrigar a operacao a adivinhar limite por tentativa e erro.',
                'pill_class': 'warning',
                'href': '#access-governance-board',
                'href_label': 'Ver governanca',
            },
        ]
        context['access_hero'] = build_page_hero(
            eyebrow='Fronteiras do sistema',
            title='Quem age, quem não invade e onde cada papel começa.',
            copy='Autoridade, fronteira e papel sem ambiguidade.',
            actions=[
                {'label': 'Ver meu escopo', 'href': '#access-current-role'},
                {'label': 'Ver mapa de Papéis', 'href': '#access-role-map', 'kind': 'secondary'},
                *([
                    {'label': 'Gerenciar grupos', 'href': admin_changelist_url('auth', 'group'), 'kind': 'secondary'},
                ] if user_can_access_admin(self.request.user) else []),
            ],
            aria_label='Panorama de acessos',
        )
        context['governance_points'] = [
            'Manager não vira coach por atalho.',
            'Coach não carrega rotina financeira ou administrativa.',
            'DEV investiga e mantém sem virar operador do box.',
            'Owner enxerga amplitude sem dissolver fronteiras entre papéis.',
        ]
        context['group_admin_url'] = admin_changelist_url('auth', 'group') if user_can_access_admin(self.request.user) else ''
        attach_shell_action_buttons(context, focus=context['access_operational_focus'], scope='access')
        return context


