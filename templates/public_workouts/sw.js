const VERSION = 'public-workouts-{{ asset_version }}';
const STATIC_CACHE = `${VERSION}-static`;
const PAGE_CACHE = `${VERSION}-pages`;
const OFFLINE_URL = '{{ offline_url }}';
const APP_SCOPE = '{{ app_scope }}';
const ALLOWLIST = [
{% for slug in plan_slugs %}  '/renan/{{ slug }}',
  '/renan/{{ slug }}/',
  '/renan/{{ slug }}?source=pwa',
  '/renan/{{ slug }}/manifest.webmanifest',
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
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((key) => key !== STATIC_CACHE).map((key) => caches.delete(key)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const request = event.request;
  const requestUrl = new URL(request.url);

  if (request.method !== 'GET') {
    return;
  }

  if (request.mode === 'navigate') {
    if (!requestUrl.pathname.startsWith(APP_SCOPE)) {
      return;
    }
    event.respondWith(
      (async () => {
        const pageCache = await caches.open(PAGE_CACHE);
        const cacheKey = normalizedWorkoutPath(requestUrl.pathname);
        try {
          const response = await fetch(request);
          if (response.ok) {
            pageCache.put(cacheKey, response.clone());
          }
          return response;
        } catch (error) {
          return (
            await pageCache.match(cacheKey, { ignoreSearch: true })
            || await pageCache.match(requestUrl.pathname, { ignoreSearch: true })
            || await caches.match(cacheKey, { ignoreSearch: true })
            || await caches.match(request, { ignoreSearch: true })
            || await caches.match(OFFLINE_URL, { ignoreSearch: true })
          );
        }
      })()
    );
    return;
  }

  if (requestUrl.origin !== self.location.origin) {
    return;
  }

  if (requestUrl.pathname.startsWith(APP_SCOPE)) {
    event.respondWith(
      (async () => {
        const cacheName = requestUrl.pathname.endsWith('.webmanifest') ? STATIC_CACHE : PAGE_CACHE;
        const cache = await caches.open(cacheName);
        const cacheKey = normalizedWorkoutPath(requestUrl.pathname);
        const cached = await cache.match(cacheKey, { ignoreSearch: true }) || await cache.match(request, { ignoreSearch: true });
        try {
          const response = await fetch(request);
          if (response.ok) {
            cache.put(cacheKey, response.clone());
          }
          return cached || response;
        } catch (error) {
          return cached || caches.match(OFFLINE_URL, { ignoreSearch: true });
        }
      })()
    );
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
