/*
 * ARQUIVO: plano alimentar sob demanda (Entrega 6, Fase 4 — docs/plans/
 * public-workouts-escala-e-nutricao-corda.md, D.4/D.6). Backend inteiro
 * (modelo, endpoint /renan/<slug>/nutricao.json, gate de tier) já existia
 * antes deste arquivo (PR #270) — isto é só o consumo em tela, sem IA nova.
 *
 * POR QUE ELE EXISTE:
 * - mesmo padrão de weekly_review.js: busca sob demanda (clique em "Ver
 *   plano alimentar"), nunca no carregamento da página.
 * - `meal_plan: null` é resposta 200 válida (tier qualifica mas ninguém
 *   publicou plano ainda) — mesmo espírito de `review_text: null`.
 *
 * PONTOS CRÍTICOS:
 * - Renderiza construindo nós DOM (textContent), nunca innerHTML com dado
 *   do payload — o payload é auto-autoral (nutricionista via admin), mas a
 *   mesma disciplina de nunca confiar em string-pra-HTML vale mesmo assim.
 * - GET simples, sem corpo — não precisa de CSRF (mesmo motivo de
 *   weekly_review.js/load_tracker.js).
 */

(function () {
  'use strict';

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) { node.className = className; }
    if (text !== undefined && text !== null) { node.textContent = text; }
    return node;
  }

  function renderMacros(macros) {
    var row = el('div', 'workout-nutrition__macros');
    if (!macros) { return row; }
    var labels = { kcal: 'kcal', protein_g: 'proteína (g)', carbs_g: 'carbo (g)', fat_g: 'gordura (g)' };
    Object.keys(labels).forEach(function (key) {
      if (typeof macros[key] !== 'number') { return; }
      var chip = el('span', 'workout-nutrition__macro-chip');
      chip.appendChild(el('strong', null, String(macros[key])));
      chip.appendChild(document.createTextNode(' ' + labels[key]));
      row.appendChild(chip);
    });
    return row;
  }

  function renderMeal(meal) {
    var card = el('div', 'workout-nutrition__meal');
    var heading = el('h3', null, meal.label + (meal.time ? ' — ' + meal.time : ''));
    card.appendChild(heading);

    var list = el('ul', 'workout-nutrition__items');
    (meal.items || []).forEach(function (item) {
      var li = el('li', null, item.food + ' — ' + item.quantity);
      list.appendChild(li);
    });
    card.appendChild(list);

    if (meal.substitutes && meal.substitutes.length) {
      var subLabel = el('p', 'workout-nutrition__substitutes-label', 'Substituições:');
      card.appendChild(subLabel);
      var subList = el('ul', 'workout-nutrition__items');
      meal.substitutes.forEach(function (sub) {
        subList.appendChild(el('li', null, sub.food + ' — ' + sub.quantity));
      });
      card.appendChild(subList);
    }

    if (meal.note) {
      card.appendChild(el('p', 'workout-nutrition__note', meal.note));
    }

    return card;
  }

  function renderMealPlan(container, mealPlan) {
    container.innerHTML = '';
    if (!mealPlan) {
      container.appendChild(el('p', null, 'Seu plano alimentar ainda não foi publicado.'));
      container.hidden = false;
      return;
    }
    container.appendChild(renderMacros(mealPlan.daily_targets));
    (mealPlan.meals || []).forEach(function (meal) {
      container.appendChild(renderMeal(meal));
    });
    container.hidden = false;
  }

  function initNutrition(root) {
    var url = root.getAttribute('data-nutrition-url');
    var contentEl = root.querySelector('[data-workout-nutrition-content]');
    var statusEl = root.querySelector('[data-workout-nutrition-status]');
    var button = root.querySelector('[data-workout-nutrition-generate]');
    if (!url || !button) { return; }

    button.addEventListener('click', function () {
      button.disabled = true;
      if (statusEl) { statusEl.textContent = 'Carregando…'; }

      window.fetch(url, { credentials: 'same-origin' })
        .then(function (response) {
          if (!response.ok) { throw new Error('http-' + response.status); }
          return response.json();
        })
        .then(function (data) {
          if (statusEl) { statusEl.textContent = ''; }
          if (contentEl) { renderMealPlan(contentEl, data && data.meal_plan); }
        })
        .catch(function () {
          if (statusEl) { statusEl.textContent = 'Não foi possível carregar o plano agora.'; }
        })
        .finally(function () {
          button.disabled = false;
        });
    });

    if (window.location.hash === '#nutricao') {
      window.setTimeout(function () { button.click(); }, 0);
    }
  }

  function init() {
    document.querySelectorAll('[data-workout-nutrition]').forEach(initNutrition);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
