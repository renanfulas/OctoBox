/*
 * ARQUIVO: plano alimentar sob demanda (Entrega 6, Fase 4 — docs/plans/
 * public-workouts-escala-e-nutricao-corda.md, D.4/D.6). Backend inteiro
 * (modelo, endpoint /renan/<slug>/nutricao.json, gate de tier) já existia
 * antes deste arquivo (PR #270) — isto é só o consumo em tela, sem IA nova.
 *
 * POR QUE ELE EXISTE:
 * - busca automatica ao abrir a aba Dieta (pedido do Renan: tirar o botao
 *   "Ver plano alimentar" — nao faz sentido pedir confirmacao pra ver a
 *   propria dieta). `[data-workout-nutrition]` so existe no DOM quando
 *   `nutrition_unlocked` e' true (ver workout.html), entao o fetch nunca
 *   dispara pra quem nao tem o tier — continua "sob demanda" no sentido
 *   de nunca rodar pra quem nao pode ver, so deixou de exigir um clique
 *   extra de quem pode.
 * - `meal_plan: null` é resposta 200 válida (tier qualifica mas ninguém
 *   publicou plano ainda) — mesmo espírito de `review_text: null`.
 * - Pedido do Renan (aba Dieta nova, ver workout.html/workout-shell.js):
 *   em vez de despejar as N refeições do dia inteiro de uma vez, o estado
 *   default depois do fetch é CONTEXTUAL por horário — mostra só "Agora"
 *   (a última refeição cujo horário já passou) e "Próxima refeição" (a
 *   primeira cujo horário ainda não chegou). Ver pickCurrentAndNext.
 *   Um botão "Ver dieta completa" continua disponível pra quem quiser
 *   rolar o cardápio inteiro (renderFullPlan, o comportamento antigo).
 *
 * PONTOS CRÍTICOS:
 * - Renderiza construindo nós DOM (textContent), nunca innerHTML com dado
 *   do payload — o payload é auto-autoral (nutricionista via admin), mas a
 *   mesma disciplina de nunca confiar em string-pra-HTML vale mesmo assim.
 * - GET simples, sem corpo — não precisa de CSRF (mesmo motivo de
 *   weekly_review.js/load_tracker.js).
 * - "Agora"/"Próxima" usa a HORA LOCAL DO DISPOSITIVO do aluno (new Date()),
 *   nunca hora do servidor — é o aluno decidindo o que comer AGORA.
 * - Refeições sem `time` (ex.: "pode consumir junto com a Refeição 1") não
 *   entram no cálculo Agora/Próxima — só aparecem na dieta completa, senão
 *   ficariam invisíveis pra sempre no modo contextual.
 * - Duas refeições com o MESMO horário (ex.: a opção panqueca às 17:00) são
 *   ALTERNATIVAS, não sequência — aparecem juntas no mesmo slot "Agora" ou
 *   "Próxima", nunca uma escondendo a outra.
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
    var card = el('article', 'workout-nutrition-meal-card');
    var head = el('div', 'workout-nutrition-meal-card__head');
    head.appendChild(el('strong', null, meal.label));
    if (meal.time) { head.appendChild(el('span', 'workout-nutrition-meal-card__time', meal.time)); }
    card.appendChild(head);

    var list = el('ul', 'workout-nutrition__items');
    (meal.items || []).forEach(function (item) {
      var li = el('li', null, item.food + ' — ' + item.quantity);
      list.appendChild(li);
    });
    card.appendChild(list);

    if (meal.substitutes && meal.substitutes.length) {
      var details = el('details', 'workout-nutrition__substitutes');
      details.appendChild(el('summary', null, 'Substituições (' + meal.substitutes.length + ')'));
      var subList = el('ul', 'workout-nutrition__items');
      meal.substitutes.forEach(function (sub) {
        subList.appendChild(el('li', null, sub.food + ' — ' + sub.quantity));
      });
      details.appendChild(subList);
      card.appendChild(details);
    }

    if (meal.note) {
      card.appendChild(el('p', 'workout-nutrition__note', meal.note));
    }

    return card;
  }

  /* ══ Agora / Próxima (hora local do aluno) ══════════════════════ */

  function parseMinutes(time) {
    if (!time || typeof time !== 'string') { return null; }
    var match = /^(\d{1,2}):(\d{2})$/.exec(time.trim());
    if (!match) { return null; }
    var hours = parseInt(match[1], 10);
    var mins = parseInt(match[2], 10);
    if (hours > 23 || mins > 59) { return null; }
    return hours * 60 + mins;
  }

  // Refeicoes sem horario ficam de fora dos grupos (ver docstring do topo).
  // Duas refeicoes no MESMO horario (alternativas) caem no mesmo grupo.
  function groupMealsByTime(meals) {
    var order = [];
    var byMinutes = {};
    (meals || []).forEach(function (meal) {
      var minutes = parseMinutes(meal.time);
      if (minutes === null) { return; }
      if (!byMinutes[minutes]) {
        byMinutes[minutes] = { minutes: minutes, meals: [] };
        order.push(byMinutes[minutes]);
      }
      byMinutes[minutes].meals.push(meal);
    });
    order.sort(function (a, b) { return a.minutes - b.minutes; });
    return order;
  }

  // "Agora" = ultimo grupo cujo horario ja chegou. "Proxima" = primeiro
  // grupo cujo horario ainda nao chegou. Antes da primeira refeicao do dia,
  // "Agora" fica null (nao existe refeicao "em andamento" ainda). Depois da
  // ultima, "Proxima" fica null (nao ha mais nada previsto hoje).
  function pickCurrentAndNext(groups, nowMinutes) {
    var current = null;
    var next = null;
    for (var i = 0; i < groups.length; i++) {
      if (groups[i].minutes <= nowMinutes) {
        current = groups[i];
      } else {
        next = groups[i];
        break;
      }
    }
    return { current: current, next: next };
  }

  function formatCountdown(targetMinutes, nowMinutes) {
    var delta = targetMinutes - nowMinutes;
    if (delta <= 0) { return ''; }
    var hours = Math.floor(delta / 60);
    var mins = delta % 60;
    if (hours === 0) { return 'em ' + mins + 'min'; }
    if (mins === 0) { return 'em ' + hours + 'h'; }
    return 'em ' + hours + 'h' + (mins < 10 ? '0' : '') + mins;
  }

  function renderSlot(labelText, group, nowMinutes, variantClass) {
    var section = el('div', 'workout-nutrition-slot ' + variantClass);
    var heading = el('div', 'workout-nutrition-slot__eyebrow');
    heading.appendChild(el('span', null, labelText));
    if (variantClass === 'is-next') {
      var countdown = formatCountdown(group.minutes, nowMinutes);
      if (countdown) { heading.appendChild(el('span', 'workout-nutrition-slot__countdown', countdown)); }
    }
    section.appendChild(heading);
    group.meals.forEach(function (meal) {
      section.appendChild(renderMeal(meal));
    });
    return section;
  }

  function appendFullPlanToggle(container, mealPlan) {
    var toggle = el('button', 'workout-nutrition__toggle', 'Ver dieta completa (' + (mealPlan.meals || []).length + ' refeições)');
    toggle.type = 'button';
    toggle.addEventListener('click', function () { renderFullPlan(container, mealPlan); });
    container.appendChild(toggle);
  }

  function renderContextualView(container, mealPlan, nowMinutes) {
    container.innerHTML = '';
    container.appendChild(renderMacros(mealPlan.daily_targets));

    var groups = groupMealsByTime(mealPlan.meals);
    var picked = pickCurrentAndNext(groups, nowMinutes);

    if (!picked.current && !picked.next) {
      // Nenhuma refeicao tem horario definido — contextual nao faz
      // sentido aqui, cai direto pra dieta completa.
      renderFullPlan(container, mealPlan);
      return;
    }

    if (picked.current) {
      container.appendChild(renderSlot('Agora', picked.current, nowMinutes, 'is-now'));
    } else {
      container.appendChild(el('p', 'workout-nutrition__empty', 'Sua primeira refeição do dia ainda não chegou.'));
    }

    if (picked.next) {
      container.appendChild(renderSlot('Próxima refeição', picked.next, nowMinutes, 'is-next'));
    } else if (picked.current) {
      container.appendChild(el('p', 'workout-nutrition__empty', 'Essa foi a última refeição prevista pra hoje.'));
    }

    appendFullPlanToggle(container, mealPlan);
  }

  function renderFullPlan(container, mealPlan) {
    container.innerHTML = '';
    container.appendChild(renderMacros(mealPlan.daily_targets));
    (mealPlan.meals || []).forEach(function (meal) {
      container.appendChild(renderMeal(meal));
    });
    var toggle = el('button', 'workout-nutrition__toggle', 'Ver só o horário de agora');
    toggle.type = 'button';
    toggle.addEventListener('click', function () {
      var now = new Date();
      renderContextualView(container, mealPlan, now.getHours() * 60 + now.getMinutes());
    });
    container.appendChild(toggle);
  }

  function renderMealPlan(container, mealPlan) {
    container.innerHTML = '';
    if (!mealPlan) {
      container.appendChild(el('p', 'workout-nutrition__empty', 'Seu plano alimentar ainda não foi publicado.'));
      container.hidden = false;
      return;
    }
    var now = new Date();
    renderContextualView(container, mealPlan, now.getHours() * 60 + now.getMinutes());
    container.hidden = false;
  }

  function initNutrition(root) {
    var url = root.getAttribute('data-nutrition-url');
    var contentEl = root.querySelector('[data-workout-nutrition-content]');
    var statusEl = root.querySelector('[data-workout-nutrition-status]');
    if (!url) { return; }

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
      });
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
