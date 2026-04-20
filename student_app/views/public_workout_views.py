"""
ARQUIVO: corredor publico de treinos em modo PWA.

POR QUE ELE EXISTE:
- separa os links publicos sem login da fronteira autenticada do app do aluno.

O QUE ESTE ARQUIVO FAZ:
1. entrega paginas HTML publicas dos treinos compartilhados.
2. publica manifest, service worker e fallback offline do PWA publico.
"""

from __future__ import annotations

import json
from pathlib import Path

from django.conf import settings
from django.http import Http404, HttpResponse
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
PUBLIC_WORKOUT_LIBRARY = {
    'juliana': {
        'title': 'Treino Juliana',
        'theme_color': '#0f172a',
        'background_color': '#f5efe4',
        'template_file': 'juliana.html',
    },
    'bruno': {
        'title': 'Treino Bruno',
        'theme_color': '#11203b',
        'background_color': '#f4efe6',
        'template_file': 'bruno.html',
    },
}
PUBLIC_WORKOUT_TEMPLATE_DIR = Path(settings.BASE_DIR) / 'templates' / 'public_workouts'


def _get_public_workout_entry(plan_slug: str) -> dict[str, str]:
    normalized_slug = (plan_slug or '').strip().lower()
    entry = PUBLIC_WORKOUT_LIBRARY.get(normalized_slug)
    if entry is None:
        raise Http404('Treino publico nao encontrado.')
    return {'slug': normalized_slug, **entry}


def _build_public_workout_manifest_url(plan_slug: str) -> str:
    return f'/renan/{plan_slug}/manifest.webmanifest'


def _render_public_workout_html(plan_slug: str) -> str:
    entry = _get_public_workout_entry(plan_slug)
    template_path = PUBLIC_WORKOUT_TEMPLATE_DIR / entry['template_file']
    if not template_path.exists():
        raise Http404('Arquivo de treino publico indisponivel.')

    html = template_path.read_text(encoding='utf-8')
    viewport_markers = (
        '<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">',
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">',
    )
    head_injection = (
        f'<meta name="theme-color" content="{entry["theme_color"]}">\n'
        '<meta name="mobile-web-app-capable" content="yes">\n'
        '<meta name="apple-mobile-web-app-capable" content="yes">\n'
        '<meta name="apple-mobile-web-app-status-bar-style" content="default">\n'
        f'<meta name="apple-mobile-web-app-title" content="{entry["title"]}">\n'
        f'<link rel="manifest" href="{_build_public_workout_manifest_url(entry["slug"])}">\n'
        f'<link rel="apple-touch-icon" href="{PUBLIC_WORKOUT_APPLE_TOUCH_ICON}">\n'
        '<link rel="icon" href="/static/images/student-app-icon.svg" type="image/svg+xml">\n'
        f'<link rel="icon" href="{PUBLIC_WORKOUT_ICON_192}" sizes="192x192" type="image/png">'
    )
    for marker in viewport_markers:
        if marker in html:
            html = html.replace(marker, f'{marker}\n{head_injection}', 1)
            break

    install_prompt_markup = """
<style>
.public-workout-install{
  position:fixed;
  right:16px;
  bottom:16px;
  z-index:9999;
  display:none;
  align-items:center;
  gap:10px;
  max-width:min(320px,calc(100vw - 32px));
  padding:12px 14px;
  border-radius:18px;
  background:rgba(17,32,59,.94);
  color:#fff;
  box-shadow:0 16px 34px rgba(15,23,42,.28);
  font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
}
.public-workout-install.is-visible{display:flex}
.public-workout-install__copy{font-size:13px;line-height:1.35}
.public-workout-install__button{
  border:0;
  border-radius:999px;
  padding:10px 14px;
  background:#f5efe4;
  color:#11203b;
  font-weight:700;
  font-size:13px;
  cursor:pointer;
  white-space:nowrap;
}
@media (max-width: 640px){
  .public-workout-install{
    left:12px;
    right:12px;
    bottom:12px;
    max-width:none;
  }
}
</style>
<div class="public-workout-install" id="public-workout-install" aria-live="polite">
  <div class="public-workout-install__copy" id="public-workout-install-copy"></div>
  <button class="public-workout-install__button" id="public-workout-install-button" type="button"></button>
</div>
""".strip()
    sw_registration_script = """
<script>
(function () {
  var installPrompt = null;
  var installRoot = document.getElementById('public-workout-install');
  var installCopy = document.getElementById('public-workout-install-copy');
  var installButton = document.getElementById('public-workout-install-button');
  var isStandalone = window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone === true;
  var isIos = /iphone|ipad|ipod/i.test(window.navigator.userAgent);

  function showInstall(copy, buttonLabel, onClick) {
    if (!installRoot || !installCopy || !installButton || isStandalone) {
      return;
    }
    installCopy.textContent = copy;
    installButton.textContent = buttonLabel;
    installButton.onclick = onClick;
    installRoot.classList.add('is-visible');
  }

  if (!('serviceWorker' in navigator)) {
    if (isIos) {
      showInstall('No iPhone/iPad, toque em Compartilhar e depois em Adicionar \u00e0 Tela de In\u00edcio.', 'Entendi', function () {
        installRoot.classList.remove('is-visible');
      });
    }
    return;
  }

  if (isIos) {
    showInstall('No iPhone/iPad, toque em Compartilhar e depois em Adicionar \u00e0 Tela de In\u00edcio.', 'Entendi', function () {
      installRoot.classList.remove('is-visible');
    });
  }

  window.addEventListener('beforeinstallprompt', function (event) {
    event.preventDefault();
    installPrompt = event;
    showInstall('Instale este treino na tela inicial para abrir como app, sem login.', 'Instalar app', function () {
      if (!installPrompt) {
        return;
      }
      installPrompt.prompt();
      installPrompt.userChoice.finally(function () {
        installPrompt = null;
        installRoot.classList.remove('is-visible');
      });
    });
  });

  window.addEventListener('appinstalled', function () {
    if (installRoot) {
      installRoot.classList.remove('is-visible');
    }
  });

  window.addEventListener('load', function () {
    navigator.serviceWorker.register('/renan/sw.js', { scope: '/renan/' }).catch(function () {
      // O treino continua abrindo mesmo sem o service worker.
    });
  });
})();
</script>
""".strip()
    if "navigator.serviceWorker.register('/renan/sw.js'" not in html:
        html = html.replace('</body>', f'{install_prompt_markup}\n{sw_registration_script}\n</body>', 1)
    return html


class PublicWorkoutDetailView(View):
    def get(self, request, plan_slug, *args, **kwargs):
        return HttpResponse(_render_public_workout_html(plan_slug))


class PublicWorkoutManifestView(View):
    def get(self, request, plan_slug, *args, **kwargs):
        entry = _get_public_workout_entry(plan_slug)
        manifest = {
            'id': f'/renan/{entry["slug"]}',
            'name': entry['title'],
            'short_name': entry['title'].replace('Treino ', '')[:12],
            'description': f'{entry["title"]} no formato rapido do OctoBox.',
            'start_url': f'/renan/{entry["slug"]}?source=pwa',
            'scope': PUBLIC_WORKOUT_SCOPE,
            'display': 'standalone',
            'orientation': 'portrait',
            'background_color': entry['background_color'],
            'theme_color': entry['theme_color'],
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
        routes = ''.join(
            [
                f"  '/renan/{slug}',\n"
                f"  '/renan/{slug}/',\n"
                f"  '/renan/{slug}?source=pwa',\n"
                f"  '/renan/{slug}/manifest.webmanifest',\n"
                for slug in PUBLIC_WORKOUT_LIBRARY
            ]
        )
        js = f"""const VERSION = 'public-workouts-{getattr(settings, 'STATIC_ASSET_VERSION', '1')}';
const STATIC_CACHE = `${{VERSION}}-static`;
const PAGE_CACHE = `${{VERSION}}-pages`;
const OFFLINE_URL = '{PUBLIC_WORKOUT_OFFLINE_URL}';
const APP_SCOPE = '{PUBLIC_WORKOUT_SCOPE}';
const ALLOWLIST = [
{routes}  OFFLINE_URL,
  '{PUBLIC_WORKOUT_ICON_192}',
  '{PUBLIC_WORKOUT_ICON_512}',
  '{PUBLIC_WORKOUT_ICON_MASKABLE_512}',
  '{PUBLIC_WORKOUT_APPLE_TOUCH_ICON}',
  '/static/images/student-app-icon.svg',
];

function isAllowedStaticAsset(requestUrl) {{
  if (requestUrl.origin !== self.location.origin) {{
    return false;
  }}
  return ALLOWLIST.includes(requestUrl.pathname);
}}

function normalizedWorkoutPath(pathname) {{
  if (!pathname.startsWith(APP_SCOPE)) {{
    return pathname;
  }}
  if (pathname === APP_SCOPE || pathname === OFFLINE_URL) {{
    return pathname;
  }}
  return pathname.endsWith('/') ? pathname.slice(0, -1) : pathname;
}}

self.addEventListener('install', (event) => {{
  event.waitUntil(caches.open(STATIC_CACHE).then((cache) => cache.addAll(ALLOWLIST)));
  self.skipWaiting();
}});

self.addEventListener('activate', (event) => {{
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((key) => key !== STATIC_CACHE).map((key) => caches.delete(key)))
    )
  );
  self.clients.claim();
}});

self.addEventListener('fetch', (event) => {{
  const request = event.request;
  const requestUrl = new URL(request.url);

  if (request.method !== 'GET') {{
    return;
  }}

  if (request.mode === 'navigate') {{
    if (!requestUrl.pathname.startsWith(APP_SCOPE)) {{
      return;
    }}
    event.respondWith(
      (async () => {{
        const pageCache = await caches.open(PAGE_CACHE);
        const cacheKey = normalizedWorkoutPath(requestUrl.pathname);
        try {{
          const response = await fetch(request);
          if (response.ok) {{
            pageCache.put(cacheKey, response.clone());
          }}
          return response;
        }} catch (error) {{
          return (
            await pageCache.match(cacheKey, {{ ignoreSearch: true }})
            || await pageCache.match(requestUrl.pathname, {{ ignoreSearch: true }})
            || await caches.match(cacheKey, {{ ignoreSearch: true }})
            || await caches.match(request, {{ ignoreSearch: true }})
            || await caches.match(OFFLINE_URL, {{ ignoreSearch: true }})
          );
        }}
      }})()
    );
    return;
  }}

  if (requestUrl.origin !== self.location.origin) {{
    return;
  }}

  if (requestUrl.pathname.startsWith(APP_SCOPE)) {{
    event.respondWith(
      (async () => {{
        const cacheName = requestUrl.pathname.endsWith('.webmanifest') ? STATIC_CACHE : PAGE_CACHE;
        const cache = await caches.open(cacheName);
        const cacheKey = normalizedWorkoutPath(requestUrl.pathname);
        const cached = await cache.match(cacheKey, {{ ignoreSearch: true }}) || await cache.match(request, {{ ignoreSearch: true }});
        try {{
          const response = await fetch(request);
          if (response.ok) {{
            cache.put(cacheKey, response.clone());
          }}
          return cached || response;
        }} catch (error) {{
          return cached || caches.match(OFFLINE_URL, {{ ignoreSearch: true }});
        }}
      }})()
    );
    return;
  }}

  if (!isAllowedStaticAsset(requestUrl)) {{
    return;
  }}

  event.respondWith(
    caches.open(STATIC_CACHE).then(async (cache) => {{
      const cached = await cache.match(request, {{ ignoreSearch: true }});
      const networkFetch = fetch(request).then((response) => {{
        if (response.ok) {{
          cache.put(request, response.clone());
        }}
        return response;
      }});
      return cached || networkFetch;
    }})
  );
}});
"""
        response = HttpResponse(js, content_type='application/javascript')
        response['Service-Worker-Allowed'] = PUBLIC_WORKOUT_SCOPE
        return response


class PublicWorkoutOfflineView(View):
    def get(self, request, *args, **kwargs):
        html = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Treinos offline</title>
  <style>
    body{margin:0;font-family:Manrope,system-ui,sans-serif;background:#f4efe6;color:#11203b;min-height:100vh;display:grid;place-items:center;padding:24px}
    main{width:min(100%,560px);background:rgba(255,255,255,.92);border:1px solid rgba(17,32,59,.12);border-radius:28px;padding:28px;box-shadow:0 24px 60px rgba(17,32,59,.12)}
    h1{margin:0 0 12px;font-size:clamp(1.8rem,4vw,2.4rem)}
    p{margin:0 0 12px;line-height:1.6;color:#52627e}
    a{display:inline-flex;margin-top:12px;padding:12px 16px;border-radius:999px;background:#11203b;color:#fff;text-decoration:none;font-weight:700}
  </style>
</head>
<body>
  <main>
    <h1>Sem conex\u00e3o agora.</h1>
    <p>Quando a internet voltar, os links p\u00fablicos de treino da Juliana e do Bruno voltam a abrir normalmente.</p>
    <p>Se voc\u00ea j\u00e1 abriu um dos treinos antes neste aparelho, tente novamente em alguns segundos.</p>
    <a href="/renan/juliana">Abrir treino da Juliana</a>
  </main>
</body>
</html>"""
        return HttpResponse(html)
