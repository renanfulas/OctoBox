const VERSION = 'public-workouts-{{ asset_version }}-e{{ cache_epoch }}';
const STATIC_CACHE = `${VERSION}-static`;
const OFFLINE_URL = '{{ offline_url }}';
const APP_SCOPE = '{{ app_scope }}';
const ALLOWLIST = [
{% for slug in plan_slugs %}  '/renan/{{ slug }}/manifest.webmanifest',
{% endfor %}  OFFLINE_URL,
{% for asset_url in static_asset_urls %}  '{{ asset_url }}',
{% endfor %}];

function isAllowedStaticAsset(requestUrl) {
  if (requestUrl.origin !== self.location.origin) {
    return false;
  }
  return ALLOWLIST.includes(requestUrl.pathname);
}

function normalizedWorkoutPath(pathname) {
  if (!pathname.startsWith(APP_SCOPE)) {
    return pathname;
  }
  if (pathname === APP_SCOPE || pathname === OFFLINE_URL) {
    return pathname;
  }
  return pathname.endsWith('/') ? pathname.slice(0, -1) : pathname;
}

self.addEventListener('install', (event) => {
  // cache.add() item a item, e nao addAll(): o addAll rejeita o install
  // INTEIRO se um unico recurso der 404, e ai o aluno fica sem modo
  // offline por causa de um caminho errado numa lista de 40 entradas.
  event.waitUntil(
    caches.open(STATIC_CACHE).then((cache) =>
      Promise.all(ALLOWLIST.map((url) => cache.add(url).catch(() => null)))
    )
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  // HTML de aluno não pertence ao cache compartilhado do navegador.
  const validCaches = [STATIC_CACHE];
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((key) => !validCaches.includes(key)).map((key) => caches.delete(key)))
    )
  );
  self.clients.claim();
});

// Todo push vira notificação, mesmo com o app à vista: o iOS revoga a
// inscrição de quem recebe push sem mostrar nada. Quem evita o alerta duplo
// do fim do descanso é o app, que cancela o aviso antes do envio.
self.addEventListener('push', (event) => {
  let payload = {};
  try { payload = event.data ? event.data.json() : {}; } catch (_) {}
  const options = {
    body: payload.body || 'Você tem uma atualização do seu treino.',
    icon: '/static/images/student-app-icon-192.png',
    badge: '/static/images/student-app-icon-192.png',
    tag: payload.tag || 'curva-update',
    data: { url: payload.url || APP_SCOPE, kind: payload.kind || '' },
  };
  // Fim do descanso: mesma tag na sessão inteira substitui em vez de empilhar;
  // renotify faz a substituição alertar de novo. O padrão de vibração só vale
  // no Android; no iPhone o aviso segue o modo do aparelho (silencioso = vibra).
  if (payload.renotify === true) options.renotify = true;
  if (Array.isArray(payload.vibrate)) options.vibrate = payload.vibrate;
  event.waitUntil(self.registration.showNotification(payload.title || 'Curva', options));
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const data = event.notification.data || {};
  const target = new URL(data.url || APP_SCOPE, self.location.origin);
  if (target.origin !== self.location.origin) return;
  event.waitUntil(self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clients) => {
    const existing = clients.find((client) => new URL(client.url).origin === target.origin);
    // Descanso: a página do plano aberta já guarda o treino em andamento;
    // só traz para a frente, sem recarregar.
    if (existing && data.kind === 'rest' && new URL(existing.url).pathname === target.pathname) {
      return existing.focus();
    }
    return existing ? existing.navigate(target.href).then(() => existing.focus()) : self.clients.openWindow(target.href);
  }));
});

self.addEventListener('fetch', (event) => {
  const request = event.request;
  const requestUrl = new URL(request.url);

  if (request.method !== 'GET') {
    return;
  }

  // B0 do CORDA: nenhum .json sob /renan/ entra em cache — e onde vive
  // dado de saude (avaliacoes.json). Rede direta, sem tocar Cache Storage,
  // mesmo depois que o cookie de posse autorizar a leitura. Checado antes
  // do branch de 'navigate' de proposito: cobre tambem o caso raro de
  // navegacao direta para a URL do JSON, nao so o fetch() da pagina.
  if (requestUrl.pathname.startsWith(APP_SCOPE) && (
    requestUrl.pathname.endsWith('.json')
    || requestUrl.pathname.endsWith('/sessao')
    || requestUrl.pathname.endsWith('/push')
  )) {
    return;
  }

  if (request.mode === 'navigate') {
    if (!requestUrl.pathname.startsWith(APP_SCOPE)) {
      return;
    }
    event.respondWith(
      (async () => {
        try {
          return await fetch(request);
        } catch (error) {
          return await caches.match(OFFLINE_URL, { ignoreSearch: true });
        }
      })()
    );
    return;
  }

  if (requestUrl.origin !== self.location.origin) {
    return;
  }

  if (requestUrl.pathname.startsWith(APP_SCOPE)) {
    if (!requestUrl.pathname.endsWith('.webmanifest')) return;
    event.respondWith(caches.open(STATIC_CACHE).then(async (cache) => {
      const cached = await cache.match(request);
      try {
        const response = await fetch(request);
        if (response.ok) cache.put(request, response.clone());
        return cached || response;
      } catch (error) { return cached || caches.match(OFFLINE_URL); }
    }));
    return;
  }

  if (!isAllowedStaticAsset(requestUrl)) {
    return;
  }

  event.respondWith(
    caches.open(STATIC_CACHE).then(async (cache) => {
      const cached = await cache.match(request, { ignoreSearch: true });
      const networkFetch = fetch(request).then((response) => {
        if (response.ok) {
          cache.put(request, response.clone());
        }
        return response;
      });
      return cached || networkFetch;
    })
  );
});
