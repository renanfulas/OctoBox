"""
ARQUIVO: corredor PWA do app autenticado do aluno.

POR QUE ELE EXISTE:
- separa manifest, service worker e offline fallback das telas de negocio.

O QUE ESTE ARQUIVO FAZ:
1. publica o manifest do app do aluno.
2. entrega o service worker com os assets esperados.
3. expõe a tela offline autenticada.
"""

from __future__ import annotations

import json

from django.conf import settings
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.views.generic import TemplateView, View

from .base import (
    STUDENT_APP_APPLE_TOUCH_ICON,
    STUDENT_APP_BACKGROUND_COLOR,
    STUDENT_APP_ICON_192,
    STUDENT_APP_ICON_512,
    STUDENT_APP_ICON_MASKABLE_512,
    STUDENT_APP_SCOPE,
    STUDENT_APP_START_URL,
    STUDENT_APP_THEME_COLOR,
)


class StudentManifestView(View):
    def get(self, request, *args, **kwargs):
        manifest = {
            'name': 'OctoBox Aluno',
            'short_name': 'OctoBox',
            'start_url': STUDENT_APP_START_URL,
            'scope': STUDENT_APP_SCOPE,
            'display': 'standalone',
            'orientation': 'portrait',
            'background_color': STUDENT_APP_BACKGROUND_COLOR,
            'theme_color': STUDENT_APP_THEME_COLOR,
            'icons': [
                {
                    'src': STUDENT_APP_ICON_192,
                    'sizes': '192x192',
                    'type': 'image/png',
                    'purpose': 'any',
                },
                {
                    'src': STUDENT_APP_ICON_512,
                    'sizes': '512x512',
                    'type': 'image/png',
                    'purpose': 'any',
                },
                {
                    'src': STUDENT_APP_ICON_MASKABLE_512,
                    'sizes': '512x512',
                    'type': 'image/png',
                    'purpose': 'maskable',
                },
            ],
        }
        return HttpResponse(json.dumps(manifest), content_type='application/manifest+json')


class StudentServiceWorkerView(View):
    def get(self, request, *args, **kwargs):
        js = render_to_string(
            'student_app/sw.js',
            {
                'asset_version': getattr(settings, 'STATIC_ASSET_VERSION', '1'),
                'student_app_scope': STUDENT_APP_SCOPE,
                'student_app_manifest_url': '/aluno/manifest.webmanifest',
                'student_app_offline_url': '/aluno/offline/',
                'student_app_css_url': '/static/css/student_app/app.css',
                'student_app_shell_css_url': '/static/css/student_app/shell.css',
                'student_app_components_css_url': '/static/css/student_app/components.css',
                'student_app_forms_css_url': '/static/css/student_app/forms.css',
                'student_app_pages_css_url': '/static/css/student_app/pages.css',
                'student_app_tokens_css_url': '/static/css/design-system/tokens.css',
                'student_app_topbar_css_url': '/static/css/design-system/topbar.css',
                'student_app_js_url': '/static/js/student_app/pwa.js',
                'student_app_theme_js_url': '/static/js/student_app/theme.js',
                'student_app_icon_192_url': STUDENT_APP_ICON_192,
                'student_app_icon_512_url': STUDENT_APP_ICON_512,
                'student_app_icon_maskable_url': STUDENT_APP_ICON_MASKABLE_512,
                'student_app_apple_touch_icon_url': STUDENT_APP_APPLE_TOUCH_ICON,
            },
        )
        response = HttpResponse(js, content_type='application/javascript')
        response['Service-Worker-Allowed'] = STUDENT_APP_SCOPE
        return response


class StudentOfflineView(TemplateView):
    template_name = 'student_app/offline.html'
