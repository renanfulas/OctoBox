(function () {
  'use strict';

  var box = document.querySelector('[data-workout-push]');
  if (!box) return;
  var enable = box.querySelector('[data-workout-push-enable]');
  var disable = box.querySelector('[data-workout-push-disable]');
  var status = box.querySelector('[data-workout-push-status]');
  if (!enable) return;
  var url = box.dataset.subscribeUrl;
  var key = box.dataset.publicKey;
  var optOutKey = 'curva-push-optout:' + location.pathname;
  var optInKey = 'curva-push-optin:' + location.pathname;
  var appBase = '/renan/';

  function optOut(value) {
    try {
      if (value === true) localStorage.setItem(optOutKey, '1');
      if (value === false) localStorage.removeItem(optOutKey);
      return localStorage.getItem(optOutKey) === '1';
    } catch (_) { return false; }
  }

  function optedIn(value) {
    try {
      if (value === true) localStorage.setItem(optInKey, '1');
      if (value === false) localStorage.removeItem(optInKey);
      return localStorage.getItem(optInKey) === '1';
    } catch (_) { return false; }
  }

  function cookie(name) {
    var item = (document.cookie || '').split(';').map(function (part) { return part.trim(); })
      .find(function (part) { return part.indexOf(name + '=') === 0; });
    return item ? decodeURIComponent(item.slice(name.length + 1)) : '';
  }

  function decodeKey(value) {
    var padding = '='.repeat((4 - value.length % 4) % 4);
    var raw = atob((value + padding).replace(/-/g, '+').replace(/_/g, '/'));
    return Uint8Array.from(raw, function (char) { return char.charCodeAt(0); });
  }

  function server(method, body) {
    return fetch(url, {
      method: method, credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': cookie('csrftoken') },
      body: JSON.stringify(body),
    }).then(function (response) {
      if (!response.ok) throw new Error('Não foi possível atualizar os avisos. Entre novamente e tente outra vez.');
    });
  }

  function paint(isActive) {
    enable.hidden = isActive;
    disable.hidden = !isActive;
    status.textContent = isActive
      ? 'Avisos ativos neste dispositivo.'
      : 'Avisos desativados neste dispositivo.';
  }

  if (!('serviceWorker' in navigator) || !('PushManager' in window) || !('Notification' in window)) {
    status.textContent = 'Este navegador não oferece avisos push para a Curva.';
    enable.hidden = true;
    return;
  }
  if (Notification.permission === 'denied') {
    status.textContent = 'Permissão bloqueada. Altere nas configurações do site.';
    enable.disabled = true;
  }

  navigator.serviceWorker.getRegistration(appBase).then(function (registration) {
    return registration ? registration.pushManager.getSubscription().then(function (subscription) {
      return { registration: registration, subscription: subscription };
    }) : { registration: null, subscription: null };
  }).then(function (state) {
    var subscription = state.subscription;
    if (subscription && optOut()) {
      var endpoint = subscription.endpoint;
      return subscription.unsubscribe().then(function () {
        return server('DELETE', { endpoint: endpoint });
      }).then(function () { paint(false); });
    }
    if (subscription) {
      enable.hidden = true;
      disable.hidden = false;
      return server('POST', { subscription: subscription.toJSON() })
        .then(function () {
          paint(true);
          if (Notification.permission === 'denied') status.textContent = 'Permissão bloqueada. Desative este dispositivo ou altere a configuração do site.';
        }).catch(function () {
          status.textContent = 'Este dispositivo pode estar associado a outra conta. Desative os avisos aqui e ative novamente.';
        });
    }
    if (state.registration && Notification.permission === 'granted' && optedIn() && !optOut() && key) {
      return state.registration.pushManager.subscribe({
        userVisibleOnly: true, applicationServerKey: decodeKey(key),
      }).then(function (renewed) {
        return server('POST', { subscription: renewed.toJSON() });
      }).then(function () {
        paint(true);
      }).catch(function () {
        status.textContent = 'Não foi possível renovar os avisos. Toque em ativar novamente.';
      });
    }
    paint(false);
    if (Notification.permission === 'denied') {
      status.textContent = 'Permissão bloqueada. Altere nas configurações do site.';
    }
  }).catch(function () { status.textContent = 'Não foi possível consultar o estado dos avisos.'; });

  enable.addEventListener('click', function () {
    enable.disabled = true;
    status.textContent = 'Ativando avisos…';
    navigator.serviceWorker.register(appBase + 'sw.js', { scope: appBase })
      .then(function (registration) {
        return Notification.requestPermission().then(function (permission) {
          if (permission !== 'granted') throw new Error('Permissão não concedida.');
          return registration.pushManager.getSubscription().then(function (existing) {
            return existing || registration.pushManager.subscribe({
              userVisibleOnly: true, applicationServerKey: decodeKey(key),
            });
          });
        });
      }).then(function (subscription) {
        return server('POST', { subscription: subscription.toJSON() });
      }).then(function () {
        optOut(false);
        optedIn(true);
        paint(true);
      }).catch(function (error) {
        status.textContent = error.message;
      }).finally(function () { enable.disabled = false; });
  });

  disable.addEventListener('click', function () {
    disable.disabled = true;
    optOut(true);
    optedIn(false);
    navigator.serviceWorker.getRegistration(appBase)
      .then(function (registration) { return registration ? registration.pushManager.getSubscription() : null; })
      .then(function (subscription) {
        if (!subscription) return;
        var endpoint = subscription.endpoint;
        return subscription.unsubscribe().then(function () { return server('DELETE', { endpoint: endpoint }); });
      }).then(function () { paint(false); })
      .catch(function (error) { status.textContent = error.message; })
      .finally(function () { disable.disabled = false; });
  });
}());
