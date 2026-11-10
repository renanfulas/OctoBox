/* Selo global de registros aguardando envio (F0 offline-first,
 * docs/plans/curva-offline-first-estrategia.md §3.4).
 *
 * Só LÊ as filas locais — treino guiado (curva-guided:<conta>:<slug>,
 * store "commands") e cargas (public-workout-outbox:account:<conta>,
 * store "pending-loads") — e pinta um selo no topo, visível em todas as
 * abas. Quem grava e drena continua sendo guided-sync/load-sync; a camada
 * de armazenamento (guided-outbox.js / load-storage.js) avisa cada mudança
 * pelo evento DOM 'curva:outbox-changed' e o selo se repinta.
 *
 * Abre os bancos SEM número de versão de propósito: nunca dispara upgrade
 * num banco existente (não briga com a conexão viva das outras camadas) e
 * um banco inexistente nasce vazio, contando zero.
 */
(function () {
  'use strict';

  var badge = document.querySelector('[data-sync-badge]');
  if (!badge || !window.indexedDB) return;
  var slug = document.body.dataset.planSlug;
  var accountScope = document.body.dataset.accountScope;
  if (!slug || !accountScope) return;

  var GUIDED_DB = 'curva-guided:' + accountScope + ':' + slug;
  var LOADS_DB = 'public-workout-outbox:account:' + accountScope;

  function countStore(dbName, storeName) {
    return new Promise(function (resolve) {
      var request;
      try { request = window.indexedDB.open(dbName); } catch (_) { resolve(0); return; }
      request.onerror = function () { resolve(0); };
      request.onblocked = function () { resolve(0); };
      request.onsuccess = function () {
        var db = request.result;
        var finish = function (count) {
          try { db.close(); } catch (_) {}
          resolve(count);
        };
        if (!db.objectStoreNames.contains(storeName)) { finish(0); return; }
        var tx;
        try { tx = db.transaction(storeName, 'readonly'); } catch (_) { finish(0); return; }
        var counter = tx.objectStore(storeName).count();
        counter.onsuccess = function () { finish(counter.result || 0); };
        counter.onerror = function () { finish(0); };
      };
    });
  }

  // Com o guiado na página, conta pela conexão que ele já mantém aberta: a
  // série online reaproveita uma conexão só, e o selo não pode quebrar isso.
  function countGuided() {
    var outbox = window.CurvaGuidedOutbox;
    if (outbox && outbox.count) {
      return outbox.count(accountScope + ':' + slug).then(function (total) { return total || 0; }, function () { return 0; });
    }
    return countStore(GUIDED_DB, 'commands');
  }

  // F2: avaliações e onboarding na fila de offline-data.js.
  function countOtherWrites() {
    var data = window.CurvaOfflineData;
    return data ? data.pending().then(function (total) { return total || 0; }, function () { return 0; }) : Promise.resolve(0);
  }

  function paint() {
    return Promise.all([
      countGuided(),
      countStore(LOADS_DB, 'pending-loads'),
      countOtherWrites(),
    ]).then(function (counts) {
      var total = counts[0] + counts[1] + counts[2];
      if (!total) {
        badge.hidden = true;
        badge.textContent = '';
        return total;
      }
      var label = total === 1 ? '1 registro a enviar' : total + ' registros a enviar';
      if (!navigator.onLine) label += ' · sem conexão';
      badge.textContent = label;
      badge.hidden = false;
      return total;
    });
  }

  // Rajadas (drenagem removendo N comandos) repintam uma vez só.
  var timer = null;
  function schedule() {
    if (timer !== null) return;
    timer = setTimeout(function () {
      timer = null;
      paint();
    }, 200);
  }

  document.addEventListener('curva:outbox-changed', schedule);
  window.addEventListener('online', schedule);
  window.addEventListener('offline', schedule);
  document.addEventListener('visibilitychange', function () {
    if (!document.hidden) schedule();
  });
  paint();

  window.CurvaSyncBadge = { refresh: paint };
}());
