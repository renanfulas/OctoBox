/* Registro de abertura do app que o servidor não vê sozinho.
 *
 * A página viva já conta a abertura ao renderizar (PublicWorkoutDetailView).
 * Faltavam dois casos, que vão pela fila offline (offline-data.js) com o
 * horário do aparelho para POST /renan/<slug>/abertura:
 * - a página aberta da cópia salva sem internet (body[data-offline-snapshot]);
 * - a volta ao app que estava em segundo plano há 30 min ou mais (a página não
 *   recarrega, então nenhuma requisição chega ao servidor).
 * O servidor descarta duplicatas pela mesma janela de 30 min.
 */
(function () {
  'use strict';

  var data = window.CurvaOfflineData;
  var body = document.body;
  if (!data || !body.dataset.accountScope || !body.dataset.planSlug) return;

  var URL_OPEN = '/renan/' + body.dataset.planSlug + '/abertura';
  var RETURN_GAP_MS = 30 * 60000;
  var hiddenAt = document.hidden ? Date.now() : null;

  function record(at) {
    data.submit({ kind: 'open', key: 'open:' + at, url: URL_OPEN, payload: { opened_at: at } })
      .catch(function () {});
  }

  if (body.dataset.offlineSnapshot) record(Date.now());

  document.addEventListener('visibilitychange', function () {
    if (document.hidden) { hiddenAt = Date.now(); return; }
    if (hiddenAt !== null && Date.now() - hiddenAt >= RETURN_GAP_MS) record(Date.now());
    hiddenAt = null;
  });

  window.CurvaAppOpen = { record: record };
}());
