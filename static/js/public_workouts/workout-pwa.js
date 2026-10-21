(function () {
  'use strict';

  var slug = document.body.dataset.planSlug;
  if (!slug) return;
  var banner = document.querySelector('[data-workout-install]');
  var homeButton = banner && banner.querySelector('[data-workout-install-button]');
  var copy = banner && banner.querySelector('[data-workout-install-copy]');
  var profileButton = document.querySelector('[data-workout-install-profile-button]');
  var profileStatus = document.querySelector('[data-workout-install-status]');
  var displayMode = window.matchMedia('(display-mode: standalone)');
  var isIOS = /iphone|ipad|ipod/i.test(navigator.userAgent);
  var promptEvent = null;

  function isInstalled() {
    return displayMode.matches || navigator.standalone === true;
  }

  function showInstalled() {
    if (banner) banner.hidden = true;
    if (profileButton) profileButton.hidden = true;
    if (profileStatus) profileStatus.textContent = 'App instalado neste dispositivo.';
  }

  function showAvailable() {
    if (isInstalled()) {
      showInstalled();
      return;
    }
    if (isIOS) {
      if (copy) copy.textContent = 'No iPhone, use Compartilhar → Adicionar à Tela de Início.';
      if (homeButton) homeButton.hidden = true;
      if (banner) banner.hidden = false;
      if (profileStatus) profileStatus.textContent = 'Para instalar no iPhone, use Compartilhar → Adicionar à Tela de Início.';
      return;
    }
    if (promptEvent) {
      if (copy) copy.textContent = 'Instale o Curva para abrir seu treino pela tela inicial.';
      if (banner) banner.hidden = false;
      if (homeButton) homeButton.hidden = false;
      if (profileButton) profileButton.hidden = false;
      if (profileStatus) profileStatus.textContent = 'Disponível para instalar neste dispositivo.';
      return;
    }
    if (banner) banner.hidden = true;
    if (profileButton) profileButton.hidden = true;
    if (profileStatus) profileStatus.textContent = 'Abra este treino no navegador para instalar o app.';
  }

  function install() {
    if (!promptEvent) return;
    var currentPrompt = promptEvent;
    promptEvent = null;
    currentPrompt.prompt();
    currentPrompt.userChoice.then(function (choice) {
      if (choice.outcome === 'accepted') {
        if (banner) banner.hidden = true;
        if (profileButton) profileButton.hidden = true;
        if (profileStatus) profileStatus.textContent = 'Concluindo instalação…';
      } else {
        showAvailable();
      }
    }).catch(showAvailable);
  }

  if (!('serviceWorker' in navigator)) {
    if (profileStatus) profileStatus.textContent = 'Instalação indisponível neste navegador.';
    return;
  }
  navigator.serviceWorker.register('/renan/sw.js?slug=' + encodeURIComponent(slug), {
    scope: '/renan/',
  }).catch(function () {});

  showAvailable();
  window.addEventListener('beforeinstallprompt', function (event) {
    event.preventDefault();
    promptEvent = event;
    showAvailable();
  });
  if (homeButton) homeButton.addEventListener('click', install);
  if (profileButton) profileButton.addEventListener('click', install);
  window.addEventListener('appinstalled', showInstalled);
  if (displayMode.addEventListener) displayMode.addEventListener('change', showAvailable);
}());
