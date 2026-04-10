/**
 * ARQUIVO: interactive_tabs.js
 * 
 * POR QUE ELE EXISTE:
 * - escuta os cliques nos KPI Cards (trigges) e alterna a exibicao dos paineis usando classes CSS.
 * - adiciona rolagem suave garantindo que a topbar nao sobreponha o limite de leitura.
 */

document.addEventListener('DOMContentLoaded', function() {
    var triggers = document.querySelectorAll('[data-action^="open-tab-"]');
    if (!triggers.length) return;

    function syncTriggerSelection(targetPanel, action) {
        var scopeRoot = targetPanel ? (targetPanel.closest('[data-page]') || document) : document;
        var cardGrid = scopeRoot.querySelector('.interactive-tab-triggers');
        if (!cardGrid) {
            return;
        }

        var allCards = cardGrid.querySelectorAll('.card');
        allCards.forEach(function(card) {
            card.classList.remove('is-selected-tab');
        });

        var linkedTrigger = cardGrid.querySelector('[data-action="' + action + '"]');
        if (!linkedTrigger) {
            return;
        }

        var currentCard = linkedTrigger.closest('.card') || linkedTrigger;
        currentCard.classList.add('is-selected-tab');
    }

    function activatePanelById(targetId, options) {
        var targetPanel = document.getElementById(targetId);
        if (!targetPanel) return null;

        var container = targetPanel.closest('.interactive-tab-container');
        if (container) {
            Array.from(container.children).forEach(function(child) {
                child.classList.remove('is-tab-active');
            });
        }

        targetPanel.classList.add('is-tab-active');

        if (targetId === 'tab-students-filters' && !(options && options.skipCoDependentDirectory) && !window.location.search.includes('keep_open=true')) {
            var directoryPanel = document.getElementById('tab-students-directory');
            if (directoryPanel) {
                directoryPanel.classList.add('is-tab-active');
            }
        }

        var selectionAction = options && options.action ? options.action : 'open-tab-' + targetId.replace(/^tab-/, '');
        syncTriggerSelection(targetPanel, selectionAction);
        return targetPanel;
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

        activatePanelById(firstPanel.id);
    }

    triggers.forEach(function(trigger) {
        trigger.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Pega o ID alvo (ex: 'open-tab-students-filters' -> 'tab-students-filters')
            var action = this.getAttribute('data-action');
            var targetId = this.getAttribute('data-target-panel') || action.replace('open-tab-', 'tab-');
            var targetPanel = document.getElementById(targetId);
            
            if (!targetPanel) return;
            
            // Se o painel ja esta ativo (toggle), minimiza-o e para.
            if (targetPanel.classList.contains('is-tab-active')) {
                var currentCardActive = this.closest('.card') || this;
                if (!currentCardActive.classList.contains('is-selected-tab')) {
                    activatePanelById(targetId, { action: action });
                    return;
                }

                targetPanel.classList.remove('is-tab-active');
                
                var cardGridToggle = this.closest('.interactive-tab-triggers');
                if (cardGridToggle) {
                    currentCardActive.classList.remove('is-selected-tab');
                }
                return;
            }
            
            activatePanelById(targetId, { action: action });
            
            // Scroll suave compensando a altura da topbar fixa (ex: 80px)
            if (this.dataset.noScroll !== "true") {
                var triggerElement = this;
                setTimeout(function() {
                    var scrollTarget = targetPanel;
                    var href = triggerElement.getAttribute('href');
                    if (href && href.startsWith('#') && href.length > 1) {
                        var innerTarget = document.getElementById(href.substring(1));
                        if (innerTarget) scrollTarget = innerTarget;
                    }
                    var yOffset = -90; 
                    var y = scrollTarget.getBoundingClientRect().top + window.scrollY + yOffset;
                    window.scrollTo({top: y, behavior: 'smooth'});
                }, 60);
            } else {
                // Reseta a flag apos o uso inicial
                delete this.dataset.noScroll;
            }
        });
    });

    document.querySelectorAll('.interactive-tab-container').forEach(function(container) {
        activateDefaultPanel(container);
    });

    // Auto-open filters if the URL contains filtering queries
    if (window.location.search && window.location.search.length > 1) {
        var params = new URLSearchParams(window.location.search);
        var hasFilter = params.has('query') || params.has('student_status') || params.has('commercial_status') || params.has('payment_status') || params.has('created_window') || params.has('keep_open');
        
        if (hasFilter) {
            activatePanelById('tab-students-directory');
        } else if (params.has('page')) {
            activatePanelById('tab-students-directory');
        }
    }
});
