/* Leituras e escritas das abas fora do Treino sem internet (F2 offline-first,
 * docs/plans/curva-offline-first-estrategia.md §3.2/§3.3).
 *
 * Um banco por conta autenticada — curva-offline-data:<conta> — com dois
 * stores:
 * - reads  (chave = URL): última resposta JSON boa de cada leitura
 *   (nutricao.json, avaliacoes.json, pacote.json, revisão semanal). Dado de
 *   saúde fica no IndexedDB da conta, nunca no Cache Storage (B0). Sem rede
 *   ou com 5xx, a leitura devolve a cópia (até 30 dias) e diz de quando ela
 *   é; 401/403/404 apagam a cópia daquela URL (o servidor decidiu).
 * - writes (chave = idempotency_key): fila write-ahead das escritas
 *   (autoavaliação, fim do onboarding). Grava antes de tentar a rede; 2xx ou
 *   recusa definitiva (4xx) tiram da fila; 401, 5xx e falta de rede mantêm.
 *   Drena ao abrir, ao voltar a conexão e ao voltar o foco. O servidor
 *   deduplica pela idempotency_key.
 *
 * "Sair da conta" e respostas que revogam a página (ver sw.js) limpam só o
 * store reads: escrita pendente nunca é apagada sem o aluno saber (F3).
 */
(function () {
  'use strict';

  var DB_VERSION = 1;
  var READ_TTL_MS = 30 * 86400000;
  var accountScope = document.body && document.body.dataset.accountScope;
  var draining = null;

  function announceChange() {
    try { document.dispatchEvent(new CustomEvent('curva:outbox-changed')); } catch (_) {}
  }

  function settled(detail) {
    try { document.dispatchEvent(new CustomEvent('curva:offline-write-settled', { detail: detail })); } catch (_) {}
  }

  function openDb() {
    return new Promise(function (resolve, reject) {
      if (!accountScope || !window.indexedDB) { reject(new Error('Armazenamento local indisponível.')); return; }
      var request = window.indexedDB.open('curva-offline-data:' + accountScope, DB_VERSION);
      request.onupgradeneeded = function () {
        var db = request.result;
        if (!db.objectStoreNames.contains('reads')) db.createObjectStore('reads', { keyPath: 'url' });
        if (!db.objectStoreNames.contains('writes')) db.createObjectStore('writes', { keyPath: 'key' });
      };
      request.onsuccess = function () { resolve(request.result); };
      request.onerror = function () { reject(request.error); };
    });
  }

  // Abre, roda e fecha: estas abas escrevem pouco, e conexão aberta seguraria
  // o deleteDatabase/upgrade de outras abas e do service worker.
  function withStore(name, mode, work) {
    return openDb().then(function (db) {
      return new Promise(function (resolve, reject) {
        var tx = db.transaction(name, mode);
        var request = work(tx.objectStore(name));
        tx.oncomplete = function () { db.close(); resolve(request ? request.result : undefined); };
        tx.onerror = function () { db.close(); reject(tx.error); };
        tx.onabort = function () { db.close(); reject(tx.error); };
      });
    });
  }

  function cookie(name) {
    var part = (document.cookie || '').split(';').map(function (item) { return item.trim(); })
      .find(function (item) { return item.indexOf(name + '=') === 0; });
    return part ? decodeURIComponent(part.slice(name.length + 1)) : '';
  }

  /* ── leituras ─────────────────────────────────────────────── */

  function cachedRead(url) {
    return withStore('reads', 'readonly', function (store) { return store.get(url); })
      .then(function (row) {
        if (!row || Date.now() - row.saved_at > READ_TTL_MS) return null;
        return { data: row.data, savedAt: row.saved_at };
      }, function () { return null; });
  }

  function readJson(url) {
    function fallback(error) {
      return cachedRead(url).then(function (copy) {
        if (copy) return copy;
        throw error;
      });
    }
    return window.fetch(url, { credentials: 'same-origin' }).then(function (response) {
      if (response.ok) {
        return response.json().then(function (data) {
          withStore('reads', 'readwrite', function (store) {
            return store.put({ url: url, data: data, saved_at: Date.now() });
          }).catch(function () {});
          return { data: data, savedAt: null };
        });
      }
      var error = new Error('http-' + response.status);
      error.status = response.status;
      if ([401, 403, 404].indexOf(response.status) !== -1) {
        return withStore('reads', 'readwrite', function (store) { return store.delete(url); })
          .catch(function () {}).then(function () { throw error; });
      }
      return response.status >= 500 ? fallback(error) : Promise.reject(error);
    }, fallback);
  }

  /* ── escritas ─────────────────────────────────────────────── */

  function newKey() {
    if (window.crypto && window.crypto.randomUUID) return window.crypto.randomUUID();
    return 'k-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2);
  }

  function send(entry) {
    var body = Object.assign({}, entry.payload, { idempotency_key: entry.key });
    return window.fetch(entry.url, {
      method: 'POST', credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': cookie('csrftoken'),
        'X-Requested-With': 'XMLHttpRequest',
      },
      body: JSON.stringify(body),
    }).then(function (response) {
      return response.text().then(function (text) {
        var data = {};
        try { data = text ? JSON.parse(text) : {}; } catch (_) {}
        if (response.ok) return { state: 'sent', status: response.status, data: data };
        if (response.status === 401 || response.status >= 500) {
          return { state: 'queued', status: response.status, data: data };
        }
        return { state: 'rejected', status: response.status, data: data };
      });
    }, function () {
      return { state: 'queued', status: 0, data: {} };
    }).then(function (result) {
      if (result.state === 'queued') return result;
      return withStore('writes', 'readwrite', function (store) { return store.delete(entry.key); })
        .then(function () { announceChange(); return result; }, function () { return result; });
    }).then(function (result) {
      result.kind = entry.kind;
      result.key = entry.key;
      return result;
    });
  }

  // Grava primeiro (write-ahead), depois tenta a rede. Sem armazenamento
  // local, ainda tenta enviar direto — só não sobrevive à falta de rede.
  function submit(options) {
    var entry = {
      key: options.key || newKey(), kind: options.kind || '', url: options.url,
      payload: options.payload || {}, created_at: Date.now(),
    };
    return withStore('writes', 'readwrite', function (store) { return store.put(entry); })
      .then(function () { announceChange(); return send(entry); }, function () {
        return send(entry).then(function (result) {
          if (result.state === 'queued') result.state = 'failed';
          return result;
        });
      });
  }

  function pendingWrites(kind) {
    return withStore('writes', 'readonly', function (store) { return store.getAll(); })
      .then(function (rows) {
        return (rows || []).filter(function (row) { return !kind || row.kind === kind; })
          .sort(function (a, b) { return a.created_at - b.created_at; });
      }, function () { return []; });
  }

  function drain() {
    if (draining) return draining;
    if (!accountScope || navigator.onLine === false) return Promise.resolve();
    draining = pendingWrites().then(function (rows) {
      // Em ordem; para no primeiro que continua na fila (rede caiu/login).
      return rows.reduce(function (chain, entry) {
        return chain.then(function (stop) {
          if (stop) return true;
          return send(entry).then(function (result) {
            settled(result);
            return result.state === 'queued';
          });
        });
      }, Promise.resolve(false));
    }).catch(function () {}).then(function () { draining = null; });
    return draining;
  }

  function pad(value) { return (value < 10 ? '0' : '') + value; }

  // "08/11 às 19:42" — mesma forma da faixa de modo offline.
  function savedLabel(savedAt) {
    var date = new Date(savedAt);
    return pad(date.getDate()) + '/' + pad(date.getMonth() + 1)
      + ' às ' + pad(date.getHours()) + ':' + pad(date.getMinutes());
  }

  window.CurvaOfflineData = {
    readJson: readJson,
    savedLabel: savedLabel,
    submit: submit,
    drain: drain,
    pending: function (kind) { return pendingWrites(kind).then(function (rows) { return rows.length; }); },
  };

  if (!accountScope) return;
  window.addEventListener('online', drain);
  document.addEventListener('visibilitychange', function () { if (!document.hidden) drain(); });
  drain();
}());
