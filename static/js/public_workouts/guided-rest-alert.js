/* Aviso push do fim do descanso, para o app fechado ou a tela bloqueada.
 *
 * O iOS congela o PWA segundos depois que ele sai da tela: o bipe e a vibração
 * do modo foco param ali. Ao começar o descanso, o app pede ao servidor um push
 * no horário final (worker run_public_workout_rest_alerts); "+30 s" reagenda e
 * pular ou encerrar cancela. Se a tela ainda estiver à vista perto do fim, o
 * próprio app toca o bipe e cancela o aviso antes do envio: o iOS mostra todo
 * push recebido, então é o cancelamento que evita o alerta duplo. Enquanto o
 * aviso estiver de pé (covers), o modo foco não bipa nem vibra por cima dele.
 * Só age com este aparelho inscrito nos avisos. Rede, relógio, visibilidade e
 * inscrição são injetáveis para os testes em Node.
 */
(function () {
  'use strict';

  // Folga para o cancelamento chegar ao servidor antes do horário de envio.
  var CANCEL_LEAD_MS = 4000;
  // Descanso que já está acabando não vale um push (o servidor exige 1 s).
  var MIN_REMAINING_MS = 1500;
  var APP_SCOPE = '/renan/';

  function cookie(name) {
    var part = (document.cookie || '').split(';').map(function (item) { return item.trim(); })
      .find(function (item) { return item.indexOf(name + '=') === 0; });
    return part ? decodeURIComponent(part.slice(name.length + 1)) : '';
  }

  function browserSend(url) {
    return function (method, body, keepalive) {
      return fetch(url, {
        method: method, credentials: 'same-origin', keepalive: !!keepalive,
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': cookie('csrftoken') },
        body: JSON.stringify(body),
      }).then(function (response) {
        if (!response.ok) throw new Error('rest-alert-' + response.status);
      });
    };
  }

  function browserEndpoint() {
    try {
      if (!('serviceWorker' in navigator) || !window.Notification || window.Notification.permission !== 'granted') {
        return Promise.resolve(null);
      }
      return navigator.serviceWorker.getRegistration(APP_SCOPE).then(function (registration) {
        return registration ? registration.pushManager.getSubscription() : null;
      }).then(function (subscription) {
        return subscription ? subscription.endpoint : null;
      }).catch(function () { return null; });
    } catch (_) { return Promise.resolve(null); }
  }

  function create(options) {
    options = options || {};
    var noop = function () {};
    if (!options.url && !options.send) {
      return { started: noop, cleared: noop, ended: noop, tick: noop, hidden: noop, remap: noop, covers: noop };
    }
    var send = options.send || browserSend(options.url);
    var endpoint = options.endpoint || browserEndpoint;
    var describe = options.describe || function () { return {}; };
    var now = options.now || function () { return Date.now(); };
    var isVisible = options.isVisible || function () { return document.visibilityState === 'visible'; };
    var rest = null;   // descanso corrente: { sessionId, endAt }
    var armed = null;  // sessão que pode ter aviso pendente no servidor
    // Em fila: um cancelamento nunca chega ao servidor antes do agendamento anterior.
    var chain = Promise.resolve();

    function enqueue(job) {
      chain = chain.then(job).catch(function () { /* aviso é conforto: a falha não trava o treino */ });
      return chain;
    }

    function schedule(keepalive) {
      if (!rest) return chain;
      var target = rest;
      armed = target.sessionId;
      return enqueue(function () {
        return endpoint().then(function (device) {
          var remaining = target.endAt - now();
          if (!device || rest !== target || remaining < MIN_REMAINING_MS) {
            if (armed === target.sessionId && rest === target) armed = null;
            return null;
          }
          var label = describe() || {};
          return send('POST', {
            session_id: target.sessionId, endpoint: device, remaining_ms: Math.round(remaining),
            exercise: label.exercise || '', set_number: label.setNumber || null,
          }, keepalive).catch(function (error) {
            if (armed === target.sessionId && rest === target) armed = null;
            throw error;
          });
        });
      });
    }

    function cancel(keepalive) {
      if (!armed) return chain;
      var sessionId = armed;
      armed = null;
      return enqueue(function () { return send('DELETE', { session_id: sessionId }, keepalive); });
    }

    return {
      // Descanso começou, ganhou +30 s ou foi retomado depois de recarregar.
      started: function (sessionId, endAt) {
        if (!sessionId || !(endAt > now())) return chain;
        rest = { sessionId: sessionId, endAt: endAt };
        return schedule(false);
      },
      // Pulou o descanso, encerrou o treino ou a série foi desfeita.
      cleared: function () {
        rest = null;
        return cancel(false);
      },
      // O relógio chegou a zero: o aviso já saiu ou foi cancelado perto do fim.
      ended: function () {
        rest = null;
        armed = null;
      },
      // Com a tela à vista, o bipe do app basta: cancela antes do envio.
      tick: function (remainingMs) {
        if (armed && rest && remainingMs <= CANCEL_LEAD_MS && isVisible()) return cancel(false);
        return chain;
      },
      // Saiu da tela depois do cancelamento: agenda de novo enquanto houver tempo.
      hidden: function () {
        if (rest && !armed && rest.endAt - now() >= MIN_REMAINING_MS) return schedule(true);
        return chain;
      },
      // O início offline ganhou id do servidor: só agora o aviso pode ser agendado.
      remap: function (localId, serverId) {
        if (!rest || rest.sessionId !== localId) return chain;
        rest = { sessionId: serverId, endAt: rest.endAt };
        return schedule(false);
      },
      // O push deste descanso está agendado e ninguém o cancelou: o fim é avisado
      // por ele (tela bloqueada, ou o iPhone que volta à tela depois do envio).
      // Sem inscrição, com o agendamento recusado ou depois do cancelamento
      // perto do fim, o aviso volta a ser o bipe do app.
      covers: function () { return !!armed; },
    };
  }

  window.CurvaGuidedRestAlert = { create: create, CANCEL_LEAD_MS: CANCEL_LEAD_MS };
}());
