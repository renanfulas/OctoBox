/**
 * ARQUIVO: finance-trend-board-controller.js
 *
 * POR QUE ELE EXISTE:
 * - transforma as pills do trend board em seletor local de metrica.
 *
 * O QUE ESTE ARQUIVO FAZ:
 * 1. alterna recebido e churn sem navegar;
 * 2. atualiza titulo, subtitulo e legenda do board;
 * 3. mantem Liquido e Gastos desabilitados enquanto a base nao existir.
 */

(function () {
  'use strict';

  document.addEventListener('DOMContentLoaded', function () {
    var board = document.querySelector('[data-finance-trend-board]');
    if (!board) {
      return;
    }

    var title = board.querySelector('[data-finance-trend-title]');
    var subtitle = board.querySelector('[data-finance-trend-subtitle]');
    var primaryLabel = board.querySelector('[data-finance-trend-legend-primary-label]');
    var secondaryLabel = board.querySelector('[data-finance-trend-legend-secondary-label]');
    var primaryDot = board.querySelector('[data-finance-trend-legend-primary-dot]');
    var secondaryDot = board.querySelector('[data-finance-trend-legend-secondary-dot]');
    var buttons = Array.from(board.querySelectorAll('[data-finance-trend-button]'));
    var views = Array.from(board.querySelectorAll('[data-finance-trend-view]'));

    if (!buttons.length || !views.length) {
      return;
    }

    function setDotState(dot, nextState) {
      if (!dot) {
        return;
      }

      Array.from(dot.classList).forEach(function (className) {
        if (className.indexOf('is-') === 0) {
          dot.classList.remove(className);
        }
      });
      dot.classList.add('is-' + nextState);
    }

    function applyMetric(metricKey, button) {
      board.dataset.financeTrendActive = metricKey;

      buttons.forEach(function (item) {
        var isActive = item === button;
        item.classList.toggle('is-active', isActive);
        item.setAttribute('aria-pressed', isActive ? 'true' : 'false');
      });

      views.forEach(function (view) {
        view.hidden = view.dataset.financeTrendView !== metricKey;
        view.classList.toggle('is-active', !view.hidden);
      });

      if (title) {
        title.textContent = button.dataset.trendTitle || title.textContent;
      }
      if (subtitle) {
        subtitle.textContent = button.dataset.trendSubtitle || subtitle.textContent;
      }
      if (primaryLabel) {
        primaryLabel.textContent = button.dataset.trendLegendPrimary || primaryLabel.textContent;
      }
      if (secondaryLabel) {
        secondaryLabel.textContent = button.dataset.trendLegendSecondary || secondaryLabel.textContent;
      }

      setDotState(primaryDot, button.dataset.trendLegendPrimaryState || 'realized');
      setDotState(secondaryDot, button.dataset.trendLegendSecondaryState || 'expected');
    }

    buttons.forEach(function (button) {
      button.addEventListener('click', function () {
        applyMetric(button.dataset.financeTrendButton, button);
      });
    });

    var initialButton = buttons.find(function (button) {
      return button.dataset.financeTrendButton === board.dataset.financeTrendActive;
    }) || buttons[0];

    applyMetric(initialButton.dataset.financeTrendButton, initialButton);
  });
})();
