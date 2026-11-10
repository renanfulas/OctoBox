"""Esperas do modo offline do Curva (docs/plans/curva-offline-first-estrategia.md).

O service worker guarda a página do dono em `curva-offline-pages` e
offline-data.js guarda as leituras JSON em `curva-offline-data:<conta>`;
estes helpers esperam essas cópias existirem antes de o teste cortar a rede.
"""

from playwright.sync_api import Page

_READ_RECORD = """({ name, stores, store, key }) => new Promise((resolve) => {
  const request = indexedDB.open(name, 1);
  request.onupgradeneeded = () => {
    stores.forEach(([storeName, keyPath]) => request.result.createObjectStore(storeName, { keyPath }));
  };
  request.onerror = () => resolve(false);
  request.onsuccess = () => {
    const db = request.result;
    const read = db.transaction(store).objectStore(store).get(key);
    read.onsuccess = () => { db.close(); resolve(Boolean(read.result)); };
    read.onerror = () => { db.close(); resolve(false); };
  };
})"""


def _wait_for_record(page: Page, args: dict, what: str):
    for _ in range(100):
        if page.evaluate(_READ_RECORD, args):
            return
        page.wait_for_timeout(100)
    raise AssertionError(f'{what} não chegou ao IndexedDB')


def wait_for_saved_page(page: Page, plan_slug: str = 'bruno'):
    """Espera o service worker guardar a página do dono (F1, curva-offline-pages)."""
    _wait_for_record(page, {
        'name': 'curva-offline-pages', 'stores': [['pages', 'slug']], 'store': 'pages', 'key': plan_slug,
    }, 'a página do treino')


def wait_for_saved_read(page: Page, account_id: int, url: str):
    """Espera offline-data.js guardar a leitura JSON no banco da conta (F2)."""
    _wait_for_record(page, {
        'name': f'curva-offline-data:{account_id}', 'stores': [['reads', 'url'], ['writes', 'key']],
        'store': 'reads', 'key': url,
    }, url)


def visit_once_under_service_worker(page: Page, plan_slug: str = 'bruno'):
    """A 1a visita acontece antes do SW existir; a seguinte, já sob ele, é a
    que guarda a página para abrir sem rede."""
    page.evaluate('async () => { await navigator.serviceWorker.ready; }')
    page.reload()
    wait_for_saved_page(page, plan_slug)
