(function() {
  function setupManifestoModal() {
    var modal = document.getElementById('manager-manifesto-modal');
    var trigger = document.getElementById('trigger-manifesto-modal');
    var closer = document.getElementById('close-manifesto-modal');

    if (!modal || !trigger || !closer || typeof modal.showModal !== 'function') {
      return;
    }

    trigger.addEventListener('click', function() {
      modal.showModal();
    });

    closer.addEventListener('click', function() {
      modal.close();
      trigger.focus();
    });

    modal.addEventListener('click', function(event) {
      var rect = modal.getBoundingClientRect();
      var clickedInside =
        rect.top <= event.clientY &&
        event.clientY <= rect.top + rect.height &&
        rect.left <= event.clientX &&
        event.clientX <= rect.left + rect.width;

      if (!clickedInside) {
        modal.close();
        trigger.focus();
      }
    });
  }

  function buildSuccessMarkup(actionName) {
    return (
      '<div class="dashboard-advisor-success">' +
        '<div class="dashboard-advisor-success-icon" aria-hidden="true">' +
          '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">' +
            '<polyline points="20 6 9 17 4 12"></polyline>' +
          '</svg>' +
        '</div>' +
        '<strong class="dashboard-advisor-success-title">Mandou bem, Maestro!</strong>' +
        '<span class="dashboard-advisor-success-copy">Acao: ' + actionName + '</span>' +
      '</div>'
    );
  }

  function resolveAdvisorItem(itemId, actionName, externalUrl) {
    var el = document.getElementById(itemId);
    if (!el) {
      return;
    }

    if (externalUrl) {
      window.open(externalUrl, '_blank', 'noopener');
    }

    el.style.height = el.offsetHeight + 'px';
    el.classList.add('dashboard-advisor-item--processing');

    setTimeout(function() {
      el.innerHTML = buildSuccessMarkup(actionName);
      el.classList.remove('dashboard-advisor-item--processing');
      el.classList.add('dashboard-advisor-item--success');

      setTimeout(function() {
        el.classList.add('dashboard-advisor-item--collapsed');
        setTimeout(function() {
          el.remove();
        }, 420);
      }, 2500);
    }, 400);
  }

  document.addEventListener('click', function(event) {
    var trigger = event.target.closest('[data-advisor-action="resolve-item"]');
    if (!trigger) {
      return;
    }

    resolveAdvisorItem(
      trigger.getAttribute('data-advisor-item'),
      trigger.getAttribute('data-advisor-result') || 'Registrado',
      trigger.getAttribute('data-external-url')
    );
  });

  setupManifestoModal();
}());
