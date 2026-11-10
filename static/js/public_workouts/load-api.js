/* Transporte HTTP do registro de carga. Política de fila e mensagens pertencem ao controlador. */
(function () {
  'use strict';

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

  function postLoad(slug, entry, meta) {
    var headers = {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCookie('csrftoken'),
      'X-Requested-With': 'XMLHttpRequest',
    };
    // F3 offline-first: carga drenada da fila diz há quanto tempo esperava.
    if (meta && meta.queuedAt) headers['X-Curva-Queued-Ms'] = String(Math.max(0, Date.now() - meta.queuedAt));
    return window.fetch('/renan/' + slug + '/carga', {
      method: 'POST',
      credentials: 'same-origin',
      headers: headers,
      body: JSON.stringify(entry || {}),
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

  function lastTopSetByMovement(slug) {
    if (!slug) return Promise.resolve({});
    var url = '/renan/' + slug + '/pacote.json';
    // F2 offline-first: sem rede, as dicas de "última carga" vêm da cópia local.
    var read = window.CurvaOfflineData
      ? window.CurvaOfflineData.readJson(url).then(function (result) { return result.data; })
      : window.fetch(url, { credentials: 'same-origin' })
        .then(function (response) { return response.ok ? response.json() : {}; });
    return read
      .then(function (data) { return (data && data.last_top_set_by_movement) || {}; })
      .catch(function () { return {}; });
  }

  window.CurvaLoadApi = { postLoad: postLoad, lastTopSetByMovement: lastTopSetByMovement };
})();
