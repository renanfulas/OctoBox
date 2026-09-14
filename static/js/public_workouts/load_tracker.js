/*
 * ARQUIVO: registro de carga do "template unico" (Onda B3 do CORDA, item 8).
 *
 * POR QUE ELE EXISTE:
 * - workout.html ja mostra a EVOLUCAO de carga (aba Historico, alimentada
 *   por load_history/one_rep_max_by_movement — ver templatetags
 *   public_workouts_extras.py::load_chart_points), mas ate aqui nao tinha
 *   como o aluno REGISTRAR a carga de hoje: so existia o endpoint HTTP
 *   (POST /renan/<slug>/carga, PublicWorkoutRecordLoadView) sem UI nenhuma
 *   chamando ele. Este arquivo e essa UI.
 * - Nao reusa static/js/public_workouts/app.js: aquele arquivo e do grid
 *   semanal client-only (.wk-input/.tp-*) das 8 paginas legadas que a
 *   Onda B3 vai apagar (item 3) — grid que nunca saia do localStorage do
 *   aparelho. Aqui o modelo e outro (backend real, um registro por data,
 *   nao uma grade fixa de 5 semanas), entao a UI tambem e outra: um input
 *   por movimento rastreado, "o que voce levantou HOJE".
 *
 * PONTOS CRITICOS (outbox em IndexedDB, item 8):
 * - Toda gravacao (clique em Salvar OU rascunho automatico em
 *   visibilitychange) primeiro entra no IndexedDB (`public-workout-outbox`,
 *   store `pending-loads`) — so DEPOIS tenta enviar. Se o envio falhar
 *   (offline, erro de rede), o registro fica no outbox e uma proxima
 *   tentativa (evento `online`, proximo load da pagina) reenvia sozinho.
 *   E o mesmo motivo de "Nenhum aluno perdeu carga" (Pronto-quando #5 da
 *   Onda B3): perder o dado seria pior que atrasar o envio.
 * - `idempotency_key` e gerada UMA VEZ, no momento em que o registro entra
 *   no outbox, e reenviada sem trocar em toda tentativa seguinte —
 *   PublicWorkoutRecordLoadView/record_load (public_workouts/services.py)
 *   usa ela pra nunca duplicar linha num reenvio. Duas gravacoes
 *   DIFERENTES (o aluno corrige o proprio numero e salva de novo) geram
 *   chaves diferentes de proposito: sao dois eventos, nao um so repetido.
 * - Limpeza no logout: ainda NAO ha rota de logout no corredor (so o
 *   cookie de posse do B0 e a sessao de login do B1, nenhum "sair"
 *   clicavel hoje) — por isso `clearOutbox` so fica exportada
 *   (`window.PublicWorkoutLoadTracker.clearOutbox`) esperando esse botao
 *   nascer, em vez de fingir que ja esta ligada a algo real.
 * - 401 (sessao de login expirou) NUNCA limpa o outbox — o registro fica
 *   guardado e tenta de novo sozinho assim que o aluno logar de novo
 *   (mesmo padrao de "sessao expirou, faca login novamente" de
 *   assessments.js, sem duplicar a logica de leitura de cookie daqui:
 *   so precisamos do redirect, nao do relatorio).
 *
 * PONTOS CRITICOS (dica de ultima carga + stepper):
 * - GET /renan/<slug>/pacote.json (PublicWorkoutPackageView, ja existe)
 *   devolve `last_load_by_movement` — usado so pra popular a dica "Última
 *   vez: X kg" acima do campo. 401 aqui (sem sessao ainda) so deixa a
 *   dica vazia, nunca bloqueia o registro em si (o aluno pode digitar e
 *   salvar sem nunca ter visto a dica — ela e so um atalho, nao um
 *   pre-requisito).
 * - O stepper (+/-2,5kg) edita o MESMO campo que o clique/toque direto —
 *   nao existe um segundo estado interno. Dispara o mesmo evento `input`
 *   que marca `data-dirty`, entao o rascunho automatico em
 *   visibilitychange cobre o stepper tambem, de graca.
 */

(function () {
  'use strict';

  var body = document.body;
  var DB_NAME = 'public-workout-outbox';
  var DB_VERSION = 1;
  var STORE_NAME = 'pending-loads';

  function planSlug() {
    return body.getAttribute('data-plan-slug') || '';
  }

  function pad2(n) {
    return n < 10 ? '0' + n : '' + n;
  }

  function todayIso() {
    var d = new Date();
    return d.getFullYear() + '-' + pad2(d.getMonth() + 1) + '-' + pad2(d.getDate());
  }

  function uuid() {
    if (window.crypto && window.crypto.randomUUID) { return window.crypto.randomUUID(); }
    // Fallback pra navegador sem crypto.randomUUID (raro, mas o corredor
    // roda em aparelho de aluno variado demais pra assumir suporte).
    return 'load-' + Date.now() + '-' + Math.random().toString(16).slice(2);
  }

  // Mesmo padrao de assessments.js::getCookie/postJson — nao importa aquele
  // arquivo direto porque nem toda pagina que carrega load_tracker.js
  // necessariamente carrega assessments.js (abas independentes).
  function getCookie(name) {
    var parts = (document.cookie || '').split(';');
    for (var i = 0; i < parts.length; i++) {
      var part = parts[i].trim();
      if (part.indexOf(name + '=') === 0) {
        return decodeURIComponent(part.slice(name.length + 1));
      }
    }
    return '';
  }

  function postJson(url, payload) {
    return window.fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken'),
        'X-Requested-With': 'XMLHttpRequest',
      },
      body: JSON.stringify(payload || {}),
    }).then(function (response) {
      return response.text().then(function (text) {
        var data = {};
        if (text) {
          try { data = JSON.parse(text); } catch (e) { /* corpo nao-JSON */ }
        }
        return { ok: response.ok, status: response.status, data: data };
      });
    });
  }

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
      };
      request.onsuccess = function () { resolve(request.result); };
      request.onerror = function () { reject(request.error); };
    });
  }

  function withStore(mode, fn) {
    return openDb().then(function (db) {
      return new Promise(function (resolve, reject) {
        var tx = db.transaction(STORE_NAME, mode);
        var store = tx.objectStore(STORE_NAME);
        var result = fn(store);
        tx.oncomplete = function () { resolve(result); };
        tx.onerror = function () { reject(tx.error); };
      });
    });
  }

  function queueEntry(entry) {
    return withStore('readwrite', function (store) { store.put(entry); return entry; });
  }

  function removeEntry(idempotencyKey) {
    return withStore('readwrite', function (store) { store.delete(idempotencyKey); });
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
    return withStore('readwrite', function (store) { store.clear(); });
  }

  // Drena o outbox: tenta reenviar cada registro pendente. 401 (sessao
  // expirada) e erro de rede param a drenagem inteira (a proxima tentativa
  // resolve sozinha, nao adianta insistir nos seguintes agora); 400 (dado
  // invalido — nao deveria acontecer, mas nao pode travar o outbox pra
  // sempre) descarta so aquele registro e segue pros outros.
  function drainOutbox() {
    var slug = planSlug();
    if (!slug || !navigator.onLine) { return Promise.resolve(); }

    return listEntries().then(function (entries) {
      var chain = Promise.resolve();
      entries.forEach(function (entry) {
        chain = chain.then(function () {
          return postJson('/renan/' + slug + '/carga', entry).then(function (result) {
            if (result.ok) { return removeEntry(entry.idempotency_key); }
            if (result.status === 400) { return removeEntry(entry.idempotency_key); }
            return Promise.reject(new Error('drain interrompido, status ' + result.status));
          });
        });
      });
      return chain.catch(function () { /* proxima tentativa (online/load) resolve */ });
    });
  }

  /* ══ DICA DE ULTIMA CARGA ═══════════════════════════════════════ */

  function fetchLastLoadByMovement() {
    var slug = planSlug();
    if (!slug) { return Promise.resolve({}); }
    return window.fetch('/renan/' + slug + '/pacote.json', { credentials: 'same-origin' })
      .then(function (response) { return response.ok ? response.json() : {}; })
      .then(function (data) { return data.last_load_by_movement || {}; })
      .catch(function () { return {}; });
  }

  function paintHints(lastLoadByMovement) {
    document.querySelectorAll('[data-workout-load-input]').forEach(function (widget) {
      var slug = widget.getAttribute('data-movement-slug');
      var entry = lastLoadByMovement[slug];
      var hint = widget.querySelector('[data-workout-load-hint]');
      var field = widget.querySelector('[data-workout-load-field]');
      if (!entry || entry.weight_kg === null || entry.weight_kg === undefined || !hint) { return; }

      var weight = entry.weight_kg;
      hint.textContent = 'Última vez: ' + weight + ' kg — toque pra usar';
      hint.addEventListener('click', function () {
        if (!field) { return; }
        field.value = weight;
        markDirty(field);
      });
    });
  }

  /* ══ UI POR MOVIMENTO ═══════════════════════════════════════════ */

  function setStatus(widget, text, isError) {
    var status = widget.querySelector('[data-workout-load-status]');
    if (!status) { return; }
    status.textContent = text;
    status.classList.toggle('workout-load-input__status--error', !!isError);
  }

  function buildEntryFromWidget(widget, weightKg) {
    return {
      idempotency_key: uuid(),
      movement_slug: widget.getAttribute('data-movement-slug'),
      program_id: widget.getAttribute('data-program-id') || '',
      weight_kg: weightKg,
      performed_on: todayIso(),
    };
  }

  function pulseSuccess(widget) {
    widget.classList.add('workout-load-input--saved');
    window.setTimeout(function () { widget.classList.remove('workout-load-input--saved'); }, 1200);
  }

  function saveWidget(widget) {
    var field = widget.querySelector('[data-workout-load-field]');
    var raw = field && field.value ? parseFloat(field.value.replace(',', '.')) : null;
    if (raw === null || isNaN(raw) || raw < 0) {
      setStatus(widget, 'Digite um peso válido antes de salvar.', true);
      return;
    }

    var entry = buildEntryFromWidget(widget, raw);
    setStatus(widget, 'Salvando…', false);
    queueEntry(entry)
      .then(function () {
        field.removeAttribute('data-dirty');
        return drainOutbox();
      })
      .then(function () { return listEntries(); })
      .then(function (remaining) {
        var stillPending = remaining.some(function (e) { return e.idempotency_key === entry.idempotency_key; });
        setStatus(widget, stillPending ? 'Salvo — será enviado quando a conexão voltar.' : 'Salvo ✓', false);
        pulseSuccess(widget);
      })
      .catch(function () {
        setStatus(widget, 'Não foi possível guardar o registro neste aparelho.', true);
      });
  }

  function markDirty(field) {
    field.setAttribute('data-dirty', '1');
  }

  // Steps do valor atual do campo (ou 0, se vazio) — nunca deixa negativo,
  // mesmo padrao de min="0" do <input type=number>.
  function stepField(field, delta) {
    var current = field.value ? parseFloat(field.value.replace(',', '.')) : 0;
    if (isNaN(current)) { current = 0; }
    var next = Math.max(0, Math.round((current + delta) * 100) / 100);
    field.value = next;
    markDirty(field);
  }

  // Rascunho em visibilitychange (item 8): campo com valor digitado mas
  // nao salvo entra no outbox mesmo sem o aluno clicar em "Salvar" — cobre
  // o caso comum no celular de trocar de app/apagar a tela no meio do
  // registro. Mesma fila de entrega do clique manual (nao um rascunho a
  // parte): assim ate um app fechado em segundo plano ja deixou o dado
  // em local seguro pra subir na proxima chance.
  function saveDirtyDrafts() {
    document.querySelectorAll('[data-workout-load-field][data-dirty]').forEach(function (field) {
      var raw = field.value ? parseFloat(field.value.replace(',', '.')) : null;
      if (raw === null || isNaN(raw) || raw < 0) { return; }
      var widget = field.closest('[data-workout-load-input]');
      if (!widget) { return; }
      queueEntry(buildEntryFromWidget(widget, raw));
      field.removeAttribute('data-dirty');
    });
  }

  function wireWidgets() {
    document.querySelectorAll('[data-workout-load-input]').forEach(function (widget) {
      var field = widget.querySelector('[data-workout-load-field]');
      var saveBtn = widget.querySelector('[data-workout-load-save]');
      if (field) { field.addEventListener('input', function () { markDirty(field); }); }
      if (saveBtn) { saveBtn.addEventListener('click', function () { saveWidget(widget); }); }
      widget.querySelectorAll('[data-workout-load-step]').forEach(function (stepBtn) {
        var delta = parseFloat(stepBtn.getAttribute('data-workout-load-step'));
        stepBtn.addEventListener('click', function () { stepField(field, delta); });
      });
    });
  }

  /* ══ BOOT ═══════════════════════════════════════════════════════ */

  function init() {
    if (!planSlug()) { return; }
    wireWidgets();
    drainOutbox();
    fetchLastLoadByMovement().then(paintHints);
    document.addEventListener('visibilitychange', function () {
      if (document.visibilityState === 'hidden') { saveDirtyDrafts(); }
    });
    window.addEventListener('online', drainOutbox);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Exportado pro hook de logout que ainda nao existe (ver docstring) e
  // pra inspecao/teste manual sem reescrever a fila.
  window.PublicWorkoutLoadTracker = {
    drainOutbox: drainOutbox,
    clearOutbox: clearOutbox,
    listEntries: listEntries,
  };
})();
