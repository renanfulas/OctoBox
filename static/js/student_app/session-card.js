(function () {
  var cards = Array.prototype.slice.call(document.querySelectorAll('[data-session-link]'));

  function isInteractiveTarget(target) {
    return Boolean(target.closest('a, button, input, select, textarea, form, summary'));
  }

  cards.forEach(function (card) {
    var href = card.getAttribute('data-session-link');
    if (!href) {
      return;
    }

    card.addEventListener('click', function (event) {
      if (isInteractiveTarget(event.target)) {
        return;
      }
      window.location.href = href;
    });

    card.addEventListener('keydown', function (event) {
      if (event.key !== 'Enter' && event.key !== ' ') {
        return;
      }
      event.preventDefault();
      window.location.href = href;
    });
  });
}());
