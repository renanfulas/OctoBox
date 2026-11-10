/* Faixa de conexão do app (F1 offline-first,
 * docs/plans/curva-offline-first-estrategia.md §3.1).
 *
 * Duas origens possíveis da página:
 * - cópia salva no aparelho: o service worker marca o <body> com
 *   data-offline-snapshot="<epoch ms>" ao servi-la sem rede. A faixa fica
 *   sempre à vista com a data da cópia; quando a rede volta, oferece
 *   "Atualizar" (não recarrega sozinha — o aluno pode estar no meio de uma
 *   série; o guiado e as cargas já drenam a fila no evento `online`).
 *   A cópia começa SEMPRE em "modo offline", mesmo com navigator.onLine
 *   true: ela abriu porque a rede falhou — inclusive na internet "conectada,
 *   mas sem resposta" da academia, em que onLine mente. Só o evento `online`
 *   (a conexão voltou de fato) troca para "Conexão de volta".
 * - página viva da rede: a faixa só aparece enquanto o aparelho está sem
 *   conexão e some quando ela volta.
 */
(function () {
  'use strict';

  var banner = document.querySelector('[data-offline-banner]');
  if (!banner) return;
  var copy = banner.querySelector('[data-offline-banner-copy]');
  var reload = banner.querySelector('[data-offline-banner-reload]');
  var savedAt = Number(document.body.dataset.offlineSnapshot || 0);
  var reconnected = false;

  function pad(value) { return (value < 10 ? '0' : '') + value; }

  function savedLabel() {
    var date = new Date(savedAt);
    return pad(date.getDate()) + '/' + pad(date.getMonth() + 1)
      + ' às ' + pad(date.getHours()) + ':' + pad(date.getMinutes());
  }

  function paint() {
    if (savedAt) {
      banner.hidden = false;
      banner.dataset.state = reconnected ? 'reconnected' : 'offline';
      copy.textContent = reconnected
        ? 'Conexão de volta. Seus registros estão sendo enviados; atualize para ver os dados mais recentes.'
        : 'Modo offline · treino salvo em ' + savedLabel()
          + '. Seus registros ficam neste aparelho e são enviados quando a conexão voltar.';
      reload.hidden = !reconnected;
      return;
    }
    var online = navigator.onLine;
    banner.hidden = online;
    banner.dataset.state = 'offline';
    copy.textContent = online ? '' : 'Sem conexão. Seus registros ficam neste aparelho e são enviados quando a conexão voltar.';
    reload.hidden = true;
  }

  reload.addEventListener('click', function () { window.location.reload(); });
  window.addEventListener('online', function () { reconnected = true; paint(); });
  window.addEventListener('offline', function () { reconnected = false; paint(); });
  paint();
}());
