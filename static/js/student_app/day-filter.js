(function () {
  var filters = Array.prototype.slice.call(document.querySelectorAll('[data-filter-date]'));
  var sections = Array.prototype.slice.call(document.querySelectorAll('[data-day-section]'));
  var emptyState = document.querySelector('[data-day-empty-state]');

  if (!filters.length || !sections.length) {
    return;
  }

  function render(dateValue) {
    var hasMatch = false;
    filters.forEach(function (filterButton) {
      filterButton.setAttribute('aria-pressed', filterButton.getAttribute('data-filter-date') === dateValue ? 'true' : 'false');
    });
    sections.forEach(function (section) {
      var isMatch = section.getAttribute('data-day-section') === dateValue;
      section.hidden = !isMatch;
      hasMatch = hasMatch || isMatch;
    });
    if (emptyState) {
      emptyState.hidden = hasMatch;
    }
  }

  filters.forEach(function (filterButton) {
    filterButton.addEventListener('click', function () {
      render(filterButton.getAttribute('data-filter-date'));
    });
  });
})();
