/* Troca de aba em DOIS niveis independentes (paineis de nivel superior +
   sub-abas de dia dentro de Treino) sem um nivel derrubar o outro:
   - "quem fica destacado" e' escopado ao NAV mais proximo
     ([data-workout-tab-nav]) — clicar um dia da semana nao apaga o
     destaque de "Treino" no bottom nav, e vice-versa.
   - "qual painel aparece" e' escopado ao CONTAINER do painel-alvo (so os
     irmaos [data-workout-tab-panel] daquele MESMO nivel), reusando o
     mesmo mecanismo de interactive-tabs.css (>*:not(.is-tab-active){display:none}),
     que ja e por filho direto — dois .interactive-tab-container aninhados
     nao brigam entre si. */
(function () {
  // Escopo de "quem fica destacado" cobre TANTO os botoes de alvo fixo
  // ([data-workout-tab-target]) QUANTO o botao de ciclo do Treino
  // ([data-workout-cycle-nav], ver mais abaixo) -- os dois vivem no MESMO
  // nav ([data-workout-tab-nav]), clicar um precisa apagar o destaque do
  // outro.
  function clearNavActive(navGroup) {
    navGroup.querySelectorAll('[data-workout-tab-target], [data-workout-cycle-nav]').forEach(function (t) {
      t.classList.remove('is-active');
      t.setAttribute('aria-selected', 'false');
    });
  }

  function showPanel(targetId) {
    var targetPanel = document.getElementById(targetId);
    if (!targetPanel || !targetPanel.parentElement) return;
    Array.prototype.forEach.call(targetPanel.parentElement.children, function (panel) {
      if (panel.hasAttribute && panel.hasAttribute('data-workout-tab-panel')) {
        panel.classList.toggle('is-tab-active', panel.id === targetId);
      }
    });
  }

  var tabs = document.querySelectorAll('[data-workout-tab-target]');
  tabs.forEach(function (tab) {
    tab.addEventListener('click', function () {
      var targetId = tab.getAttribute('data-workout-tab-target');
      var navGroup = tab.closest('[data-workout-tab-nav]') || document;
      clearNavActive(navGroup);
      tab.classList.add('is-active');
      tab.setAttribute('aria-selected', 'true');
      showPanel(targetId);
    });
  });

  // Botao de ciclo "Treino" do bottom nav (item pedido pelo Renan): um SO'
  // slot da nav alterna Treino -> Cardio -> Periodizacao -> Treino a cada
  // toque, em vez de 3 botoes fixos (nav so' tem espaco pros 5 de sempre).
  // Cardio/Periodizacao saem da lista de alvos quando o programa nao tem
  // esse dado (data-cycle-targets vem filtrado pelo template, ver acima).
  // Chegar de OUTRO botao sempre reseta pro primeiro estado (Treino) --
  // so' avanca no ciclo quando o proprio botao JA esta ativo.
  var cycleNav = document.querySelector('[data-workout-cycle-nav]');
  var resetCycleToTreino = function () {}; // no-op se nao houver cycleNav (nunca deveria faltar)
  if (cycleNav) {
    var CYCLE_ICONS = {
      treino: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M3 10h3"/><path d="M18 10h3"/><path d="M6 7v6"/><path d="M18 7v6"/><path d="M8.5 12h7"/><path d="M8.5 10h7"/><path d="M8.5 14h7"/></svg>',
      cardio: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><circle cx="14.5" cy="4.5" r="1.7"/><path d="M10 9.5 12.5 8l2 3 3.5 1.5"/><path d="M12.5 8 9 10l-1.5 4"/><path d="M14.5 11 17 12.5l1 4.5"/><path d="M9 17.5l3-3"/></svg>',
      periodizacao: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M4 20v-7"/><path d="M9.5 20V8"/><path d="M15 20v-9"/><path d="M20 20V5"/></svg>',
    };
    var CYCLE_LABELS = { treino: 'Treino', cardio: 'Cardio', periodizacao: 'Periodização' };
    var cycleTargets = cycleNav.getAttribute('data-cycle-targets').split('|');
    var cycleIndex = 0;

    function cycleKeyOf(targetId) {
      return targetId.replace('workout-panel-', '');
    }

    function showCycleState(index) {
      cycleIndex = index;
      var targetId = cycleTargets[cycleIndex];
      var key = cycleKeyOf(targetId);
      cycleNav.querySelector('[data-cycle-icon]').innerHTML = CYCLE_ICONS[key];
      cycleNav.querySelector('[data-cycle-label]').textContent = CYCLE_LABELS[key];

      var navGroup = cycleNav.closest('[data-workout-tab-nav]') || document;
      clearNavActive(navGroup);
      cycleNav.classList.add('is-active');
      cycleNav.setAttribute('aria-selected', 'true');
      showPanel(targetId);
    }

    cycleNav.addEventListener('click', function () {
      var isActive = cycleNav.classList.contains('is-active');
      showCycleState(isActive ? (cycleIndex + 1) % cycleTargets.length : 0);
    });

    // Treino e' sempre cycleTargets[0] (garantido pelo template) -- usado
    // pelo atalho de "dia da semana" do Início abaixo, que precisa
    // ATERRISSAR em Treino especificamente, nunca so' "avancar o ciclo"
    // (diferente de um clique de verdade no botao).
    resetCycleToTreino = function () {
      showCycleState(0);
    };
  }

  // Atalhos que pulam telas (ex.: dia da semana em Início -> Treino + o
  // sub-dia certo). Deliberadamente FORA do NodeList `tabs` acima: um
  // atalho nao tem estado proprio de "aba ativa" (nao aparece nem no
  // bottom nav nem nos sub-tabs de dia) — so aciona os botoes REAIS via
  // .click(), reusando a logica de cima sem duplicar nem interferir na
  // marcacao is-active deles.
  document.querySelectorAll('[data-workout-jump-panel]').forEach(function (jumpButton) {
    jumpButton.addEventListener('click', function () {
      var panelTarget = jumpButton.getAttribute('data-workout-jump-panel');
      var dayTarget = jumpButton.getAttribute('data-workout-jump-day');
      if (panelTarget === 'workout-panel-treino') {
        // Treino nao tem mais [data-workout-tab-target] fixo (virou o
        // botao de ciclo acima) -- reseta pro primeiro estado do ciclo em
        // vez de simular clique (que AVANÇARIA o ciclo se ja estivesse em
        // Cardio/Periodizacao).
        resetCycleToTreino();
      } else {
        var navButton = document.querySelector('.workout-mobile-nav [data-workout-tab-target="' + panelTarget + '"]');
        if (navButton) navButton.click();
      }
      if (dayTarget) {
        var dayButton = document.getElementById(dayTarget);
        if (dayButton) dayButton.click();
      }
    });
  });

  // A ação de registro é um botão nativo dentro do artigo (sem controles
  // interativos aninhados em um elemento com role=button). O painel é
  // localizado pelo aria-controls, sem depender de nextElementSibling.
  document.querySelectorAll('[data-workout-load-toggle]').forEach(function (trigger) {
    trigger.addEventListener('click', function () {
      var widgetId = trigger.getAttribute('aria-controls');
      var widget = widgetId ? document.getElementById(widgetId) : null;
      if (!widget || !widget.hasAttribute('data-workout-load-input')) return;
      widget.hidden = !widget.hidden;
      var expanded = !widget.hidden;
      trigger.setAttribute('aria-expanded', expanded ? 'true' : 'false');
      var label = trigger.querySelector('[data-workout-load-action-label]');
      var icon = trigger.querySelector('[data-workout-load-action-icon]');
      if (label) label.textContent = expanded ? 'Fechar registro' : 'Registrar carga';
      if (icon) icon.textContent = expanded ? '−' : '＋';
      if (!widget.hidden) {
        var weightField = widget.querySelector('[data-workout-load-field]');
        if (weightField) weightField.focus();
      }
    });
  });

  // "Ver variação": botão independente, sem disputar a ação de registro.
  // Pedido do Renan: disponivel em TODO exercicio que tiver variacao
  // sugerida pelo treinador (`.ex-var` do HTML legado), nao so' os
  // rastreados — mesmo espirito do item de carga.
  document.querySelectorAll('[data-workout-variation-toggle]').forEach(function (trigger) {
    function toggle() {
      var panelId = trigger.getAttribute('aria-controls');
      var panel = panelId ? document.getElementById(panelId) : null;
      if (!panel || !panel.hasAttribute('data-workout-variation')) return;
      panel.hidden = !panel.hidden;
      trigger.setAttribute('aria-expanded', panel.hidden ? 'false' : 'true');
    }
    trigger.addEventListener('click', toggle);
  });

  // Bolinha de jargao de treino (RIR, AMRAP, Feeder, Top, Prep — ver
  // glossary_highlight em public_workouts_extras.py): clique alterna a
  // definicao, so uma aberta por vez, clique fora fecha. Delegado no
  // document (nao querySelectorAll na carga da pagina) porque os termos
  // vivem dentro de texto renderizado por movimento, que pode repetir
  // varias vezes por dia/bloco.
  //
  // .workout-glossary-tip e' position:fixed (CSS) — cardo/student-card tem
  // overflow:hidden pro decor-topstripe, um position:absolute cortaria o
  // tooltip. Por isso a posicao e' calculada aqui via getBoundingClientRect
  // do TERMO (nao do tooltip, que comeca com display:none e mediria 0x0) e
  // aplicada como inline style antes de abrir.
  function positionGlossaryTip(term) {
    var tip = term.querySelector('.workout-glossary-tip');
    if (!tip) return;
    var termRect = term.getBoundingClientRect();
    var margin = 8;
    var maxWidth = 240;
    var left = Math.min(termRect.left, window.innerWidth - maxWidth - margin);
    left = Math.max(margin, left);
    var top = termRect.bottom + margin;
    // Sem altura real ainda medida (tip escondido) -- usa uma altura
    // estimada generosa pra decidir se cabe embaixo antes de abrir acima.
    var estimatedHeight = 90;
    if (top + estimatedHeight > window.innerHeight - margin) {
      top = termRect.top - estimatedHeight - margin;
    }
    tip.style.left = left + 'px';
    tip.style.top = Math.max(margin, top) + 'px';
  }

  function closeGlossaryTerm(term) {
    term.classList.remove('is-open');
    term.setAttribute('aria-expanded', 'false');
  }

  function toggleGlossaryTerm(term) {
    document.querySelectorAll('[data-workout-glossary].is-open').forEach(function (open) {
      if (open !== term) closeGlossaryTerm(open);
    });
    var willOpen = !term.classList.contains('is-open');
    if (willOpen) positionGlossaryTip(term);
    term.classList.toggle('is-open', willOpen);
    term.setAttribute('aria-expanded', willOpen ? 'true' : 'false');
  }

  document.addEventListener('click', function (event) {
    var term = event.target.closest('[data-workout-glossary]');
    if (!term) {
      document.querySelectorAll('[data-workout-glossary].is-open').forEach(closeGlossaryTerm);
      return;
    }
    event.stopPropagation();
    toggleGlossaryTerm(term);
  });
  document.addEventListener('keydown', function (event) {
    if (event.key !== 'Enter' && event.key !== ' ') return;
    var term = event.target.closest('[data-workout-glossary]');
    if (!term) return;
    event.preventDefault();
    toggleGlossaryTerm(term);
  });
  window.addEventListener('scroll', function () {
    document.querySelectorAll('[data-workout-glossary].is-open').forEach(closeGlossaryTerm);
  }, true);

  // "Sair da conta" (Perfil) -- mesmo padrao de getCookie de
  // load_tracker.js/assessments.js, nao importado direto (abas
  // independentes, ver comentario la).
  function getCookie(name) {
    var parts = (document.cookie || '').split(';');
    for (var i = 0; i < parts.length; i++) {
      var part = parts[i].trim();
      if (part.indexOf(name + '=') === 0) return decodeURIComponent(part.slice(name.length + 1));
    }
    return '';
  }
  var signOutButton = document.querySelector('[data-workout-signout]');
  if (signOutButton) {
    signOutButton.addEventListener('click', function () {
      if (!window.confirm('Sair da conta?')) return;
      window.fetch(signOutButton.getAttribute('data-signout-url'), {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'X-CSRFToken': getCookie('csrftoken') },
      }).then(function () {
        window.location.href = '/renan/offline/';
      });
    });
  }
})();
