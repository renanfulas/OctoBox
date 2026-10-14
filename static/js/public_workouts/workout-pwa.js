(function () {
  'use strict';

  var slug = document.body.dataset.planSlug;
  if (!slug || !('serviceWorker' in navigator)) return;
  navigator.serviceWorker.register('/renan/sw.js?slug=' + encodeURIComponent(slug), {
    scope: '/renan/',
  }).catch(function () {});

  var banner = document.querySelector('[data-workout-install]');
  var button = banner && banner.querySelector('[data-workout-install-button]');
  var copy = banner && banner.querySelector('[data-workout-install-copy]');
  if (!banner || !button || !copy) return;
  if (window.matchMedia('(display-mode: standalone)').matches || navigator.standalone === true) return;
  var promptEvent = null;
  window.addEventListener('beforeinstallprompt', function (event) {
    event.preventDefault();
    promptEvent = event;
    copy.textContent = 'Instale o Curva para abrir seu treino pela tela inicial.';
    banner.hidden = false;
  });
  if (/iphone|ipad|ipod/i.test(navigator.userAgent)) {
    copy.textContent = 'No iPhone, use Compartilhar → Adicionar à Tela de Início.';
    button.hidden = true;
    banner.hidden = false;
  }
  button.addEventListener('click', function () {
    if (!promptEvent) return;
    promptEvent.prompt();
    promptEvent.userChoice.then(function () { banner.hidden = true; promptEvent = null; });
  });
  window.addEventListener('appinstalled', function () { banner.hidden = true; });
}());
