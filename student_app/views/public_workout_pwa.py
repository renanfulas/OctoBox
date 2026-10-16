"""Entrega do PWA Curva: assets, manifest, service worker e offline."""

from __future__ import annotations

import json
from pathlib import Path

from django.conf import settings
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.views.generic import View

from public_workouts.catalog import PUBLIC_WORKOUT_LIBRARY
from .base import (
    STUDENT_APP_APPLE_TOUCH_ICON, STUDENT_APP_ICON_192,
    STUDENT_APP_ICON_512, STUDENT_APP_ICON_MASKABLE_512,
)
from .public_workout_access import _get_public_workout_entry


PUBLIC_WORKOUT_SCOPE = '/renan/'
PUBLIC_WORKOUT_OFFLINE_URL = '/renan/offline/'


# R1 do CORDA: corrigir o codigo do A4 nao apaga as copias ja gravadas nos
# aparelhos com PWA instalado. So um VERSION novo expurga. Bump manual e
# deliberado — nao depende do mtime dos assets estaticos, que nao mudam
# nesta correcao. Bumpar de novo sempre que uma correcao de seguranca
# precisar forcar a troca de cache em todos os aparelhos.
# Bump para 3 (Entrega 4, corte pra workout.html): o HTML que /renan/<slug>
# devolve mudou de arquivo por-cliente pra template unico — sem isto, o
# service worker ja instalado nos aparelhos dos 10 clientes continua
# servindo a pagina legada em cache, offline, indefinidamente.
# Bump para 4 (botao de nutricao): novo asset (nutrition.js) entrou em
# PUBLIC_WORKOUT_UNIFIED_TEMPLATE_SCRIPTS abaixo — sem bump, PWA ja
# instalado no aparelho do aluno nunca baixa o script novo (mesmo motivo
# do bump anterior). Bump 4->5 (plano curva-grafico-hierarquia-e-set-
# role.md, §7.10): load_tracker.js passa a enviar set_role sempre.
# Bump 9->10: relatório, API de carga e estado guiado ganharam assets
# obrigatórios; PWA instalada precisa baixar o HTML e o precache novos.
# Bump 10->11: coordenadores de sincronização de carga/guia entram no HTML.
# Bump 11->12: a retomada local e a barra com teclado precisam trocar os
# scripts já guardados em instalações antigas, mesmo com versão estática fixa.
# Bump 12->13: modo foco do treino guiado (guided-format/ring/focus e CSS
# próprio) e guided-loads.js, que faltava no precache, viram obrigatórios.
# Bump 13->14: write-ahead do guiado (onda 3) e conexão IndexedDB reaproveitada
# trocam guided-sync/outbox/focus e workout-guided já guardados no aparelho.
# Bump 14->15: a confirmação de e-mail por código para ativar avisos mudou
# workout-push.js/css; o app instalado é justamente onde o aluno precisa dela.
# Bump 15->16: camada neon Curva — HTML novo (hero com a curva, letreiro) e
# workout-curve.js entram no precache.
# Bump 16->17: aviso push do fim do descanso — guided-rest-alert.js entra no
# precache, workout-guided.js muda e o sw.js trata renotify/vibrate e o toque
# no aviso do descanso sem recarregar a página.
PUBLIC_WORKOUT_CACHE_EPOCH = 17
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
    '/static/css/public_workouts/assessments.css',
    '/static/css/public_workouts/mobile.css',
)

PUBLIC_WORKOUT_SCRIPTS: tuple[str, ...] = (
    '/static/js/public_workouts/app.js',
    '/static/js/public_workouts/assessments-report.js',
    '/static/js/public_workouts/assessments.js',
)

# Entrega 4 — exclusivos de workout.html (template unico, ver <head>/fim do
# proprio arquivo). NAO entram em PUBLIC_WORKOUT_STYLESHEETS/_SCRIPTS de
# proposito: aquelas duas tuplas tambem alimentam `stylesheet_urls` no
# contexto de `_render_legacy_template_html` (os arquivos legados fazem
# `{% for url in stylesheet_urls %}` no proprio <head>) — misturar aqui
# vazaria <link>/<script> de workout.html pras paginas legadas, que nao os
# usam. Só entram no precache do service worker (PublicWorkoutServiceWorkerView),
# que precisa dos dois conjuntos juntos pra qualquer pagina abrir offline.
PUBLIC_WORKOUT_UNIFIED_TEMPLATE_STYLESHEETS: tuple[str, ...] = (
    '/static/css/student_app/app.css',
    '/static/css/design-system/components/tables.css',
    '/static/css/design-system/components/interactive-tabs.css',
    '/static/css/design-system/neon.css',
    '/static/css/public_workouts/workout-shell.css',
    '/static/css/public_workouts/onboarding.css',
    '/static/css/public_workouts/workout-loads.css',
    '/static/css/public_workouts/workout-program-extras.css',
    '/static/css/public_workouts/workout-nutrition.css',
    '/static/css/public_workouts/workout-training.css',
    '/static/css/public_workouts/workout-progress.css',
    '/static/css/public_workouts/workout-assessment.css',
    '/static/css/public_workouts/workout-guided.css',
    '/static/css/public_workouts/workout-guided-focus.css',
    '/static/css/public_workouts/workout-push.css',
)

PUBLIC_WORKOUT_UNIFIED_TEMPLATE_SCRIPTS: tuple[str, ...] = (
    '/static/js/core/shell.js',
    '/static/js/public_workouts/load-storage.js',
    '/static/js/public_workouts/load-plate-calculator.js',
    '/static/js/public_workouts/load-api.js',
    '/static/js/public_workouts/load-sync.js',
    '/static/js/public_workouts/load_tracker.js',
    '/static/js/public_workouts/weekly_review.js',
    '/static/js/public_workouts/nutrition.js',
    '/static/js/public_workouts/workout-shell.js',
    '/static/js/public_workouts/workout-curve.js',
    '/static/js/public_workouts/assessments-report.js',
    '/static/js/public_workouts/assessments.js',
    '/static/js/public_workouts/account.js',
    '/static/js/public_workouts/onboarding.js',
    '/static/js/public_workouts/workout-guided.js',
    '/static/js/public_workouts/guided-outbox.js',
    '/static/js/public_workouts/guided-api.js',
    '/static/js/public_workouts/guided-sync.js',
    '/static/js/public_workouts/guided-timer.js',
    '/static/js/public_workouts/guided-rest-alert.js',
    '/static/js/public_workouts/guided-state.js',
    '/static/js/public_workouts/guided-loads.js',
    '/static/js/public_workouts/guided-format.js',
    '/static/js/public_workouts/guided-ring.js',
    '/static/js/public_workouts/guided-focus.js',
    '/static/js/public_workouts/workout-offline.js',
    '/static/js/public_workouts/workout-pwa.js',
    '/static/js/public_workouts/workout-push.js',
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
    for url in (
        PUBLIC_WORKOUT_STYLESHEETS + PUBLIC_WORKOUT_SCRIPTS
        + PUBLIC_WORKOUT_UNIFIED_TEMPLATE_STYLESHEETS
        + PUBLIC_WORKOUT_UNIFIED_TEMPLATE_SCRIPTS
    ):
        path = base_dir / url.lstrip('/')
        if path.exists():
            mtimes.append(int(path.stat().st_mtime))
    for template_name in ('offline.html', 'sw.js'):
        path = base_dir / 'templates' / 'public_workouts' / template_name
        if path.exists():
            mtimes.append(int(path.stat().st_mtime))
    version = str(max(mtimes, default=1))
    _ASSET_VERSION_CACHE['value'] = version
    return version


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
        # A4 do CORDA: o precache nao pode mais trazer TODOS os slugs (isso
        # e o que faz o aparelho de um aluno guardar o dado de outro,
        # offline). Resolve em runtime, a partir do slug que a propria
        # pagina registrante informa via ?slug= (ver data-plan-slug em
        # _base.html e no head legado). Slug ausente ou desconhecido: SW
        # generico, sem nenhuma pagina de plano no precache.
        requested_slug = (request.GET.get('slug') or '').strip().lower()
        plan_slugs = (requested_slug,) if requested_slug in PUBLIC_WORKOUT_LIBRARY else ()
        js = render_to_string(
            'public_workouts/sw.js',
            {
                'asset_version': public_workout_asset_version(),
                'cache_epoch': PUBLIC_WORKOUT_CACHE_EPOCH,
                'offline_url': PUBLIC_WORKOUT_OFFLINE_URL,
                'app_scope': PUBLIC_WORKOUT_SCOPE,
                'plan_slugs': plan_slugs,
                # CSS e JS compartilhados entram no precache: sem eles a
                # pagina abre offline sem estilo e sem tracker. Inclui os
                # dois conjuntos (legado + workout.html, Entrega 4) porque
                # o precache e' um so pra qualquer pagina que o SW cubra —
                # so os <link>/<script> de CADA TEMPLATE ficam separados
                # (ver comentario de PUBLIC_WORKOUT_UNIFIED_TEMPLATE_*).
                'static_asset_urls': tuple(dict.fromkeys(
                    PUBLIC_WORKOUT_STYLESHEETS
                    + PUBLIC_WORKOUT_SCRIPTS
                    + PUBLIC_WORKOUT_UNIFIED_TEMPLATE_STYLESHEETS
                    + PUBLIC_WORKOUT_UNIFIED_TEMPLATE_SCRIPTS
                    + PUBLIC_WORKOUT_STATIC_ASSETS
                )),
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
