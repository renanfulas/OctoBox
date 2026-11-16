/* Selo global de registros aguardando envio e painel de pendências
 * (F0/F3 offline-first, docs/plans/curva-offline-first-estrategia.md §3.4).
 *
 * Só LÊ as filas locais e pinta um selo no topo, visível em todas as abas:
 * - treino guiado: curva-guided:<conta>:<slug>, store "commands" (pela
 *   conexão viva de guided-outbox.js quando ele está na página);
 * - cargas: public-workout-outbox:account:<conta>, store "pending-loads";
 * - avaliação e onboarding: fila de offline-data.js.
 * Quem grava e drena continua sendo cada módulo; a camada de armazenamento
 * avisa cada mudança pelo evento DOM 'curva:outbox-changed'.
 *
 * Tocar no selo abre o painel: quanto há em cada fila, há quanto tempo o mais
 * antigo espera e o que o servidor recusou e precisa de revisão (o conflito
 * se resolve onde ele nasceu: no treino guiado ou na aba Cargas).
 *
 * Abre o banco de cargas SEM número de versão de propósito: nunca dispara
 * upgrade num banco existente e um banco inexistente nasce vazio.
 */
(function () {
  'use strict';

  var badge = document.querySelector('[data-sync-badge]');
  if (!badge || !window.indexedDB) return;
  var panel = document.querySelector('[data-sync-panel]');
  var slug = document.body.dataset.planSlug;
  var accountScope = document.body.dataset.accountScope;
  if (!slug || !accountScope) return;

  var GUIDED_DB = 'curva-guided:' + accountScope + ':' + slug;
  var LOADS_DB = 'public-workout-outbox:account:' + accountScope;
  var MINUTE = 60000;

  function listStore(dbName, storeName) {
    return new Promise(function (resolve) {
      var request;
      try { request = window.indexedDB.open(dbName); } catch (_) { resolve([]); return; }
      request.onerror = function () { resolve([]); };
      request.onblocked = function () { resolve([]); };
      request.onsuccess = function () {
        var db = request.result;
        var finish = function (rows) {
          try { db.close(); } catch (_) {}
          resolve(rows || []);
        };
        if (!db.objectStoreNames.contains(storeName)) { finish([]); return; }
        var tx;
        try { tx = db.transaction(storeName, 'readonly'); } catch (_) { finish([]); return; }
        var reader = tx.objectStore(storeName).getAll();
        reader.onsuccess = function () { finish(reader.result); };
        reader.onerror = function () { finish([]); };
      };
    });
  }

  // Com o guiado na página, lê pela conexão que ele já mantém aberta: a série
  // online reaproveita uma conexão só, e o selo não pode quebrar isso.
  function guidedRows() {
    var outbox = window.CurvaGuidedOutbox;
    if (outbox && outbox.list) {
      return outbox.list(accountScope + ':' + slug).then(function (rows) { return rows || []; }, function () { return []; });
    }
    return listStore(GUIDED_DB, 'commands');
  }

  function otherRows() {
    var data = window.CurvaOfflineData;
    return data && data.list ? data.list().then(function (rows) { return rows || []; }, function () { return []; }) : Promise.resolve([]);
  }

  // Resumo único das três filas, no formato que o selo e o painel pintam.
  function summarize(guided, loads, others) {
    var oldest = null;
    function seen(at) { if (at && (oldest === null || at < oldest)) oldest = at; }
    guided.forEach(function (row) { seen(row.created_at); });
    loads.forEach(function (row) { seen(row.queued_at); });
    // Aberturas do app (app-open.js) vão pela mesma fila, mas não são
    // registros do aluno: não entram no selo nem no aviso de "Sair".
    others = others.filter(function (row) { return row.kind !== 'open'; });
    others.forEach(function (row) { seen(row.created_at); });
    return {
      total: guided.length + loads.length + others.length,
      guided: guided.length,
      guidedBlocked: guided.filter(function (row) { return row.blocked; }).length,
      loads: loads.length,
      loadsBlocked: loads.filter(function (row) { return row.sync_state === 'blocked'; }).length,
      assessments: others.filter(function (row) { return row.kind === 'assessment'; }).length,
      onboarding: others.filter(function (row) { return row.kind === 'onboarding'; }).length,
      oldest: oldest,
    };
  }

  function ago(at) {
    var minutes = Math.max(0, Math.floor((Date.now() - at) / MINUTE));
    if (minutes < 1) return 'agora há pouco';
    if (minutes < 60) return 'há ' + minutes + ' min';
    var hours = Math.floor(minutes / 60);
    if (hours < 24) return 'há ' + hours + ' h';
    var days = Math.floor(hours / 24);
    return days === 1 ? 'há 1 dia' : 'há ' + days + ' dias';
  }

  function plural(count, one, many) { return count + ' ' + (count === 1 ? one : many); }

  function paintPanel(summary) {
    if (!panel) return;
    var lines = [];
    if (summary.guided) lines.push('Treino guiado: ' + plural(summary.guided, 'registro', 'registros'));
    if (summary.loads) lines.push('Cargas: ' + plural(summary.loads, 'registro', 'registros'));
    if (summary.assessments) lines.push('Avaliações: ' + plural(summary.assessments, 'avaliação', 'avaliações'));
    if (summary.onboarding) lines.push('Tutorial concluído, aguardando envio');
    if (summary.oldest) lines.push('Mais antigo: ' + ago(summary.oldest));
    var warnings = [];
    if (summary.guidedBlocked) {
      warnings.push('Treino guiado: o servidor recusou ' + plural(summary.guidedBlocked, 'registro', 'registros')
        + '. Abra o treino guiado para revisar.');
    }
    if (summary.loadsBlocked) {
      warnings.push('Cargas: ' + plural(summary.loadsBlocked, 'registro precisa', 'registros precisam')
        + ' de revisão na aba Cargas.');
    }
    var status = navigator.onLine
      ? 'Enviando assim que o servidor responder.'
      : 'Sem conexão. Tudo fica salvo neste aparelho e é enviado quando a conexão voltar.';
    panel.replaceChildren();
    lines.concat(warnings).concat([status]).forEach(function (text, index) {
      var row = document.createElement('p');
      row.textContent = text;
      if (index >= lines.length && index < lines.length + warnings.length) row.className = 'is-warning';
      panel.appendChild(row);
    });
  }

  function paint() {
    return Promise.all([guidedRows(), listStore(LOADS_DB, 'pending-loads'), otherRows()]).then(function (lists) {
      var summary = summarize(lists[0], lists[1], lists[2]);
      if (!summary.total) {
        badge.hidden = true;
        badge.textContent = '';
        badge.setAttribute('aria-expanded', 'false');
        if (panel) panel.hidden = true;
        return summary.total;
      }
      var label = summary.total === 1 ? '1 registro a enviar' : summary.total + ' registros a enviar';
      if (summary.guidedBlocked || summary.loadsBlocked) label += ' · revisar';
      else if (!navigator.onLine) label += ' · sem conexão';
      badge.textContent = label;
      badge.hidden = false;
      paintPanel(summary);
      return summary.total;
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

  if (panel) {
    badge.addEventListener('click', function () {
      var open = panel.hidden;
      panel.hidden = !open;
      badge.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
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
