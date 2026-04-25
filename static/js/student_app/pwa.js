(function () {
  if (!('serviceWorker' in navigator)) {
    return;
  }

  var appRoot = document.body || document.documentElement;
  var deferredInstallPrompt = null;
  var mediaQuery = window.matchMedia ? window.matchMedia('(display-mode: standalone)') : null;
  var pushPublicKey = appRoot.dataset.studentWebPushPublicKey || '';
  var pushSubscribeUrl = appRoot.dataset.studentPushSubscribeUrl || '';
  var pushUnsubscribeUrl = appRoot.dataset.studentPushUnsubscribeUrl || '';
  var notificationPermission = ('Notification' in window && typeof window.Notification.permission === 'string')
    ? window.Notification.permission
    : 'unsupported';
  var currentPushSubscription = null;
  var activationElement = null;
  var installAction = null;
  var notificationAction = null;
  var installStatus = null;
  var notificationStatus = null;
  var copyElement = null;
  var installNote = null;
  var notificationNote = null;
  var installCard = null;
  var notificationCard = null;
  var dismissAction = null;
  var dismissKey = 'octobox_pwa_card_dismissed';

  function isIos() {
    var userAgent = (window.navigator.userAgent || '').toLowerCase();
    var platform = (window.navigator.platform || '').toLowerCase();
    return /iphone|ipad|ipod/.test(userAgent) || (platform === 'macintel' && window.navigator.maxTouchPoints > 1);
  }

  function isStandalone() {
    return Boolean((mediaQuery && mediaQuery.matches) || window.navigator.standalone);
  }

  function notificationSupportState() {
    return {
      notificationsApi: 'Notification' in window,
      pushManager: 'PushManager' in window,
      configured: Boolean(pushPublicKey),
    };
  }

  function syncNotificationPermission() {
    notificationPermission = ('Notification' in window && typeof window.Notification.permission === 'string')
      ? window.Notification.permission
      : 'unsupported';
  }

  function getCookie(name) {
    var cookieString = document.cookie || '';
    var cookieParts = cookieString.split(';');
    for (var index = 0; index < cookieParts.length; index += 1) {
      var part = cookieParts[index].trim();
      if (part.indexOf(name + '=') === 0) {
        return decodeURIComponent(part.slice(name.length + 1));
      }
    }
    return '';
  }

  function urlBase64ToUint8Array(base64String) {
    var padding = '='.repeat((4 - base64String.length % 4) % 4);
    var normalized = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
    var rawData = window.atob(normalized);
    var outputArray = new Uint8Array(rawData.length);
    for (var i = 0; i < rawData.length; i += 1) {
      outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
  }

  function parseJsonResponse(response) {
    return response.text().then(function (text) {
      if (!text) {
        return {};
      }
      try {
        return JSON.parse(text);
      } catch (error) {
        return {};
      }
    }).then(function (payload) {
      if (!response.ok) {
        return Promise.reject(payload);
      }
      return payload;
    });
  }

  function postJson(url, payload) {
    if (!url) {
      return Promise.resolve({});
    }
    return window.fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken'),
        'X-Requested-With': 'XMLHttpRequest'
      },
      body: JSON.stringify(payload || {})
    }).then(parseJsonResponse);
  }

  function serializeSubscription(subscription) {
    if (!subscription) {
      return null;
    }
    if (typeof subscription.toJSON === 'function') {
      return subscription.toJSON();
    }
    return {
      endpoint: subscription.endpoint,
      expirationTime: subscription.expirationTime,
    };
  }

  function syncSubscriptionWithBackend(subscription) {
    var serialized = serializeSubscription(subscription);
    if (!serialized || !pushSubscribeUrl) {
      return Promise.resolve(false);
    }
    return postJson(pushSubscribeUrl, { subscription: serialized }).then(function () {
      return true;
    }).catch(function () {
      return false;
    });
  }

  function revokeSubscriptionFromBackend(endpoint) {
    if (!endpoint || !pushUnsubscribeUrl) {
      return Promise.resolve(false);
    }
    return postJson(pushUnsubscribeUrl, { endpoint: endpoint }).then(function () {
      return true;
    }).catch(function () {
      return false;
    });
  }

  function refreshPushSubscriptionState() {
    if (!pushPublicKey || !('PushManager' in window)) {
      currentPushSubscription = null;
      publishPwaState();
      return Promise.resolve(null);
    }
    return navigator.serviceWorker.ready.then(function (registration) {
      return registration.pushManager.getSubscription();
    }).then(function (subscription) {
      currentPushSubscription = subscription;
      if (subscription && notificationPermission === 'granted') {
        return syncSubscriptionWithBackend(subscription).then(function () {
          publishPwaState();
          return subscription;
        });
      }
      publishPwaState();
      return subscription;
    }).catch(function () {
      currentPushSubscription = null;
      publishPwaState();
      return null;
    });
  }

  function ensurePushSubscription() {
    if (!pushPublicKey || !('PushManager' in window)) {
      publishPwaState();
      return Promise.resolve(null);
    }
    return navigator.serviceWorker.ready.then(function (registration) {
      return registration.pushManager.getSubscription().then(function (existingSubscription) {
        if (existingSubscription) {
          currentPushSubscription = existingSubscription;
          return syncSubscriptionWithBackend(existingSubscription).then(function () {
            publishPwaState();
            return existingSubscription;
          });
        }
        return registration.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: urlBase64ToUint8Array(pushPublicKey)
        }).then(function (subscription) {
          currentPushSubscription = subscription;
          return syncSubscriptionWithBackend(subscription).then(function () {
            publishPwaState();
            return subscription;
          });
        });
      });
    }).catch(function () {
      currentPushSubscription = null;
      publishPwaState();
      return null;
    });
  }

  function resolveActivationCopy(state) {
    if (state.activationComplete) {
      return 'Tudo certo. O app ja esta instalado e conectado ao trilho de notificacoes.';
    }
    if (!state.isStandalone && isIos()) {
      return 'Instale o app no iPhone primeiro. Depois volte aqui para liberar as notificacoes.';
    }
    if (!state.isStandalone && state.canInstall) {
      return 'Instale o app agora para transformar o OctoBox em atalho nativo no seu celular.';
    }
    if (!state.isStandalone) {
      return 'Abra o menu do navegador e instale o app no celular. Assim o OctoBox fica com cara de aplicativo de verdade.';
    }
    if (state.notificationPermission === 'denied') {
      return 'As notificacoes foram bloqueadas. Reative nas configuracoes do navegador para o app poder te alertar.';
    }
    if (!state.pushConfigured) {
      return 'O PWA ja pode ser instalado, mas o push ainda nao foi configurado neste ambiente.';
    }
    if (!state.notificationSupported) {
      return 'Este navegador nao oferece o pacote completo de notificacoes push para o app. Abra no navegador principal do celular.';
    }
    if (state.notificationPermission === 'granted' && !state.hasPushSubscription) {
      return 'Permissao concedida. Estamos terminando a assinatura push deste aparelho.';
    }
    return 'Instalacao concluida. Agora aceite as notificacoes para receber alertas do OctoBox.';
  }

  function updateStatusChip(element, label, state) {
    if (!element) {
      return;
    }
    element.textContent = label;
    element.dataset.state = state;
  }

  function shouldShowActivationCard(state) {
    if (state.activationComplete) {
      try {
        window.localStorage.removeItem(dismissKey);
      } catch (error) {
        // noop
      }
      return false;
    }
    try {
      return window.localStorage.getItem(dismissKey) !== '1';
    } catch (error) {
      return true;
    }
  }

  function bindActivationUI() {
    if (activationElement) {
      return;
    }
    activationElement = document.querySelector('[data-ui="student-pwa-activation"]');
    if (!activationElement) {
      return;
    }
    installAction = activationElement.querySelector('[data-ui="student-pwa-install-action"]');
    notificationAction = activationElement.querySelector('[data-ui="student-pwa-notification-action"]');
    installStatus = activationElement.querySelector('[data-ui="student-pwa-install-status"]');
    notificationStatus = activationElement.querySelector('[data-ui="student-pwa-notification-status"]');
    copyElement = activationElement.querySelector('[data-ui="student-pwa-copy"]');
    installNote = activationElement.querySelector('[data-ui="student-pwa-install-note"]');
    notificationNote = activationElement.querySelector('[data-ui="student-pwa-notification-note"]');
    installCard = activationElement.querySelector('[data-ui="student-pwa-install-card"]');
    notificationCard = activationElement.querySelector('[data-ui="student-pwa-notification-card"]');
    dismissAction = activationElement.querySelector('[data-ui="student-pwa-dismiss-action"]');

    if (installAction) {
      installAction.addEventListener('click', function () {
        if (!window.OctoBoxStudentPWA || typeof window.OctoBoxStudentPWA.promptInstall !== 'function') {
          return;
        }
        window.OctoBoxStudentPWA.promptInstall().finally(function () {
          publishPwaState();
        });
      });
    }

    if (notificationAction) {
        notificationAction.addEventListener('click', function () {
        if (!window.OctoBoxStudentPWA || typeof window.OctoBoxStudentPWA.requestNotifications !== 'function') {
          return;
        }
        window.OctoBoxStudentPWA.requestNotifications().finally(function () {
          publishPwaState();
        });
      });
    }

    if (dismissAction) {
      dismissAction.addEventListener('click', function () {
        try {
          window.localStorage.setItem(dismissKey, '1');
        } catch (error) {
          // noop
        }
        activationElement.hidden = true;
      });
    }
  }

  function renderActivationUI(state) {
    bindActivationUI();
    if (!activationElement) {
      return;
    }

    var hideInstallCard = Boolean(state.isStandalone);
    var hideNotificationCard = Boolean(
      state.notificationPermission === 'granted' ||
      state.notificationPermission === 'unsupported' ||
      !state.notificationSupported
    );

    activationElement.hidden = Boolean((hideInstallCard && hideNotificationCard) || !shouldShowActivationCard(state));
    if (copyElement) {
      copyElement.textContent = resolveActivationCopy(state);
    }

    if (installCard) {
      installCard.hidden = hideInstallCard;
    }

    if (notificationCard) {
      notificationCard.hidden = hideNotificationCard;
    }

    updateStatusChip(
      installStatus,
      state.isStandalone ? 'PWA instalado' : 'PWA pendente',
      state.isStandalone ? 'done' : 'pending'
    );

    if (state.notificationPermission === 'granted') {
      updateStatusChip(
        notificationStatus,
        state.hasPushSubscription ? 'Notificacoes ativas' : 'Sincronizando notificacoes',
        state.hasPushSubscription ? 'done' : 'pending'
      );
    } else if (state.notificationPermission === 'denied') {
      updateStatusChip(notificationStatus, 'Notificacoes bloqueadas', 'blocked');
    } else if (!state.pushConfigured) {
      updateStatusChip(notificationStatus, 'Push ainda nao configurado', 'blocked');
    } else if (!state.notificationSupported) {
      updateStatusChip(notificationStatus, 'Push indisponivel neste navegador', 'blocked');
    } else {
      updateStatusChip(notificationStatus, 'Notificacoes pendentes', 'pending');
    }

    if (installAction) {
      installAction.hidden = Boolean(state.isStandalone);
      installAction.disabled = Boolean(!state.canInstall && !isIos() && !state.isStandalone);
    }

    if (notificationAction) {
      notificationAction.hidden = Boolean(!state.isStandalone || hideNotificationCard);
      notificationAction.disabled = Boolean(!state.isStandalone || !state.notificationSupported || !state.pushConfigured);
    }

    if (installNote) {
      if (state.isStandalone) {
        installNote.textContent = 'App instalado neste aparelho.';
      } else if (isIos()) {
        installNote.textContent = 'No iPhone/iPad, toque em Compartilhar e depois em Adicionar a Tela de Inicio.';
      } else if (state.canInstall) {
        installNote.textContent = 'Toque em Instalar app para concluir a instalacao do PWA.';
      } else {
        installNote.textContent = 'Se o botao nao aparecer, use o menu do navegador e escolha Instalar app ou Adicionar a tela inicial.';
      }
    }

    if (notificationNote) {
      if (!state.notificationSupported) {
        notificationNote.textContent = 'Este navegador ainda nao oferece notificacoes push completas para este app.';
      } else if (!state.pushConfigured) {
        notificationNote.textContent = 'O trilho de push ainda nao foi configurado neste ambiente do OctoBox.';
      } else if (!state.isStandalone) {
        notificationNote.textContent = 'Depois de instalar, volte aqui e aceite as notificacoes para receber alertas do app.';
      } else if (state.notificationPermission === 'denied') {
        notificationNote.textContent = 'As notificacoes foram negadas. Reative nas configuracoes do navegador e volte para tentar de novo.';
      } else if (state.notificationPermission === 'granted') {
        notificationNote.textContent = state.hasPushSubscription
          ? 'Permissao concedida e assinatura push ativa neste aparelho.'
          : 'Permissao concedida. Estamos finalizando a assinatura push deste aparelho.';
      } else {
        notificationNote.textContent = 'Toque em Ativar notificacoes e aceite o pedido do navegador.';
      }
    }
  }

  function publishPwaState() {
    syncNotificationPermission();
    var notificationSupport = notificationSupportState();
    var state = {
      canInstall: Boolean(deferredInstallPrompt),
      isStandalone: isStandalone(),
      notificationPermission: notificationPermission,
      notificationSupported: Boolean(notificationSupport.notificationsApi && notificationSupport.pushManager),
      pushConfigured: Boolean(notificationSupport.configured),
      hasPushSubscription: Boolean(currentPushSubscription),
    };
    state.activationComplete = Boolean(state.isStandalone && state.notificationPermission === 'granted');

    window.OctoBoxStudentPWA = Object.assign({}, window.OctoBoxStudentPWA || {}, state, {
      promptInstall: function () {
        if (!deferredInstallPrompt) {
          return Promise.resolve(false);
        }
        deferredInstallPrompt.prompt();
        return deferredInstallPrompt.userChoice.then(function (choice) {
          deferredInstallPrompt = null;
          publishPwaState();
          return choice;
        });
      },
      requestNotifications: function () {
        if (!('Notification' in window) || typeof window.Notification.requestPermission !== 'function') {
          return Promise.resolve('unsupported');
        }
        return window.Notification.requestPermission().then(function (permission) {
          notificationPermission = permission;
          if (permission === 'granted') {
            return ensurePushSubscription().then(function () {
              publishPwaState();
              return permission;
            });
          }
          if (permission === 'denied' && currentPushSubscription) {
            var endpoint = currentPushSubscription.endpoint;
            return currentPushSubscription.unsubscribe().catch(function () {
              return false;
            }).then(function () {
              currentPushSubscription = null;
              return revokeSubscriptionFromBackend(endpoint);
            }).then(function () {
              publishPwaState();
              return permission;
            });
          }
          publishPwaState();
          return permission;
        });
      }
    });

    window.dispatchEvent(new CustomEvent('octobox:student-pwa-state', {
      detail: state
    }));
    renderActivationUI(state);
  }

  window.addEventListener('beforeinstallprompt', function (event) {
    event.preventDefault();
    deferredInstallPrompt = event;
    publishPwaState();
  });

  window.addEventListener('appinstalled', function () {
    deferredInstallPrompt = null;
    publishPwaState();
  });

  window.addEventListener('focus', refreshPushSubscriptionState);
  document.addEventListener('visibilitychange', function () {
    if (!document.hidden) {
      refreshPushSubscriptionState();
    }
  });

  if (mediaQuery && typeof mediaQuery.addEventListener === 'function') {
    mediaQuery.addEventListener('change', publishPwaState);
  } else if (mediaQuery && typeof mediaQuery.addListener === 'function') {
    mediaQuery.addListener(publishPwaState);
  }

  window.addEventListener('load', function () {
    navigator.serviceWorker.register('/aluno/sw.js', { scope: '/aluno/' }).catch(function () {
      // Falha silenciosa: o app do aluno continua funcional sem o registro.
    }).finally(function () {
      refreshPushSubscriptionState();
    });
  });
})();
