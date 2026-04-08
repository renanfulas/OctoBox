(function() {
    var pageRoot = document.querySelector('[data-page="intake-center"]');
    if (!pageRoot) {
        return;
    }

    var sortPill = pageRoot.querySelector('[data-intake-sort="registration"]');
    var queueBoard = pageRoot.querySelector('#intake-queue-board');
    var tbody = queueBoard ? queueBoard.querySelector('tbody') : null;

    if (!sortPill || !tbody) {
        return;
    }

    var sortState = {
        sortBy: null,
        sortDirection: sortPill.getAttribute('data-sort-direction') || 'desc',
    };

    function getRegistrationAgeValue(row) {
        var rawValue = row.getAttribute('data-registration-age-days') || '0';
        var parsedValue = Number.parseInt(rawValue, 10);
        return Number.isNaN(parsedValue) ? 0 : parsedValue;
    }

    function sortRowsIfNeeded() {
        if (sortState.sortBy !== 'registration') {
            return;
        }

        var rows = Array.prototype.slice.call(tbody.querySelectorAll('.intake-directory-row'));
        rows.sort(function(leftRow, rightRow) {
            var compare = getRegistrationAgeValue(leftRow) - getRegistrationAgeValue(rightRow);

            if (sortState.sortDirection === 'desc') {
                compare *= -1;
            }

            if (compare !== 0) {
                return compare;
            }

            return leftRow.innerText.localeCompare(rightRow.innerText, 'pt-BR');
        });

        rows.forEach(function(row) {
            tbody.appendChild(row);
        });
    }

    function syncSortPill() {
        var isActive = sortState.sortBy === 'registration';
        sortPill.textContent = 'Data ' + (sortState.sortDirection === 'asc' ? '↑' : '↓');
        sortPill.classList.toggle('is-active', isActive);
        sortPill.setAttribute('aria-pressed', isActive ? 'true' : 'false');
    }

    sortPill.addEventListener('click', function() {
        if (sortState.sortBy === 'registration') {
            sortState.sortDirection = sortState.sortDirection === 'desc' ? 'asc' : 'desc';
        } else {
            sortState.sortBy = 'registration';
            sortState.sortDirection = sortPill.getAttribute('data-sort-direction') || 'desc';
        }

        syncSortPill();
        sortRowsIfNeeded();
    });

    syncSortPill();
})();
