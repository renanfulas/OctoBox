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

  function postLoad(slug, entry) {
    return window.fetch('/renan/' + slug + '/carga', {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken'),
        'X-Requested-With': 'XMLHttpRequest',
      },
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
    return window.fetch('/renan/' + slug + '/pacote.json', { credentials: 'same-origin' })
      .then(function (response) { return response.ok ? response.json() : {}; })
      .then(function (data) { return data.last_top_set_by_movement || {}; })
      .catch(function () { return {}; });
  }

  window.CurvaLoadApi = { postLoad: postLoad, lastTopSetByMovement: lastTopSetByMovement };
})();
