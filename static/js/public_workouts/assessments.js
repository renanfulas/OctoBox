/*
 * ARQUIVO: aba "Avaliacoes" do corredor publico de treinos (/renan/<slug>).
 *
 * POR QUE ELE EXISTE:
 * - mostra evolucao fisica (peso/medidas/BF%/RCQ/IMC) num relatorio estilo
 *   bioimpedancia, alimentado por GET /renan/<slug>/avaliacoes.json
 *   (public_workouts app, SHARED_APP — ver student_app/views/public_workout_assessment_views.py).
 *
 * PONTOS CRITICOS:
 * - o painel #tab-avaliacoes e criado 100% por este arquivo (nenhum template
 *   tem o markup estatico) e injetado logo apos `.tabs` — o showTab()
 *   generico de app.js (ou o das paginas legadas, ja generalizado) descobre
 *   `[id^="tab-"]` sozinho, entao nao precisa de nenhuma mudanca la.
 * - sem escrita publica de proposito: quem registra avaliacao e o
 *   treinador, via management command (ver public_workouts/management/).
 *   Esta pagina so LE.
 */

(function () {
  'use strict';

  var MEASUREMENT_LABELS = {
    pescoco: 'Pescoço',
    ombro: 'Ombro',
    peito: 'Peito',
    cintura: 'Cintura',
    abdomen: 'Abdômen',
    quadril: 'Quadril',
    braco: 'Braço',
    coxa: 'Coxa',
    panturrilha: 'Panturrilha',
  };

  /* ══ SILHUETA ══════════════════════════════════════════════
   * Corpo desenhado no viewBox 440x380, centrado em x=220. O corpo ocupa
   * so a faixa 150-290; as laterais sao reservadas para os rotulos, que
   * ANTES estouravam o viewBox (o "Abdomen" saia cortado na direita).
   */
  var BODY_VIEW_W = 440;
  var BODY_VIEW_H = 356;   // corpo vai ate y=341; o resto e so respiro

  var BODY_TORSO_PATH =
    'M 207 60 C 207 70 206 76 204 80 C 192 83 182 90 176 101 ' +
    'C 180 124 188 148 194 172 C 187 182 184 191 185 204 ' +
    'C 183 228 185 252 188 274 C 189 294 188 312 189 332 ' +
    'C 189 338 194 341 200 341 C 206 341 210 338 210 332 ' +
    'C 211 310 213 288 214 266 C 215 248 217 232 220 218 ' +
    'C 223 232 225 248 226 266 C 227 288 229 310 230 332 ' +
    'C 230 338 234 341 240 341 C 246 341 251 338 251 332 ' +
    'C 252 312 251 294 252 274 C 255 252 257 228 255 204 ' +
    'C 256 191 253 182 246 172 C 252 148 260 124 264 101 ' +
    'C 258 90 248 83 236 80 C 234 76 233 70 233 60 Z';

  var BODY_ARM_LEFT_PATH =
    'M 176 101 C 168 112 162 128 158 146 C 155 164 152 182 150 198 ' +
    'C 149 206 152 211 158 211 C 164 211 167 207 168 200 ' +
    'C 170 182 174 162 178 144 C 181 128 183 113 184 104 Z';

  // Espelho exato do braco esquerdo em torno de x=220 (x' = 440 - x).
  var BODY_ARM_RIGHT_PATH =
    'M 264 101 C 272 112 278 128 282 146 C 285 164 288 182 290 198 ' +
    'C 291 206 288 211 282 211 C 276 211 273 207 272 200 ' +
    'C 270 182 266 162 262 144 C 259 128 257 113 256 104 Z';

  // Ponto do corpo onde a linha-guia nasce. `x` e a borda DIREITA do corpo
  // naquela altura; o lado esquerdo e o espelho (BODY_VIEW_W - x), porque o
  // corpo e simetrico. Isso deixa cada medida ir pra qualquer coluna sem a
  // linha-guia atravessar a silhueta — o que permite balancear as colunas
  // conforme as medidas que o aluno realmente tem.
  var SILHOUETTE_ANCHORS = {
    pescoco: { x: 233, y: 70 },
    ombro: { x: 263, y: 100 },
    peito: { x: 260, y: 125 },
    braco: { x: 283, y: 155 },
    cintura: { x: 246, y: 172 },
    abdomen: { x: 249, y: 190 },
    quadril: { x: 255, y: 206 },
    coxa: { x: 254, y: 250 },
    panturrilha: { x: 252, y: 300 },
  };

  var LABEL_X_LEFT = 116;
  var LABEL_X_RIGHT = 324;
  var LABEL_MIN_GAP = 38;   // altura de um bloco titulo+valor, com folga
  var LABEL_MIN_Y = 40;
  var LABEL_MAX_Y = 336;

  // Dominio aproximado so pra POSICIONAR o marcador no gauge visual — a
  // classificacao (cor/rotulo) que manda e sempre a que vem do backend.
  var GAUGE_DOMAINS = {
    bmi: [15, 40],
    whr: [0.6, 1.15],
    body_fat_percent: [3, 35],
  };

  function planSlug() {
    return document.body.getAttribute('data-plan-slug');
  }

  function escapeHtml(value) {
    return String(value).replace(/[&<>"']/g, function (ch) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch];
    });
  }

  function fmtNum(value) {
    if (value === null || value === undefined) return '';
    var rounded = Math.round(value * 10) / 10;
    return String(rounded).replace('.', ',');
  }

  function fmtDate(iso) {
    var parts = iso.split('-');
    return parts[2] + '/' + parts[1] + '/' + parts[0];
  }

  function badgeHtml(classification) {
    if (!classification) return '';
    return '<span class="assess-badge assess-badge--' + classification.level + '">' + escapeHtml(classification.label) + '</span>';
  }

  function bodyFatSourceSuffix(source) {
    switch (source) {
      case 'navy_estimate':
        return ' (estimado)';
      case 'skinfold_jp7':
        return ' (dobras cutâneas — 7 pontos)';
      case 'skinfold_jp3':
        return ' (dobras cutâneas — 3 pontos)';
      case 'device':
        return ' (bioimpedância)';
      default:
        return '';
    }
  }

  function gaugeHtml(kind, value) {
    var domain = GAUGE_DOMAINS[kind];
    if (!domain) return '';
    var pct = ((value - domain[0]) / (domain[1] - domain[0])) * 100;
    pct = Math.max(2, Math.min(98, pct));
    return '<div class="assess-gauge"><div class="assess-gauge-marker" style="left:' + pct + '%"></div></div>';
  }

  function buildSummaryCards(indicators) {
    if (!indicators) return '';
    var cards = [];
    if (indicators.bmi) {
      cards.push(
        '<div class="assess-card">' +
          '<div class="assess-card-label">IMC</div>' +
          '<div class="assess-card-value">' + fmtNum(indicators.bmi.value) + '</div>' +
          badgeHtml(indicators.bmi.classification) +
          gaugeHtml('bmi', indicators.bmi.value) +
          '</div>'
      );
    }
    if (indicators.whr) {
      cards.push(
        '<div class="assess-card">' +
          '<div class="assess-card-label">RCQ (Cintura/Quadril)</div>' +
          '<div class="assess-card-value">' + String(indicators.whr.value).replace('.', ',') + '</div>' +
          badgeHtml(indicators.whr.classification) +
          gaugeHtml('whr', indicators.whr.value) +
          '</div>'
      );
    }
    if (indicators.body_fat_percent) {
      var bf = indicators.body_fat_percent;
      cards.push(
        '<div class="assess-card">' +
          '<div class="assess-card-label">% Gordura' + bodyFatSourceSuffix(bf.source) + '</div>' +
          '<div class="assess-card-value">' + fmtNum(bf.value) + '%</div>' +
          badgeHtml(bf.classification) +
          gaugeHtml('body_fat_percent', bf.value) +
          '</div>'
      );
    }
    if (!cards.length) return '';
    return '<div class="assess-summary">' + cards.join('') + '</div>';
  }

  // Empilha os rotulos de uma coluna sem sobreposicao: cada um comeca na
  // altura do proprio ponto no corpo e so desce o minimo necessario pra
  // nao encostar no de cima. Sem isso, medidas vizinhas (cintura/abdomen/
  // quadril ficam a ~18px uma da outra no corpo) imprimem uma sobre a outra.
  function stackLabels(entries) {
    entries.sort(function (a, b) { return a.anchorY - b.anchorY; });
    var previous = -Infinity;
    entries.forEach(function (entry) {
      entry.labelY = Math.max(entry.anchorY, previous + LABEL_MIN_GAP, LABEL_MIN_Y);
      previous = entry.labelY;
    });
    var last = entries[entries.length - 1];
    if (last && last.labelY > LABEL_MAX_Y) {
      var shift = last.labelY - LABEL_MAX_Y;
      entries.forEach(function (entry) {
        entry.labelY = Math.max(LABEL_MIN_Y, entry.labelY - shift);
      });
    }
    return entries;
  }

  // Linha-guia em cotovelo: sai reta do corpo, faz a diagonal e chega
  // horizontal no rotulo — le melhor que uma reta unica na diagonal.
  function connectorPath(anchorX, anchorY, labelX, labelY, direction) {
    var stub = anchorX + direction * 16;
    var approach = labelX - direction * 8;
    return 'M ' + anchorX + ' ' + anchorY + ' L ' + stub + ' ' + anchorY +
      ' L ' + approach + ' ' + labelY + ' L ' + labelX + ' ' + labelY;
  }

  function deltaTspan(delta) {
    if (delta === null || delta === undefined || delta === 0) return '';
    var direction = delta > 0 ? 'up' : 'down';
    var arrow = delta > 0 ? '▲' : '▼';
    return '<tspan class="assess-label-delta assess-label-delta--' + direction + '" dx="5">' +
      arrow + ' ' + fmtNum(Math.abs(delta)) + '</tspan>';
  }

  function buildSilhouette(measurements) {
    // Distribui as medidas alternando pela coluna mais vazia, em ordem de
    // altura no corpo. Antes o lado era fixo por regiao, o que amontoava
    // tudo de um lado quando o aluno nao tinha as medidas do outro.
    var present = Object.keys(SILHOUETTE_ANCHORS)
      .filter(function (key) { return measurements[key]; })
      .map(function (key) {
        return { key: key, x: SILHOUETTE_ANCHORS[key].x, anchorY: SILHOUETTE_ANCHORS[key].y };
      })
      .sort(function (a, b) { return a.anchorY - b.anchorY; });
    if (!present.length) return '';

    var sides = { left: [], right: [] };
    present.forEach(function (item) {
      var side = sides.left.length <= sides.right.length ? 'left' : 'right';
      sides[side].push({
        key: item.key,
        anchorX: side === 'left' ? BODY_VIEW_W - item.x : item.x,
        anchorY: item.anchorY,
      });
    });

    var marks = '';
    var order = 0;
    ['left', 'right'].forEach(function (side) {
      var direction = side === 'left' ? -1 : 1;
      var labelX = side === 'left' ? LABEL_X_LEFT : LABEL_X_RIGHT;
      var textAnchor = side === 'left' ? 'end' : 'start';

      stackLabels(sides[side]).forEach(function (entry) {
        var measure = measurements[entry.key];
        marks +=
          '<g class="assess-mark" style="animation-delay:' + (order++ * 70) + 'ms">' +
            '<path class="assess-dot-line" d="' +
              connectorPath(entry.anchorX, entry.anchorY, labelX, entry.labelY, direction) + '"></path>' +
            '<circle class="assess-dot-halo" cx="' + entry.anchorX + '" cy="' + entry.anchorY + '" r="7.5"></circle>' +
            '<circle class="assess-dot" cx="' + entry.anchorX + '" cy="' + entry.anchorY + '" r="3.6"></circle>' +
            '<text class="assess-label-title" x="' + labelX + '" y="' + (entry.labelY - 5) +
              '" text-anchor="' + textAnchor + '">' +
              escapeHtml(MEASUREMENT_LABELS[entry.key] || entry.key) +
            '</text>' +
            '<text class="assess-label-value" x="' + labelX + '" y="' + (entry.labelY + 11) +
              '" text-anchor="' + textAnchor + '">' +
              fmtNum(measure.current) + 'cm' + deltaTspan(measure.delta) +
            '</text>' +
          '</g>';
      });
    });

    return (
      '<svg class="assess-silhouette" viewBox="0 0 ' + BODY_VIEW_W + ' ' + BODY_VIEW_H + '"' +
        ' xmlns="http://www.w3.org/2000/svg" role="img"' +
        ' aria-label="Silhueta corporal com as circunferências medidas">' +
        '<defs>' +
          '<linearGradient id="pw-body-fill" x1="0" y1="0" x2="0" y2="1">' +
            '<stop offset="0" style="stop-color:var(--accent,#0891B2);stop-opacity:.22"></stop>' +
            '<stop offset="1" style="stop-color:var(--accent,#0891B2);stop-opacity:.05"></stop>' +
          '</linearGradient>' +
          '<radialGradient id="pw-body-glow">' +
            '<stop offset="0" style="stop-color:var(--accent,#0891B2);stop-opacity:.11"></stop>' +
            '<stop offset="1" style="stop-color:var(--accent,#0891B2);stop-opacity:0"></stop>' +
          '</radialGradient>' +
        '</defs>' +
        '<ellipse cx="220" cy="186" rx="128" ry="172" fill="url(#pw-body-glow)"></ellipse>' +
        '<g class="assess-body-shape">' +
          '<circle cx="220" cy="38" r="21"></circle>' +
          '<path d="' + BODY_TORSO_PATH + '"></path>' +
          '<path d="' + BODY_ARM_LEFT_PATH + '"></path>' +
          '<path d="' + BODY_ARM_RIGHT_PATH + '"></path>' +
        '</g>' +
        marks +
      '</svg>'
    );
  }

  function buildMeasurementsGrid(measurements) {
    var keys = Object.keys(measurements);
    if (!keys.length) return '';
    var items = keys.map(function (key) {
      var m = measurements[key];
      var deltaHtml = '';
      if (m.delta !== null && m.delta !== undefined && m.delta !== 0) {
        var cls = m.delta > 0 ? 'up' : 'down';
        deltaHtml = '<span class="assess-measure-delta assess-measure-delta--' + cls + '">' +
          (m.delta > 0 ? '+' : '') + fmtNum(m.delta) + 'cm</span>';
      }
      return (
        '<div class="assess-measure">' +
          '<div class="assess-measure-label">' + escapeHtml(MEASUREMENT_LABELS[key] || key) + '</div>' +
          '<span class="assess-measure-value">' + fmtNum(m.current) + 'cm</span>' + deltaHtml +
        '</div>'
      );
    });
    return '<div class="assess-measurements">' + items.join('') + '</div>';
  }

  function buildTimeline(assessments) {
    var rows = assessments.slice().reverse().map(function (a) {
      var bits = [];
      if (a.weight_kg !== null) bits.push(fmtNum(a.weight_kg) + 'kg');
      Object.keys(a.measurements || {}).forEach(function (key) {
        bits.push((MEASUREMENT_LABELS[key] || key) + ' ' + fmtNum(a.measurements[key]) + 'cm');
      });
      return (
        '<div class="assess-timeline-row">' +
          '<span class="assess-timeline-date">' + fmtDate(a.measured_at) + '</span>' +
          '<span class="assess-timeline-meta">' + escapeHtml(bits.join(' · ')) + '</span>' +
        '</div>'
      );
    });
    return '<div class="assess-timeline">' + rows.join('') + '</div>';
  }

  function buildWeightChart(assessments) {
    var points = assessments
      .map(function (a, i) { return { i: i, w: a.weight_kg, date: a.measured_at }; })
      .filter(function (p) { return p.w !== null && p.w !== undefined; });
    if (points.length < 2) return '';

    var chartW = 600,
      chartH = 100,
      pad = 10;
    var weights = points.map(function (p) { return p.w; });
    var minW = Math.min.apply(null, weights);
    var maxW = Math.max.apply(null, weights);
    var range = maxW - minW || 1;
    var stepX = (chartW - pad * 2) / (points.length - 1 || 1);

    var coords = points.map(function (p, idx) {
      var x = pad + idx * stepX;
      var y = chartH - pad - ((p.w - minW) / range) * (chartH - pad * 2);
      return { x: x, y: y, w: p.w, date: p.date };
    });

    var polyline = coords.map(function (c) { return c.x + ',' + c.y; }).join(' ');
    var dots = coords
      .map(function (c) {
        return '<circle class="assess-chart-dot" cx="' + c.x + '" cy="' + c.y + '" r="3"></circle>' +
          '<text class="assess-chart-label" x="' + c.x + '" y="' + (chartH + 12) + '" text-anchor="middle">' + fmtDate(c.date).slice(0, 5) + '</text>';
      })
      .join('');

    return (
      '<div class="assess-chart">' +
        '<div class="assess-chart-title">Evolução de peso (kg)</div>' +
        '<svg viewBox="0 0 ' + chartW + ' ' + (chartH + 20) + '" preserveAspectRatio="none">' +
          '<polyline class="assess-chart-line" points="' + polyline + '"></polyline>' +
          dots +
        '</svg>' +
      '</div>'
    );
  }

  function buildPanel(report) {
    if (!report.assessments.length) {
      return '<div class="assess-wrap"><div class="assess-empty">Nenhuma avaliação registrada ainda.</div></div>';
    }

    var summary = report.summary;
    var last = report.assessments[report.assessments.length - 1];
    var sections = [];

    sections.push(buildSummaryCards(report.indicators));

    var silhouette = buildSilhouette(summary.measurements);
    var measurementsGrid = buildMeasurementsGrid(summary.measurements);
    if (silhouette || measurementsGrid) {
      sections.push(
        '<div class="assess-body">' + silhouette + '</div>' +
        measurementsGrid
      );
    }

    var chart = buildWeightChart(report.assessments);
    if (chart) sections.push(chart);

    sections.push(buildTimeline(report.assessments));

    var bfSource = report.indicators && report.indicators.body_fat_percent && report.indicators.body_fat_percent.source;
    if (bfSource === 'navy_estimate') {
      sections.push('<div class="assess-source-note">% gordura estimado pelo método de circunferências (US Navy) — margem típica de ±3 a 5 pontos vs. bioimpedância/DEXA. Não substitui avaliação clínica.</div>');
    } else if (bfSource === 'skinfold_jp7') {
      sections.push('<div class="assess-source-note">% gordura calculado pelo método de 7 dobras cutâneas (Jackson-Pollock) — margem típica de ±3 pontos.</div>');
    } else if (bfSource === 'skinfold_jp3') {
      sections.push('<div class="assess-source-note">% gordura calculado pelo método de 3 dobras cutâneas (Jackson-Pollock) — margem típica de ±3 pontos. Informe também a dobra axilar média pra usar o protocolo de 7 dobras, mais preciso.</div>');
    }

    return '<div class="assess-wrap">' + sections.join('') + '</div>';
  }

  function renderError() {
    return '<div class="assess-wrap"><div class="assess-empty">Não foi possível carregar as avaliações agora.</div></div>';
  }

  function mountPanel() {
    var tabsRow = document.querySelector('.tabs');
    if (!tabsRow || document.getElementById('tab-avaliacoes')) return null;
    var panel = document.createElement('div');
    panel.id = 'tab-avaliacoes';
    panel.style.display = 'none';
    panel.innerHTML = '<div class="assess-wrap"><div class="assess-empty">Carregando avaliações…</div></div>';
    tabsRow.insertAdjacentElement('afterend', panel);
    return panel;
  }

  function init() {
    var slug = planSlug();
    var panel = mountPanel();
    if (!slug || !panel) return;

    fetch('/renan/' + slug + '/avaliacoes.json')
      .then(function (response) {
        if (!response.ok) throw new Error('bad status');
        return response.json();
      })
      .then(function (report) {
        panel.innerHTML = buildPanel(report);
      })
      .catch(function () {
        panel.innerHTML = renderError();
      });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
