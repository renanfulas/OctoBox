(function () {
    function clampPercent(value) {
        var numeric = Number(value);

        if (Number.isNaN(numeric)) {
            return 0;
        }

        if (numeric < 0) {
            return 0;
        }

        if (numeric > 100) {
            return 100;
        }

        return numeric;
    }

    function applyElement(node) {
        if (!node) {
            return;
        }

        if (node.hasAttribute('data-visual-width')) {
            node.style.setProperty('--dynamic-visual-width', clampPercent(node.dataset.visualWidth) + '%');
        }

        if (node.hasAttribute('data-visual-height')) {
            node.style.setProperty('--dynamic-visual-height', clampPercent(node.dataset.visualHeight) + '%');
        }

        if (node.hasAttribute('data-visual-columns')) {
            var columns = Number(node.dataset.visualColumns);
            node.style.setProperty('--dynamic-visual-columns', String(Number.isNaN(columns) || columns < 1 ? 1 : Math.round(columns)));
        }
    }

    function apply(root) {
        var scope = root || document;
        scope.querySelectorAll('[data-visual-width], [data-visual-height], [data-visual-columns]').forEach(applyElement);
    }

    window.OctoDynamicVisuals = {
        apply: apply,
        applyElement: applyElement
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function () {
            apply(document);
        });
        return;
    }

    apply(document);
}());
