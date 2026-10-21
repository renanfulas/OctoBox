/* Fila de cargas confirmadas e rascunhos locais, isolados por conta. */
(function () {
  'use strict';

  function create(accountScope, planSlug, todayIso) {
    // Cada conta usa um banco local; registros sem dono ficam isolados.
    var DB_NAME = 'public-workout-outbox:account:' + (accountScope || 'visitor');
    var DB_VERSION = 2;
    var STORE_NAME = 'pending-loads';
    var DRAFT_STORE_NAME = 'drafts';

    /* ══ OUTBOX (IndexedDB) ═══════════════════════════════════════ */

    function openDb() {
      return new Promise(function (resolve, reject) {
        if (!window.indexedDB) { reject(new Error('sem IndexedDB')); return; }
        var request = window.indexedDB.open(DB_NAME, DB_VERSION);
        request.onupgradeneeded = function () {
          var db = request.result;
          if (!db.objectStoreNames.contains(STORE_NAME)) {
            db.createObjectStore(STORE_NAME, { keyPath: 'idempotency_key' });
          }
          // v2 (plano curva-carga-completa-reps-rir-recorde, §3.2): store
          // separado pra rascunho -- chave composta (plano/movimento/data)
          // porque um rascunho e' por combinacao dessas tres coisas, nao
          // por idempotency_key (que so nasce quando o rascunho e'
          // promovido pra confirmado, no clique em Salvar).
          if (!db.objectStoreNames.contains(DRAFT_STORE_NAME)) {
            db.createObjectStore(DRAFT_STORE_NAME, { keyPath: ['plan_slug', 'movement_slug', 'performed_on'] });
          }
        };
        request.onblocked = function () {
          // Outra aba da mesma origem ainda tem a versao 1 aberta -- nao
          // forca o upgrade (fecharia a conexao da outra aba no meio do
          // uso). A proxima tentativa (reload, ou a outra aba fechando)
          // resolve sozinha; nunca perde rascunho/outbox por isso.
          reject(new Error('upgrade do IndexedDB bloqueado por outra aba'));
        };
        request.onsuccess = function () {
          var db = request.result;
          db.onversionchange = function () { db.close(); };
          resolve(db);
        };
        request.onerror = function () { reject(request.error); };
      });
    }

    function withStore(storeName, mode, fn) {
      return openDb().then(function (db) {
        return new Promise(function (resolve, reject) {
          var tx = db.transaction(storeName, mode);
          var store = tx.objectStore(storeName);
          var result = fn(store);
          tx.oncomplete = function () { resolve(result); };
          tx.onerror = function () { reject(tx.error); };
        });
      });
    }

    function queueEntry(entry) {
      return withStore(STORE_NAME, 'readwrite', function (store) { store.put(entry); return entry; });
    }

    function removeEntry(idempotencyKey) {
      return withStore(STORE_NAME, 'readwrite', function (store) { store.delete(idempotencyKey); });
    }

    function listEntries() {
      return openDb().then(function (db) {
        return new Promise(function (resolve, reject) {
          var tx = db.transaction(STORE_NAME, 'readonly');
          var request = tx.objectStore(STORE_NAME).getAll();
          request.onsuccess = function () { resolve(request.result || []); };
          request.onerror = function () { reject(request.error); };
        });
      });
    }

    function clearOutbox() {
      return withStore(STORE_NAME, 'readwrite', function (store) { store.clear(); });
    }

    /* ══ RASCUNHO (IndexedDB, store separado da outbox confirmada) ══ */

    function draftKey(widget) {
      return {
        plan_slug: planSlug(),
        movement_slug: widget.getAttribute('data-movement-slug'),
        performed_on: todayIso(),
      };
    }

    function putDraft(widget, weightKg, reps, rir) {
      var key = draftKey(widget);
      return withStore(DRAFT_STORE_NAME, 'readwrite', function (store) {
        store.put({
          plan_slug: key.plan_slug,
          movement_slug: key.movement_slug,
          performed_on: key.performed_on,
          weight_kg: weightKg,
          reps: reps,
          rir: rir,
          saved_at: Date.now(),
        });
      });
    }

    function deleteDraft(widget) {
      var key = draftKey(widget);
      return withStore(DRAFT_STORE_NAME, 'readwrite', function (store) {
        store.delete([key.plan_slug, key.movement_slug, key.performed_on]);
      });
    }

    function getDraft(widget) {
      var key = draftKey(widget);
      return openDb().then(function (db) {
        return new Promise(function (resolve, reject) {
          var tx = db.transaction(DRAFT_STORE_NAME, 'readonly');
          var request = tx.objectStore(DRAFT_STORE_NAME).get([key.plan_slug, key.movement_slug, key.performed_on]);
          request.onsuccess = function () { resolve(request.result || null); };
          request.onerror = function () { reject(request.error); };
        });
      });
    }

    function clearDrafts() {
      return withStore(DRAFT_STORE_NAME, 'readwrite', function (store) { store.clear(); });
    }

    return { queueEntry: queueEntry, removeEntry: removeEntry, listEntries: listEntries,
      clearOutbox: clearOutbox, putDraft: putDraft, deleteDraft: deleteDraft,
      getDraft: getDraft, clearDrafts: clearDrafts };
  }

  window.CurvaLoadStorage = { create: create };
}());
