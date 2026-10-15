(function () {
  'use strict';

  function cookie(name) {
    var part = (document.cookie || '').split(';').map(function (item) { return item.trim(); })
      .find(function (item) { return item.indexOf(name + '=') === 0; });
    return part ? decodeURIComponent(part.slice(name.length + 1)) : '';
  }

  function create(url, accountScope) {
    return function request(method, data) {
      if (method === 'POST' && data && accountScope) {
        data = Object.assign({}, data, { account_scope: accountScope });
      }
      return fetch(url, {
        method: method, credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': cookie('csrftoken') },
        body: data ? JSON.stringify(data) : undefined,
      }).then(function (response) {
        return response.text().then(function (body) {
          var result = {};
          try { result = JSON.parse(body); } catch (_) {}
          if (!response.ok) {
            var error = new Error(result.error || 'Não foi possível registrar o treino.');
            error.retryable = response.status >= 500;
            error.status = response.status;
            throw error;
          }
          return result;
        });
      }).catch(function (error) {
        if (error instanceof TypeError) error.retryable = true;
        throw error;
      });
    };
  }

  window.CurvaGuidedApi = { create: create };
}());
