(function () {
  var toggles = Array.prototype.slice.call(document.querySelectorAll('[data-preview-toggle]'));

  toggles.forEach(function (toggle) {
    toggle.addEventListener('click', function () {
      var dateValue = toggle.getAttribute('data-preview-toggle');
      var panel = document.querySelector('[data-preview-panel="' + dateValue + '"]');
      if (!panel) {
        return;
      }
      var expanded = toggle.getAttribute('aria-expanded') === 'true';
      document.querySelectorAll('[data-preview-panel]').forEach(function (item) {
        item.hidden = true;
      });
      document.querySelectorAll('[data-preview-toggle]').forEach(function (button) {
        button.setAttribute('aria-expanded', 'false');
      });
      panel.hidden = expanded;
      toggle.setAttribute('aria-expanded', expanded ? 'false' : 'true');
    });
  });
})();
