(function () {
    'use strict';

    const CONFIRM_WORD = 'ARQUIVAR';

    function initArchiveAllDialog() {
        const openBtn = document.querySelector('[data-wod-archive-all-open]');
        const dialog = document.querySelector('[data-wod-archive-all-dialog]');
        if (!openBtn || !dialog) return;

        const closeBtn = dialog.querySelector('[data-wod-archive-all-close]');
        const confirmInput = dialog.querySelector('[data-wod-archive-confirm-input]');
        const submitBtn = dialog.querySelector('[data-wod-archive-submit]');

        function updateSubmit() {
            const ready = confirmInput.value.trim().toUpperCase() === CONFIRM_WORD;
            submitBtn.disabled = !ready;
        }

        openBtn.addEventListener('click', function () {
            confirmInput.value = '';
            submitBtn.disabled = true;
            dialog.showModal();
        });

        if (closeBtn) {
            closeBtn.addEventListener('click', function () {
                dialog.close();
            });
        }

        dialog.addEventListener('click', function (e) {
            if (e.target === dialog) dialog.close();
        });

        confirmInput.addEventListener('input', updateSubmit);
    }

    document.addEventListener('DOMContentLoaded', initArchiveAllDialog);
})();
