/* Faixa de conexão do app (F1 offline-first,
 * docs/plans/curva-offline-first-estrategia.md §3.1).
 *
 * Duas origens possíveis da página:
 * - cópia salva no aparelho: o service worker marca o <body> com
 *   data-offline-snapshot="<epoch ms>" ao servi-la sem rede. A faixa fica
 *   sempre à vista com a data da cópia; quando a rede volta, oferece
 *   "Atualizar" (não recarrega sozinha — o aluno pode estar no meio de uma
 *   série; o guiado e as cargas já drenam a fila no evento `online`).
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

  function pad(value) { return (value < 10 ? '0' : '') + value; }

  function savedLabel() {
    var date = new Date(savedAt);
    return pad(date.getDate()) + '/' + pad(date.getMonth() + 1)
      + ' às ' + pad(date.getHours()) + ':' + pad(date.getMinutes());
  }

  function paint() {
    var online = navigator.onLine;
    if (savedAt) {
      banner.hidden = false;
      banner.dataset.state = online ? 'reconnected' : 'offline';
      copy.textContent = online
        ? 'Conexão de volta. Seus registros estão sendo enviados; atualize para ver os dados mais recentes.'
        : 'Modo offline · treino salvo em ' + savedLabel()
          + '. Seus registros ficam neste aparelho e são enviados quando a conexão voltar.';
      reload.hidden = !online;
      return;
    }
    banner.hidden = online;
    banner.dataset.state = 'offline';
    copy.textContent = online ? '' : 'Sem conexão. Seus registros ficam neste aparelho e são enviados quando a conexão voltar.';
    reload.hidden = true;
  }

  reload.addEventListener('click', function () { window.location.reload(); });
  window.addEventListener('online', paint);
  window.addEventListener('offline', paint);
  paint();
}());
