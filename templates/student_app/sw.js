const VERSION = 'student-app-{{ asset_version }}';
const STATIC_CACHE = `${VERSION}-static`;
const OFFLINE_URL = '{{ student_app_offline_url }}';
const APP_SCOPE = '{{ student_app_scope }}';
const ALLOWLIST = [
  OFFLINE_URL,
  '{{ student_app_manifest_url }}',
  {% for css_url in student_app_css_urls %}'{{ css_url }}',{% endfor %}
  '{{ student_app_tokens_css_url }}',
  '{{ student_app_topbar_css_url }}',
  '{{ student_app_js_url }}',
  '{{ student_app_theme_js_url }}',
  '{{ student_app_icon_192_url }}',
  '{{ student_app_icon_512_url }}',
  '{{ student_app_icon_maskable_url }}',
  '{{ student_app_apple_touch_icon_url }}',
  '/static/images/student-app-icon.svg',
];

function isAllowedStaticAsset(requestUrl) {
  if (requestUrl.origin !== self.location.origin) {
    return false;
  }
  const pathname = requestUrl.pathname;
  return ALLOWLIST.includes(pathname);
}

async function staleWhileRevalidate(request) {
  const cache = await caches.open(STATIC_CACHE);
  const cached = await cache.match(request, { ignoreSearch: true });
  const networkFetch = fetch(request).then((response) => {
    if (response.ok) {
      cache.put(request, response.clone());
    }
    return response;
  });
  return cached || networkFetch;
}

async function networkFirst(request) {
  const cache = await caches.open(STATIC_CACHE);
  try {
    const response = await fetch(request);
    return response;
  } catch (error) {
    return cache.match(OFFLINE_URL, { ignoreSearch: true });
  }
}

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then((cache) => cache.addAll(ALLOWLIST))
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
    event.respondWith(networkFirst(request));
    return;
  }

  if (!isAllowedStaticAsset(requestUrl)) {
    return;
  }

  event.respondWith(staleWhileRevalidate(request));
});

self.addEventListener('push', (event) => {
  let payload = {};
  try {
    payload = event.data ? event.data.json() : {};
  } catch (error) {
    payload = {
      title: 'OctoBox Aluno',
      body: event.data ? event.data.text() : 'Voce recebeu uma nova notificacao.',
    };
  }

  const title = payload.title || 'OctoBox Aluno';
  const options = {
    body: payload.body || 'Voce recebeu uma nova notificacao.',
    icon: payload.icon || '{{ student_app_icon_192_url }}',
    badge: payload.badge || '{{ student_app_icon_192_url }}',
    tag: payload.tag || 'student-app-notification',
    data: {
      url: payload.url || '{{ student_app_scope }}',
    },
  };

  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const targetUrl = (event.notification.data && event.notification.data.url) || '{{ student_app_scope }}';
  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clients) => {
      for (const client of clients) {
        if ('focus' in client && client.url.includes(targetUrl)) {
          return client.focus();
        }
      }
      if (self.clients.openWindow) {
        return self.clients.openWindow(targetUrl);
      }
      return undefined;
    })
  );
});
