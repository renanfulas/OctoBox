/*
ARQUIVO: navegacao local da estrutura do treino no editor do coach.

POR QUE ELE EXISTE:
- cria uma camada de overview e detalhe para blocos do treino sem depender do Smart Paste.
*/

(function () {
  var shell = document.querySelector('[data-coach-wod-structure]');
  if (!shell) return;

  var overview = shell.querySelector('[data-coach-wod-structure-overview]');
  var details = shell.querySelector('[data-coach-wod-structure-details]');
  if (!overview || !details) return;
  var lastTrigger = null;

  function openDetail(blockId, trigger) {
    if (!blockId) return;
    lastTrigger = trigger || null;
    overview.hidden = true;
    details.hidden = false;
    details.querySelectorAll('[data-coach-wod-structure-detail]').forEach(function (detail) {
      var isTarget = detail.getAttribute('data-coach-wod-structure-detail') === String(blockId);
      detail.classList.toggle('is-active', isTarget);
      detail.hidden = !isTarget;
      if (isTarget && typeof detail.scrollIntoView === 'function') {
        detail.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  }

  function closeDetail() {
    details.hidden = true;
    details.querySelectorAll('[data-coach-wod-structure-detail]').forEach(function (detail) {
      detail.classList.remove('is-active');
      detail.hidden = true;
    });
    overview.hidden = false;
    if (lastTrigger && typeof lastTrigger.focus === 'function') {
      lastTrigger.focus();
    }
  }

  shell.querySelectorAll('[data-coach-wod-structure-open]').forEach(function (button) {
    button.addEventListener('click', function () {
      openDetail(button.getAttribute('data-coach-wod-structure-open'), button);
    });
  });

  shell.querySelectorAll('[data-coach-wod-structure-back]').forEach(function (button) {
    button.addEventListener('click', function () {
      closeDetail();
    });
  });

  document.addEventListener('keydown', function (event) {
    if (event.key !== 'Escape') return;
    if (!details.hidden) {
      event.preventDefault();
      closeDetail();
    }
  });
})();
