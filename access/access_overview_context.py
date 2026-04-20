"""
ARQUIVO: contexto da visao geral de acessos.

POR QUE ELE EXISTE:
- tira de `access/views.py` a montagem de perfis e payload da tela de governanca.
"""

from django.contrib.auth import get_user_model

from access.admin import admin_changelist_url, user_can_access_admin
from shared_support.page_payloads import build_page_hero, build_page_reading_panel

from .forms import AccessProfileCreateForm, AccessProfileUpdateForm
from .roles import ROLE_DEFINITIONS, get_user_capabilities, get_user_role


def build_access_profile_entries(*, request, forms_by_user_id=None):
    user_model = get_user_model()
    profiles = []
    for user in user_model.objects.order_by('-is_active', 'username').prefetch_related('groups'):
        role = get_user_role(user)
        profile_form = (
            forms_by_user_id[user.id]
            if forms_by_user_id and user.id in forms_by_user_id
            else AccessProfileUpdateForm(
                prefix=f'profile-{user.id}',
                initial={
                    'full_name': build_access_user_full_name(user),
                    'email': user.email,
                    'role': getattr(role, 'slug', ''),
                },
            )
        )
        profiles.append(
            {
                'id': user.id,
                'username': user.username,
                'full_name': build_access_user_full_name(user),
                'email': user.email,
                'role_label': getattr(role, 'label', 'Sem papel definido'),
                'role_slug': getattr(role, 'slug', ''),
                'is_active': user.is_active,
                'is_superuser': user.is_superuser,
                'is_current_user': user.pk == request.user.pk,
                'form': profile_form,
            }
        )
    return profiles


def build_access_user_full_name(user):
    full_name = user.get_full_name().strip()
    return full_name or user.username


def build_access_overview_context(view, *, context, profile_create_form=None, forms_by_user_id=None):
    current_role = get_user_role(view.request.user)
    role_capabilities = get_user_capabilities(view.request.user)
    role_definitions = ROLE_DEFINITIONS
    can_manage_access_profiles = view._can_manage_access_profiles()
    access_profiles_panel_open = (
        view.request.GET.get('manage_profiles') == '1' or bool(forms_by_user_id)
    )

    context['current_role'] = current_role
    context['role_definitions'] = role_definitions
    context['can_manage_access_profiles'] = can_manage_access_profiles
    context['access_profiles_panel_open'] = access_profiles_panel_open
    context['profile_create_form'] = profile_create_form or AccessProfileCreateForm()
    context['access_profiles'] = build_access_profile_entries(
        request=view.request,
        forms_by_user_id=forms_by_user_id,
    )
    context['page_title'] = 'Papeis e acessos'
    context['page_subtitle'] = 'Quem decide o que e onde cada papel para.'
    context['hero_stats'] = [
        {'label': 'Papel atual', 'value': current_role.label},
        {'label': 'Capacidades do papel', 'value': len(role_capabilities)},
        {'label': 'Papeis formais', 'value': len(role_definitions)},
        {'label': 'Fronteira central', 'value': 'Governanca'},
    ]
    context['access_operational_focus'] = []
    context['access_reading_panel'] = build_page_reading_panel(
        items=context['access_operational_focus'],
        primary_href='',
        pill_label='Governanca',
        pill_class='accent',
        class_name='access-reading-panel',
        panel_id='access-command-lane',
    )
    context['access_hero'] = build_page_hero(
        eyebrow='Acessos',
        title='Fronteiras em leitura.',
        copy='Veja quem pode agir, onde cada papel comeca e o que pede cuidado agora.',
        actions=[
            {'label': 'Ver mapa de papeis', 'href': '#access-role-map'},
        ],
        aria_label='Panorama de acessos',
        classes=['access-hero'],
        data_panel='access-hero',
        actions_slot='access-hero-actions',
    )
    context['group_admin_url'] = (
        admin_changelist_url('auth', 'group')
        if user_can_access_admin(view.request.user)
        else ''
    )
    return context
