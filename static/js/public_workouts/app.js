/*
 * ARQUIVO: comportamento das paginas publicas de treino (/renan/).
 *
 * POR QUE ELE EXISTE:
 * - as mesmas 11 funcoes estavam reimplementadas dentro de cada um dos 7
 *   arquivos HTML. As copias divergiram e viraram bug: o renderBar da
 *   milene apontava para um id que nao existe (barra morta), o bruno
 *   pintava as barras de azul embaixo de um accent laranja, e a giovanna
 *   simplesmente nao tinha tracker nenhum.
 *
 * PONTOS CRITICOS:
 * - o namespace do localStorage vem de data-store-key no <body> e e
 *   CONGELADO por aluno. Trocar apaga o historico de carga sem aviso.
 * - as funcoes usadas por onclick= no markup precisam continuar no
 *   escopo global; a exposicao explicita esta no fim do arquivo.
 */

(function () {
  'use strict';

  var body = document.body;
  var STORE_KEY = body.getAttribute('data-store-key');

  function cssVar(name, fallback) {
    var v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    return v || fallback;
  }

  function trackerWeeks() {
    return parseInt(cssVar('--tracker-weeks', '5'), 10) || 5;
  }

  /* ══ NAVEGACAO ══════════════════════════════════════════════ */

  function goDay(id, el) {
    document.querySelectorAll('.session').forEach(function (s) { s.classList.remove('on'); });
    document.querySelectorAll('.dp:not(.rest)').forEach(function (p) {
      p.classList.remove('active');
      p.removeAttribute('aria-current');
    });
    var session = document.getElementById(id);
    if (session) { session.classList.add('on'); }
    if (el) {
      el.classList.add('active');
      el.setAttribute('aria-current', 'true');
    }
    showTab('treino');
    document.querySelectorAll('.tab').forEach(function (t, i) {
      t.classList.toggle('on', i === 0);
    });
  }

  // Antes cada arquivo listava na mao exatamente as abas que possuia
  // (o bruno tinha 'nutri' a mais, a thaislima nao tinha 'period'), o que
  // tornava a funcao impossivel de compartilhar. Agora ela descobre.
  function showTab(name) {
    document.querySelectorAll('[id^="tab-"]').forEach(function (panel) {
      panel.style.display = panel.id === 'tab-' + name ? 'block' : 'none';
    });
  }

  function goTab(name, el) {
    showTab(name);
    document.querySelectorAll('.tab').forEach(function (b) { b.classList.remove('on'); });
    if (el) { el.classList.add('on'); }
    if (name === 'period') { buildChart(); }
  }

  /* ══ MODO ACADEMIA ══════════════════════════════════════════ */

  var MODE_KEY = 'public-workout-simplified';

  function paintModeButton(btn, simplified) {
    if (!btn) { return; }
    var label = btn.querySelector('.mode-label');
    var icon = btn.querySelector('.mode-icon');
    if (label) { label.textContent = simplified ? 'Modo Completo' : 'Modo Academia'; }
    if (icon) { icon.textContent = simplified ? '📖' : '🏋️'; }
    btn.classList.toggle('is-simplified', simplified);
    btn.setAttribute('aria-pressed', simplified ? 'true' : 'false');
  }

  // Antes o modo resetava a cada carregamento — o aluno reativava a cada
  // exercicio. E o botao recebia um verde escrito na mao no style inline;
  // agora e a classe .is-simplified, que vive no CSS.
  function toggleMode(btn) {
    var simplified = body.classList.toggle('simplified');
    try { localStorage.setItem(MODE_KEY, simplified ? '1' : '0'); } catch (e) { /* modo anonimo */ }
    paintModeButton(btn || document.querySelector('.mode-btn'), simplified);
  }

  function restoreMode() {
    var saved = null;
    try { saved = localStorage.getItem(MODE_KEY); } catch (e) { /* modo anonimo */ }
    if (saved === '1') {
      body.classList.add('simplified');
      paintModeButton(document.querySelector('.mode-btn'), true);
    }
  }

  /* ══ GRAFICO DE PERIODIZACAO ════════════════════════════════ */

  // Os dados sao conteudo de treino (rotulos, foco, reps, altura) e vivem
  // no template do aluno, num <script type="application/json">.
  function chartData() {
    var node = document.getElementById('period-chart-data');
    if (!node) { return []; }
    try { return JSON.parse(node.textContent) || []; } catch (e) { return []; }
  }

  function buildChart() {
    var host = document.getElementById('period-chart-body');
    if (!host || host.children.length > 0) { return; }
    var weeks = chartData();
    var maxH = 100;
    var chartH = 120;
    weeks.forEach(function (w) {
      var barH = Math.round((w.h / maxH) * chartH);
      var col = document.createElement('div');
      col.className = 'chart-col';
      col.innerHTML =
        '<div class="chart-bar-wrap" style="height:' + chartH + 'px">' +
          '<div class="chart-reps" style="color:' + w.fg + '">' + w.reps + '</div>' +
          '<div class="chart-bar" style="height:' + barH + 'px;background:' + w.color + '">' +
            '<div class="chart-bar-sheen"></div>' +
          '</div>' +
        '</div>' +
        '<div class="chart-focus" style="background:' + w.bg + ';color:' + w.fg + '">' + w.focus + '</div>' +
        '<div class="chart-label">' + w.label + '</div>';
      host.appendChild(col);
    });
  }

  /* ══ REGISTRO DE CARGA ══════════════════════════════════════ */

  function loadAll() {
    if (!STORE_KEY) { return {}; }
    try { return JSON.parse(localStorage.getItem(STORE_KEY) || '{}'); } catch (e) { return {}; }
  }

  function saveAll(data) {
    if (!STORE_KEY) { return; }
    try { localStorage.setItem(STORE_KEY, JSON.stringify(data)); } catch (e) { /* cota/anonimo */ }
  }

  // Tira o sufixo -s<N> da chave. A milene usa prefixo de 3 segmentos
  // ('mil-seg-A1') e os outros de 2 ('seg-A1'); o codigo antigo cortava
  // por contagem fixa de segmentos, entao na milene o prefixo saia
  // errado, o getElementById dava null e a barra nunca desenhava.
  function prefixOf(key) {
    return key.replace(/-s\d+$/, '');
  }

  function getVals(prefix) {
    var out = [];
    for (var i = 1; i <= trackerWeeks(); i++) {
      var el = document.querySelector('[data-key="' + prefix + '-s' + i + '"]');
      out.push(el && el.value ? parseFloat(el.value) : null);
    }
    return out;
  }

  function renderBar(prefix) {
    var prog = document.getElementById('prog-' + prefix);
    if (!prog) { return; }
    var vals = getVals(prefix);
    var filled = vals.filter(function (v) { return v !== null; });
    if (!filled.length) { prog.innerHTML = ''; return; }

    var maxV = Math.max.apply(null, filled);
    var minV = Math.min.apply(null, filled);
    var range = (maxV - minV) || 1;
    var MAXH = 36;

    prog.innerHTML = vals.map(function (v, i) {
      if (v === null) {
        return '<div class="tp-empty">S' + (i + 1) + '</div>';
      }
      var h = Math.max(6, Math.round(((v - minV) / range) * (MAXH - 6) + 6));
      var isMax = v === maxV && filled.length > 1;
      // Classe em vez de hex inline: o bruno tinha barra azul embaixo de
      // um accent laranja porque o hex veio junto no copiar e colar.
      return '<div class="tp-col' + (isMax ? ' tp-col--max' : '') + '">' +
        '<div class="tp-val">' + v + 'kg</div>' +
        '<div class="tp-bar" style="height:' + h + 'px"></div>' +
        '<div class="tp-lbl">S' + (i + 1) + '</div>' +
      '</div>';
    }).join('');
  }

  function saveTracker(prefix) {
    var data = loadAll();
    for (var i = 1; i <= trackerWeeks(); i++) {
      var el = document.querySelector('[data-key="' + prefix + '-s' + i + '"]');
      var key = prefix + '-s' + i;
      if (el && el.value) { data[key] = parseFloat(el.value); } else { delete data[key]; }
    }
    saveAll(data);
    renderBar(prefix);
    suggestLoads(prefix);
    var msg = document.getElementById('msg-' + prefix);
    if (msg) {
      msg.style.opacity = '1';
      setTimeout(function () { msg.style.opacity = '0'; }, 2000);
    }
  }

  function initTrackers() {
    var data = loadAll();
    var prefixes = {};
    document.querySelectorAll('.wk-input').forEach(function (input) {
      var key = input.getAttribute('data-key');
      if (!key) { return; }
      if (data[key] !== undefined) { input.value = data[key]; }
      prefixes[prefixOf(key)] = true;
      input.addEventListener('input', function () { renderBar(prefixOf(key)); });
    });
    // Antes cada arquivo repetia a lista de prefixos na mao; agora sai do
    // proprio DOM e nao tem como esquecer um.
    Object.keys(prefixes).forEach(function (prefix) {
      renderBar(prefix);
      suggestLoads(prefix);
    });
  }

  /* ══ CICLO E SUGESTAO DE CARGA ══════════════════════════════ */

  // Nasceu no treino do john e era o unico arquivo com nocao de tempo.
  // Agora qualquer plano habilita so declarando data-cycle-start.
  function cycleConfig() {
    var banner = document.querySelector('[data-cycle-start]');
    if (!banner) { return null; }
    var start = new Date(banner.getAttribute('data-cycle-start') + 'T00:00:00');
    if (isNaN(start.getTime())) { return null; }
    return {
      node: banner,
      start: start,
      weeks: parseInt(banner.getAttribute('data-cycle-weeks'), 10) || trackerWeeks(),
      increment: parseFloat(banner.getAttribute('data-cycle-increment')) || 0
    };
  }

  function currentCycleWeek(cfg) {
    var days = Math.floor((new Date() - cfg.start) / 86400000);
    if (days < 0) { return 1; }
    return (Math.floor(days / 7) % cfg.weeks) + 1;
  }

  function renderBanner() {
    var cfg = cycleConfig();
    if (!cfg) { return; }
    var week = currentCycleWeek(cfg);
    var num = document.getElementById('pb-num');
    var title = document.getElementById('pb-title');
    var sub = document.getElementById('pb-sub');
    var dots = document.getElementById('pb-dots');

    if (num) { num.textContent = week; }
    if (title) { title.textContent = 'Semana ' + week + ' de ' + cfg.weeks + ' — Progressão de carga'; }
    if (sub) {
      sub.textContent = week === 1
        ? 'Registre suas cargas esta semana. As próximas vão sugerir a progressão automaticamente.'
        : 'Meta: +' + fmtKg(cfg.increment * (week - 1)) + ' kg sobre a semana 1 nos exercícios principais. Mesmas reps, mais carga.';
    }
    if (dots) {
      var html = '';
      for (var w = 1; w <= cfg.weeks; w++) {
        html += '<div class="pb-dot ' + (w < week ? 'done' : (w === week ? 'now' : '')) + '"></div>';
      }
      dots.innerHTML = html;
    }
    // Destaca a semana corrente nas caixinhas do tracker.
    document.querySelectorAll('.wk-box').forEach(function (box) {
      var input = box.querySelector('.wk-input');
      var key = input && input.getAttribute('data-key');
      box.classList.toggle('wk-current', !!key && key.slice(-2) === 's' + week);
    });
  }

  function fmtKg(value) {
    return String(Math.round(value * 10) / 10).replace(/\.0$/, '');
  }

  function suggestLoads(prefix) {
    var cfg = cycleConfig();
    if (!cfg || !cfg.increment) { return; }
    var baseEl = document.querySelector('[data-key="' + prefix + '-s1"]');
    var base = baseEl && baseEl.value ? parseFloat(baseEl.value) : null;
    for (var i = 2; i <= trackerWeeks(); i++) {
      var el = document.querySelector('[data-key="' + prefix + '-s' + i + '"]');
      if (!el || el.value) { continue; }
      el.placeholder = base ? fmtKg(base + cfg.increment * (i - 1)) + ' →' : 'kg';
    }
  }

  /* ══ BOOT ═══════════════════════════════════════════════════ */

  function init() {
    restoreMode();
    initTrackers();
    renderBanner();
    // Se a pagina abre ja na aba de periodizacao, o grafico precisa existir.
    var active = document.querySelector('.tab.on');
    if (active && /period/.test(active.getAttribute('onclick') || '')) { buildChart(); }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Usadas por onclick= no markup dos planos.
  window.goDay = goDay;
  window.goTab = goTab;
  window.showTab = showTab;
  window.toggleMode = toggleMode;
  window.saveTracker = saveTracker;
  window.buildChart = buildChart;
})();
