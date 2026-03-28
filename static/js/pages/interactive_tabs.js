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

    triggers.forEach(function(trigger) {
        trigger.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Pega o ID alvo (ex: 'open-tab-students-filters' -> 'tab-students-filters')
            var action = this.getAttribute('data-action');
            var targetId = action.replace('open-tab-', 'tab-');
            var targetPanel = document.getElementById(targetId);
            
            if (!targetPanel) return;
            
            // Se o painel ja esta ativo (toggle), minimiza-o e para.
            if (targetPanel.classList.contains('is-tab-active')) {
                targetPanel.classList.remove('is-tab-active');
                
                var cardGridToggle = this.closest('.interactive-tab-triggers');
                if (cardGridToggle) {
                    var currentCardToggle = this.closest('.card') || this;
                    currentCardToggle.classList.remove('is-selected-tab');
                }
                return;
            }
            
            // Remove 'is-tab-active' de todos os irmãos no container
            var container = targetPanel.closest('.interactive-tab-container');
            if (container) {
                Array.from(container.children).forEach(function(child) {
                    child.classList.remove('is-tab-active');
                });
            }
            
            // Adiciona classe no alvo principal
            targetPanel.classList.add('is-tab-active');
            
            // Regra especial (Phase 13.5): Se o alvo for o form de Busca, a Tabela de Diretório vira co-dependente e deve abrir abaixo.
            if (targetId === 'tab-students-filters' && !window.location.search.includes('keep_open=true')) {
                var directoryPanel = document.getElementById('tab-students-directory');
                if (directoryPanel) {
                    directoryPanel.classList.add('is-tab-active');
                }
            }
            
            // Trata o estado selecionado do card (trigger)
            var cardGrid = this.closest('.interactive-tab-triggers');
            if (cardGrid) {
                var allCards = cardGrid.querySelectorAll('.card');
                allCards.forEach(function(c) {
                    c.classList.remove('is-selected-tab');
                });
                
                var currentCard = this.closest('.card') || this;
                currentCard.classList.add('is-selected-tab');
            }
            
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

    // Auto-open filters if the URL contains filtering queries
    if (window.location.search && window.location.search.length > 1) {
        var params = new URLSearchParams(window.location.search);
        var hasFilter = params.has('query') || params.has('student_status') || params.has('commercial_status') || params.has('payment_status') || params.has('keep_open');
        
        if (hasFilter) {
            var filtersTrigger = document.querySelector('[data-action="open-tab-students-filters"]');
            if (filtersTrigger) {
                filtersTrigger.dataset.noScroll = "true"; 
                filtersTrigger.click();
            }
        } else if (params.has('page')) {
            var directoryTrigger = document.querySelector('[data-action="open-tab-students-directory"]');
            if (directoryTrigger) {
                directoryTrigger.dataset.noScroll = "true"; 
                directoryTrigger.click();
            }
        }
    }
});
