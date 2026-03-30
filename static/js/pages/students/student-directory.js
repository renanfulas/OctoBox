/**
 * ARQUIVO: comportamentos locais do diretorio de alunos.
 *
 * POR QUE ELE EXISTE:
 * - move a interacao de importacao e bulk actions para um arquivo JS estatico.
 * - reforca navegacao por teclado e feedback acessivel no diretorio.
 */

document.addEventListener('DOMContentLoaded', function() {
    var importForm = document.getElementById('import-form');
    var importFile = document.getElementById('student-import-file');

    if (importForm && importFile) {
        importFile.addEventListener('change', function() {
            if (importFile.files && importFile.files.length > 0) {
                importForm.submit();
            }
        });
    }

    var bulkForm = document.getElementById('bulk-action-form');
    var selectAll = document.getElementById('bulk-select-all');
    var actionBar = document.getElementById('bulk-action-bar');
    var countSpan = document.getElementById('bulk-selected-count');
    var statusNode = document.getElementById('student-bulk-status');
    var checkboxes = Array.from(document.querySelectorAll('.bulk-select-item'));
    var rows = Array.from(document.querySelectorAll('[data-student-row]'));

    function checkedCount() {
        return document.querySelectorAll('.bulk-select-item:checked').length;
    }

    function updateActionBar() {
        if (!actionBar || !countSpan) {
            return;
        }

        var count = checkedCount();
        countSpan.textContent = String(count);
        actionBar.hidden = count === 0;

        if (statusNode) {
            if (count === 0) {
                statusNode.textContent = 'Nenhum aluno selecionado.';
            } else if (count === 1) {
                statusNode.textContent = '1 aluno selecionado para acao em lote.';
            } else {
                statusNode.textContent = String(count) + ' alunos selecionados para acao em lote.';
            }
        }

        if (selectAll) {
            selectAll.checked = count > 0 && count === checkboxes.length;
            selectAll.indeterminate = count > 0 && count < checkboxes.length;
        }
    }

    if (selectAll) {
        selectAll.addEventListener('change', function() {
            checkboxes.forEach(function(checkbox) {
                checkbox.checked = selectAll.checked;
            });
            updateActionBar();
        });
    }

    checkboxes.forEach(function(checkbox) {
        checkbox.addEventListener('change', updateActionBar);
    });

    if (bulkForm) {
        bulkForm.addEventListener('submit', function(event) {
            if (checkedCount() === 0) {
                event.preventDefault();
                return;
            }

            var confirmed = window.confirm('Aplicar esta acao aos alunos selecionados? Falhas pontuais serao ignoradas.');
            if (!confirmed) {
                event.preventDefault();
            }
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

    updateActionBar();
});
