(function () {
  if (!('serviceWorker' in navigator)) {
    return;
  }

  var deferredInstallPrompt = null;
  var mediaQuery = window.matchMedia ? window.matchMedia('(display-mode: standalone)') : null;
  var notificationPermission = ('Notification' in window && typeof window.Notification.permission === 'string')
    ? window.Notification.permission
    : 'unsupported';
  var activationElement = null;
  var installAction = null;
  var notificationAction = null;
  var installStatus = null;
  var notificationStatus = null;
  var copyElement = null;
  var installNote = null;
  var notificationNote = null;

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
    };
  }

  function syncNotificationPermission() {
    notificationPermission = ('Notification' in window && typeof window.Notification.permission === 'string')
      ? window.Notification.permission
      : 'unsupported';
  }

  function resolveActivationCopy(state) {
    if (state.activationComplete) {
      return 'Tudo certo. O app ja esta instalado e pronto para trabalhar com alertas.';
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
    if (state.notificationPermission === 'granted') {
      return 'Instalacao concluida. Falta so manter este app como seu ponto rapido de entrada no box.';
    }
    if (state.notificationPermission === 'denied') {
      return 'As notificacoes foram bloqueadas. Reative nas configuracoes do navegador para o app poder te alertar.';
    }
    if (!state.notificationSupported) {
      return 'Este navegador nao oferece o pacote completo de notificacoes push para o app. Abra no navegador principal do celular.';
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
  }

  function renderActivationUI(state) {
    bindActivationUI();
    if (!activationElement) {
      return;
    }

    activationElement.hidden = Boolean(state.activationComplete);
    if (copyElement) {
      copyElement.textContent = resolveActivationCopy(state);
    }

    updateStatusChip(
      installStatus,
      state.isStandalone ? 'PWA instalado' : 'PWA pendente',
      state.isStandalone ? 'done' : 'pending'
    );

    if (state.notificationPermission === 'granted') {
      updateStatusChip(notificationStatus, 'Notificacoes ativas', 'done');
    } else if (state.notificationPermission === 'denied') {
      updateStatusChip(notificationStatus, 'Notificacoes bloqueadas', 'blocked');
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
      notificationAction.hidden = Boolean(!state.isStandalone || state.notificationPermission === 'granted' || !state.notificationSupported);
      notificationAction.disabled = Boolean(!state.isStandalone || !state.notificationSupported);
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
      } else if (!state.isStandalone) {
        notificationNote.textContent = 'Depois de instalar, volte aqui e aceite as notificacoes para receber alertas do app.';
      } else if (state.notificationPermission === 'denied') {
        notificationNote.textContent = 'As notificacoes foram negadas. Reative nas configuracoes do navegador e volte para tentar de novo.';
      } else if (state.notificationPermission === 'granted') {
        notificationNote.textContent = 'Permissao concedida. Quando o trilho de envio estiver ativo, este aparelho podera receber alertas.';
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

  window.addEventListener('focus', publishPwaState);
  document.addEventListener('visibilitychange', function () {
    if (!document.hidden) {
      publishPwaState();
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
      publishPwaState();
    });
  });
})();
