"""
ARQUIVO: contrato compartilhado do shell global.

POR QUE ELE EXISTE:
- centraliza o shape canonico de sidebar, topbar e contexto estrutural da shell.
- reduz payload solto no context processor e prepara fronteiras claras para cache futuro.
"""

SHELL_CHROME_CACHE_RULES = {
    'static_sections': ('brand', 'theme_toggle'),
    'role_scoped_sections': ('sidebar.navigation', 'topbar.quick_links', 'page.scope'),
    'user_scoped_sections': ('sidebar.identity', 'topbar.profile'),
    'volatile_sections': ('topbar.alerts', 'counts'),
}


def build_shell_sidebar_item(*, nav_key, label, href, icon, is_active):
    return {
        'nav_key': nav_key,
        'label': label,
        'href': href,
        'icon': icon,
        'is_active': bool(is_active),
    }


def build_shell_sidebar_payload(*, brand, tagline, user_name, navigation):
    return {
        'brand': brand,
        'tagline': tagline,
        'identity': {
            'user_name': user_name,
        },
        'navigation': list(navigation or []),
    }


def build_shell_search_payload(*, action, placeholder, autocomplete_url):
    return {
        'action': action,
        'placeholder': placeholder,
        'autocomplete_url': autocomplete_url,
    }


def build_shell_quick_link(*, label, href, kind='secondary', action=''):
    return {
        'label': label,
        'href': href,
        'kind': kind,
        'action': action,
    }


def build_shell_alert_link(*, finance, intakes):
    return {
        'finance': finance,
        'intakes': intakes,
    }


def build_shell_alert_item(*, key, href, count, singular_label, plural_label, action, tone='default'):
    label = singular_label if count == 1 else plural_label
    return {
        'key': key,
        'href': href,
        'count': count,
        'singular_label': singular_label,
        'plural_label': plural_label,
        'label': label,
        'action': action,
        'tone': tone,
        'has_volume': bool(count),
    }


def build_shell_theme_toggle_payload(*, state='light'):
    return {
        'state': state,
    }


def build_shell_profile_payload(*, user_name, role_label, navigation):
    return {
        'user_name': user_name,
        'role_label': role_label,
        'navigation': list(navigation or []),
    }


def build_shell_page_payload(*, eyebrow, title, scope, active_label, role_label, role_slug=''):
    return {
        'eyebrow': eyebrow,
        'title': title,
        'scope': scope,
        'active_label': active_label,
        'role_label': role_label,
        'role_slug': role_slug,
    }


def build_shell_chrome_payload(*, sidebar, topbar, page, counts, cache_rules=None):
    return {
        'sidebar': sidebar,
        'topbar': topbar,
        'page': page,
        'counts': counts or {},
        'cache_rules': cache_rules or dict(SHELL_CHROME_CACHE_RULES),
    }
