"""
ARQUIVO: corredor publico de treinos em modo PWA.

POR QUE ELE EXISTE:
- separa os links publicos sem login da fronteira autenticada do app do aluno.

O QUE ESTE ARQUIVO FAZ:
1. entrega paginas HTML publicas dos treinos compartilhados.
2. publica manifest, service worker e fallback offline do PWA publico.

PONTOS CRITICOS:
- roda no schema `public` sem tenant (ver PUBLIC_SCHEMA_PATHS em
  control/middleware.py): NENHUMA view aqui pode tocar modelo de
  TENANT_APPS. O conftest aplica schema_context('box_test') nos testes,
  entao esse erro passa no teste e so quebra em producao.
- usa render_to_string SEM request de proposito. render(request, ...)
  dispararia access.context_processors.role_navigation, que consulta o
  banco com usuario anonimo no schema public.
- `slug` e `store_key` de PublicWorkoutPlan sao congelados: o primeiro
  esta em links ja distribuidos, o segundo e o namespace do localStorage
  onde o aluno guarda o historico de carga.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings
from django.http import Http404, HttpResponse
from django.template import TemplateDoesNotExist
from django.template.loader import render_to_string
from django.views.generic import View

from .base import (
    STUDENT_APP_APPLE_TOUCH_ICON,
    STUDENT_APP_ICON_192,
    STUDENT_APP_ICON_512,
    STUDENT_APP_ICON_MASKABLE_512,
)


PUBLIC_WORKOUT_SCOPE = '/renan/'
PUBLIC_WORKOUT_OFFLINE_URL = '/renan/offline/'
PUBLIC_WORKOUT_ICON_192 = STUDENT_APP_ICON_192
PUBLIC_WORKOUT_ICON_512 = STUDENT_APP_ICON_512
PUBLIC_WORKOUT_ICON_MASKABLE_512 = STUDENT_APP_ICON_MASKABLE_512
PUBLIC_WORKOUT_APPLE_TOUCH_ICON = STUDENT_APP_APPLE_TOUCH_ICON

# Assets estaticos que o service worker pre-carrega no install.
# Caminhos SEM hash de proposito: o ManifestStaticFilesStorage mantem o
# arquivo original ao lado do hasheado, e o PWA de /aluno/ ja depende disso
# em producao (ver pwa_views.py).
# CUIDADO: cache.addAll() rejeita o install INTEIRO se um item der 404 —
# uma entrada errada aqui mata o modo offline de todos os alunos.
PUBLIC_WORKOUT_STATIC_ASSETS: tuple[str, ...] = (
    PUBLIC_WORKOUT_ICON_192,
    PUBLIC_WORKOUT_ICON_512,
    PUBLIC_WORKOUT_ICON_MASKABLE_512,
    PUBLIC_WORKOUT_APPLE_TOUCH_ICON,
    '/static/images/student-app-icon.svg',
)


@dataclass(frozen=True)
class PublicWorkoutAccent:
    """Rampa de accent do aluno — o UNICO eixo legitimo de branding.

    Todo o resto dos tokens (neutros, raio, sombra, badges de serie) e
    compartilhado. Os arquivos divergem no NOME da familia (--accent nos
    5 modernos, --amber na milene, --blue na giovanna) mas nao no papel.
    """

    base: str
    bg: str
    border: str
    light: str
    dark: str


@dataclass(frozen=True)
class PublicWorkoutPlan:
    """Configuracao de um treino publico.

    CONGELADO — mexer aqui causa dano silencioso:
    - `slug` esta em links ja distribuidos aos alunos (ver public_urls.py).
    - `store_key` e o namespace do localStorage: trocar apaga o historico
      de carga que o aluno digitou, sem aviso e sem backup.
    - `title` alimenta o manifest e `short_name` e derivado dele.
    """

    slug: str
    title: str
    theme_color: str
    background_color: str
    template_file: str
    accent: PublicWorkoutAccent
    tabs: tuple[tuple[str, str], ...]
    tracker_weeks: int = 0
    store_key: str | None = None

    @property
    def short_name(self) -> str:
        # Derivacao preservada: o teste do manifest assere 'Juliana'.
        return self.title.replace('Treino ', '')[:12]

    @property
    def manifest_url(self) -> str:
        return f'/renan/{self.slug}/manifest.webmanifest'


_TAB_TREINO = ('treino', 'Treinos')
_TAB_CARDIO = ('cardio', 'Cardio')
_TAB_PERIOD = ('period', 'Periodização')

PUBLIC_WORKOUT_LIBRARY: dict[str, PublicWorkoutPlan] = {
    plan.slug: plan
    for plan in (
        PublicWorkoutPlan(
            slug='juliana',
            title='Treino Juliana',
            theme_color='#0f172a',
            background_color='#f5efe4',
            template_file='juliana.html',
            accent=PublicWorkoutAccent('#E11D48', '#FFF1F2', '#FECDD3', '#FBD7DF', '#BE123C'),
            tabs=(_TAB_TREINO, _TAB_CARDIO, _TAB_PERIOD),
            tracker_weeks=5,
            store_key='juliana_alves_v3',
        ),
        PublicWorkoutPlan(
            slug='bruno',
            title='Treino Bruno',
            theme_color='#11203b',
            background_color='#f4efe6',
            template_file='bruno.html',
            accent=PublicWorkoutAccent('#EA580C', '#FFF7ED', '#FED7AA', '#FFEDD5', '#C2410C'),
            tabs=(_TAB_TREINO, _TAB_CARDIO, ('nutri', 'Nutrição'), _TAB_PERIOD),
            tracker_weeks=5,
            store_key='bruno_cutting_v1',
        ),
        PublicWorkoutPlan(
            slug='milene',
            title='Treino Milene',
            theme_color='#1a1a1a',
            background_color='#fafaf7',
            template_file='milene.html',
            accent=PublicWorkoutAccent('#D97706', '#FFFBEB', '#FDE68A', '#FEF3C7', '#92400E'),
            tabs=(_TAB_TREINO, _TAB_PERIOD),
            tracker_weeks=5,
            store_key='milene_geraldes_treino',
        ),
        PublicWorkoutPlan(
            slug='giovanna',
            title='Treino Giovanna',
            theme_color='#172017',
            background_color='#f8faf7',
            template_file='giovanna.html',
            # A giovanna so declara 3 degraus (--blue/-bg/-border), e sao os
            # mesmos valores do henrique. Os dois faltantes vem dele.
            accent=PublicWorkoutAccent('#2563EB', '#EFF6FF', '#BFDBFE', '#DBEAFE', '#1D4ED8'),
            tabs=(_TAB_TREINO, _TAB_PERIOD),
            tracker_weeks=5,
            # store_key novo: esta pagina nunca teve tracker, entao nao ha
            # historico anterior para preservar.
            store_key='giovanna_fontes_v1',
        ),
        PublicWorkoutPlan(
            slug='thaislima',
            title='Treino Thais Lima',
            theme_color='#111111',
            background_color='#f6f5f2',
            template_file='thaislima.html',
            accent=PublicWorkoutAccent('#7C3AED', '#F5F3FF', '#DDD6FE', '#EDE9FE', '#5B21B6'),
            tabs=(_TAB_TREINO, _TAB_CARDIO),
            tracker_weeks=5,
            store_key='thais_lima_v1',
        ),
        PublicWorkoutPlan(
            slug='john',
            title='Treino John',
            theme_color='#111111',
            background_color='#f6f5f2',
            template_file='john.html',
            accent=PublicWorkoutAccent('#0891B2', '#ECFEFF', '#A5F3FC', '#CFFAFE', '#0E7490'),
            tabs=(_TAB_TREINO, _TAB_PERIOD),
            tracker_weeks=6,  # unico plano com mesociclo de 6 semanas
            store_key='john_v1',
        ),
        PublicWorkoutPlan(
            slug='henrique',
            title='Treino Henrique',
            theme_color='#141414',
            background_color='#f6f5f2',
            template_file='henrique.html',
            accent=PublicWorkoutAccent('#2563EB', '#EFF6FF', '#BFDBFE', '#DBEAFE', '#1D4ED8'),
            tabs=(_TAB_TREINO, _TAB_CARDIO, _TAB_PERIOD),
            tracker_weeks=5,
            store_key='henrique_santos_souza_v1',
        ),
    )
}


# Ordem importa: tokens antes de tudo, mobile por ultimo (sobrescreve).
# Estes MESMOS caminhos vao para o ALLOWLIST do service worker, entao
# precisam ser planos (sem {% static %}): o allowlist nao sabe resolver
# nome hasheado do ManifestStaticFilesStorage.
PUBLIC_WORKOUT_STYLESHEETS: tuple[str, ...] = (
    '/static/css/public_workouts/tokens.css',
    '/static/css/public_workouts/layout.css',
    '/static/css/public_workouts/components.css',
    '/static/css/public_workouts/tracker.css',
    '/static/css/public_workouts/period.css',
    '/static/css/public_workouts/install-prompt.css',
    '/static/css/public_workouts/mobile.css',
)

PUBLIC_WORKOUT_SCRIPTS: tuple[str, ...] = (
    '/static/js/public_workouts/app.js',
)

_ASSET_VERSION_CACHE: dict[str, str] = {}


def public_workout_asset_version() -> str:
    """Versao usada no ?v= dos assets e no nome do cache do service worker.

    ATENCAO: `STATIC_ASSET_VERSION` esta SEMPRE definida em settings, com
    valor '1' quando o ambiente nao seta nada — e nenhum deploy seta
    (`RENDER_GIT_COMMIT` era do Render, e o projeto migrou para VPS). Ou
    seja: na producao de hoje o ?v= fica congelado em 1 para sempre, o
    cache do navegador nunca invalida e o service worker nunca troca de
    versao. Enquanto o CSS era inline isso nao aparecia, porque o estilo
    chegava junto com o HTML. Agora que e arquivo externo, apareceria.

    Quando o ambiente define a variavel de verdade, respeitamos. Caso
    contrario caimos no mtime dos proprios assets, que muda sozinho a
    cada deploy que altere um arquivo.
    """
    configured = getattr(settings, 'STATIC_ASSET_VERSION', '1')
    if configured and configured != '1':
        return configured

    if 'value' in _ASSET_VERSION_CACHE and not settings.DEBUG:
        return _ASSET_VERSION_CACHE['value']

    base_dir = Path(settings.BASE_DIR)
    mtimes = []
    for url in PUBLIC_WORKOUT_STYLESHEETS + PUBLIC_WORKOUT_SCRIPTS:
        path = base_dir / url.lstrip('/')
        if path.exists():
            mtimes.append(int(path.stat().st_mtime))
    version = str(max(mtimes, default=1))
    _ASSET_VERSION_CACHE['value'] = version
    return version


def _get_public_workout_entry(plan_slug: str) -> PublicWorkoutPlan:
    normalized_slug = (plan_slug or '').strip().lower()
    plan = PUBLIC_WORKOUT_LIBRARY.get(normalized_slug)
    if plan is None:
        raise Http404('Treino publico nao encontrado.')
    return plan


def _render_public_workout_html(plan_slug: str) -> str:
    """Renderiza a pagina do plano a partir do template do aluno.

    O <head>, o prompt de instalacao e o registro do service worker vem
    de public_workouts/_base.html. Antes eram concatenados aqui por
    substituicao de string, procurando a tag <meta name="viewport"> por
    correspondencia EXATA — reformatar essa linha em qualquer arquivo
    desligava o PWA em silencio.

    render_to_string SEM request de proposito: render(request, ...)
    dispararia access.context_processors.role_navigation, que consulta o
    banco com usuario anonimo no schema public. Ver pwa_views.py.
    """
    plan = _get_public_workout_entry(plan_slug)
    try:
        return render_to_string(
            f'public_workouts/{plan.template_file}',
            {
                'plan': plan,
                'stylesheet_urls': PUBLIC_WORKOUT_STYLESHEETS,
                'static_asset_version': public_workout_asset_version(),
                'apple_touch_icon': PUBLIC_WORKOUT_APPLE_TOUCH_ICON,
                'icon_192': PUBLIC_WORKOUT_ICON_192,
            },
        )
    except TemplateDoesNotExist:
        raise Http404('Arquivo de treino publico indisponivel.')


class PublicWorkoutDetailView(View):
    def get(self, request, plan_slug, *args, **kwargs):
        return HttpResponse(_render_public_workout_html(plan_slug))


class PublicWorkoutManifestView(View):
    def get(self, request, plan_slug, *args, **kwargs):
        entry = _get_public_workout_entry(plan_slug)
        manifest = {
            'id': f'/renan/{entry.slug}',
            'name': entry.title,
            'short_name': entry.short_name,
            'description': f'{entry.title} no formato rapido do OctoBox.',
            'start_url': f'/renan/{entry.slug}?source=pwa',
            'scope': PUBLIC_WORKOUT_SCOPE,
            'display': 'standalone',
            'orientation': 'portrait',
            'background_color': entry.background_color,
            'theme_color': entry.theme_color,
            'icons': [
                {
                    'src': PUBLIC_WORKOUT_ICON_192,
                    'sizes': '192x192',
                    'type': 'image/png',
                    'purpose': 'any',
                },
                {
                    'src': PUBLIC_WORKOUT_ICON_512,
                    'sizes': '512x512',
                    'type': 'image/png',
                    'purpose': 'any',
                },
                {
                    'src': PUBLIC_WORKOUT_ICON_MASKABLE_512,
                    'sizes': '512x512',
                    'type': 'image/png',
                    'purpose': 'maskable',
                },
            ],
        }
        return HttpResponse(json.dumps(manifest), content_type='application/manifest+json')


class PublicWorkoutServiceWorkerView(View):
    def get(self, request, *args, **kwargs):
        js = render_to_string(
            'public_workouts/sw.js',
            {
                'asset_version': public_workout_asset_version(),
                'offline_url': PUBLIC_WORKOUT_OFFLINE_URL,
                'app_scope': PUBLIC_WORKOUT_SCOPE,
                'plan_slugs': tuple(PUBLIC_WORKOUT_LIBRARY),
                # CSS e JS compartilhados entram no precache: sem eles a
                # pagina abre offline sem estilo e sem tracker.
                'static_asset_urls': (
                    PUBLIC_WORKOUT_STYLESHEETS
                    + PUBLIC_WORKOUT_SCRIPTS
                    + PUBLIC_WORKOUT_STATIC_ASSETS
                ),
            },
        )
        response = HttpResponse(js, content_type='application/javascript')
        response['Service-Worker-Allowed'] = PUBLIC_WORKOUT_SCOPE
        return response


class PublicWorkoutOfflineView(View):
    def get(self, request, *args, **kwargs):
        # A lista de alunos sai da biblioteca, nao de copy fixa: a versao
        # anterior citava so 4 nomes e linkava /renan/juliana, entao quem
        # entrou depois (thaislima, john, henrique) ficava de fora.
        html = render_to_string(
            'public_workouts/offline.html',
            {'plans': tuple(PUBLIC_WORKOUT_LIBRARY.values())},
        )
        return HttpResponse(html)
