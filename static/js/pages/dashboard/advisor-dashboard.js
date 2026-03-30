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
    var wrapper = document.createElement('div');
    var icon = document.createElement('div');
    var title = document.createElement('strong');
    var copy = document.createElement('span');
    var svgNamespace = 'http://www.w3.org/2000/svg';
    var svg = document.createElementNS(svgNamespace, 'svg');
    var polyline = document.createElementNS(svgNamespace, 'polyline');

    wrapper.className = 'dashboard-advisor-success';
    icon.className = 'dashboard-advisor-success-icon';
    icon.setAttribute('aria-hidden', 'true');

    svg.setAttribute('width', '24');
    svg.setAttribute('height', '24');
    svg.setAttribute('viewBox', '0 0 24 24');
    svg.setAttribute('fill', 'none');
    svg.setAttribute('stroke', 'currentColor');
    svg.setAttribute('stroke-width', '3');
    svg.setAttribute('stroke-linecap', 'round');
    svg.setAttribute('stroke-linejoin', 'round');
    polyline.setAttribute('points', '20 6 9 17 4 12');

    svg.appendChild(polyline);
    icon.appendChild(svg);

    title.className = 'dashboard-advisor-success-title';
    title.textContent = 'Mandou bem, Maestro!';
    copy.className = 'dashboard-advisor-success-copy';
    copy.textContent = 'Acao: ' + actionName;

    wrapper.appendChild(icon);
    wrapper.appendChild(title);
    wrapper.appendChild(copy);

    return wrapper;
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
      el.replaceChildren(buildSuccessMarkup(actionName));
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
