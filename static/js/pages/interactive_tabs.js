/**
 * ARQUIVO: interactive_tabs.js
 *
 * POR QUE ELE EXISTE:
 * - escuta os cliques nos KPI cards e alterna a exibicao dos paineis usando classes CSS.
 * - adiciona rolagem suave garantindo que a topbar nao sobreponha o limite de leitura.
 */

document.addEventListener('DOMContentLoaded', function() {
    var triggers = document.querySelectorAll('[data-action^="open-tab-"]');
    if (!triggers.length) {
        return;
    }

    function activateDefaultPanel(container) {
        if (!container || container.querySelector('.is-tab-active')) {
            return;
        }

        var requestedPanelId = container.dataset.defaultPanel;
        var defaultPanel = requestedPanelId ? document.getElementById(requestedPanelId) : null;
        var firstPanel = defaultPanel || container.firstElementChild;
        if (!firstPanel || !firstPanel.id) {
            return;
        }

        firstPanel.classList.add('is-tab-active');

        var expectedAction = 'open-tab-' + firstPanel.id.replace(/^tab-/, '');
        var linkedTrigger = document.querySelector('[data-action="' + expectedAction + '"]');
        if (!linkedTrigger) {
            return;
        }

        var triggerCard = linkedTrigger.closest('.card') || linkedTrigger;
        triggerCard.classList.add('is-selected-tab');
    }

    triggers.forEach(function(trigger) {
        trigger.addEventListener('click', function(event) {
            event.preventDefault();

            var action = this.getAttribute('data-action');
            var targetId = action.replace('open-tab-', 'tab-');
            var targetPanel = document.getElementById(targetId);

            if (!targetPanel) {
                return;
            }

            if (targetPanel.classList.contains('is-tab-active')) {
                targetPanel.classList.remove('is-tab-active');

                var currentGrid = this.closest('.interactive-tab-triggers');
                if (currentGrid) {
                    var currentCardToggle = this.closest('.card') || this;
                    currentCardToggle.classList.remove('is-selected-tab');
                }
                return;
            }

            var container = targetPanel.closest('.interactive-tab-container');
            if (container) {
                Array.from(container.children).forEach(function(child) {
                    child.classList.remove('is-tab-active');
                });
            }

            targetPanel.classList.add('is-tab-active');

            var cardGrid = this.closest('.interactive-tab-triggers');
            if (cardGrid) {
                var allCards = cardGrid.querySelectorAll('.card');
                allCards.forEach(function(card) {
                    card.classList.remove('is-selected-tab');
                });

                var currentCard = this.closest('.card') || this;
                currentCard.classList.add('is-selected-tab');
            }

            if (this.dataset.noScroll !== 'true') {
                var triggerElement = this;
                setTimeout(function() {
                    var scrollTarget = targetPanel;
                    var href = triggerElement.getAttribute('href');
                    if (href && href.startsWith('#') && href.length > 1) {
                        var innerTarget = document.getElementById(href.substring(1));
                        if (innerTarget) {
                            scrollTarget = innerTarget;
                        }
                    }
                    var yOffset = -90;
                    var y = scrollTarget.getBoundingClientRect().top + window.scrollY + yOffset;
                    window.scrollTo({ top: y, behavior: 'smooth' });
                }, 60);
            } else {
                delete this.dataset.noScroll;
            }
        });
    });

    document.querySelectorAll('.interactive-tab-container').forEach(function(container) {
        activateDefaultPanel(container);
    });
});
