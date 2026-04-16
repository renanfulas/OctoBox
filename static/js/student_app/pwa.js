(function () {
  if (!('serviceWorker' in navigator)) {
    return;
  }

  var deferredInstallPrompt = null;
  var mediaQuery = window.matchMedia ? window.matchMedia('(display-mode: standalone)') : null;

  function isStandalone() {
    return Boolean((mediaQuery && mediaQuery.matches) || window.navigator.standalone);
  }

  function publishPwaState() {
    var state = {
      canInstall: Boolean(deferredInstallPrompt),
      isStandalone: isStandalone(),
    };

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
      }
    });

    window.dispatchEvent(new CustomEvent('octobox:student-pwa-state', {
      detail: state
    }));
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
