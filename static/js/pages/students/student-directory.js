/**
 * ARQUIVO: comportamentos locais do diretorio de alunos.
 *
 * POR QUE ELE EXISTE:
 * - automatiza a busca e mantem a navegacao por linha da tabela.
 */

document.addEventListener('DOMContentLoaded', function() {
    var filterForm = document.getElementById('student-directory-filter-form');
    var searchInput = filterForm ? filterForm.querySelector('input[name="query"]') : null;
    var rows = Array.from(document.querySelectorAll('[data-student-row]'));

    if (filterForm && searchInput) {
        var searchTimer = null;
        searchInput.addEventListener('input', function() {
            window.clearTimeout(searchTimer);
            searchTimer = window.setTimeout(function() {
                filterForm.submit();
            }, 260);
        });
    }

    rows.forEach(function(row) {
        function openRowTarget() {
            var targetHref = row.getAttribute('data-href');
            if (targetHref) {
                window.location.assign(targetHref);
            }
        }

        row.addEventListener('click', function(event) {
            if (event.target.closest('[data-row-ignore-click], a, button, input, select, textarea, label')) {
                return;
            }

            openRowTarget();
        });

        row.addEventListener('keydown', function(event) {
            if (event.target.closest('[data-row-ignore-click], a, button, input, select, textarea, label')) {
                return;
            }

            if (event.key !== 'Enter' && event.key !== ' ') {
                return;
            }

            event.preventDefault();
            openRowTarget();
        });
    });
});
