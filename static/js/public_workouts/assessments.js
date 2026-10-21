/*
 * ARQUIVO: aba "Avaliacoes" do corredor publico de treinos (/renan/<slug>).
 *
 * POR QUE ELE EXISTE:
 * - mostra evolucao fisica (peso/medidas/BF%/RCQ/IMC) num relatorio estilo
 *   bioimpedancia, alimentado por GET /renan/<slug>/avaliacoes.json
 *   (public_workouts app, SHARED_APP — ver student_app/views/public_workout_assessment_views.py).
 * - monta o formulario e atualiza a aba; o HTML do relatorio vive em
 *   assessments-report.js.
 *
 * PONTOS CRITICOS:
 * - o painel #tab-avaliacoes e criado 100% por este arquivo (nenhum template
 *   tem o markup estatico) e injetado logo apos `.tabs` — o showTab()
 *   generico de app.js (ou o das paginas legadas, ja generalizado) descobre
 *   `[id^="tab-"]` sozinho, entao nao precisa de nenhuma mudanca la.
 * - ESCRITA (Onda A3/B4): a autoavaliacao ONLINE e o proprio aluno quem
 *   mede e lanca, via o formulario deste arquivo -> POST
 *   /renan/<slug>/avaliacoes (PublicWorkoutRecordAssessmentView, exige
 *   sessao de LOGIN — 401 sem ela; o formulario manda pra
 *   /treinos/login?next=/renan/<slug> nesse caso, sem checar de antemao
 *   porque nao ha sinal client-side de sessao ativa — o `next` fecha o
 *   ciclo, depois de logar o aluno volta direto pra ca em vez de cair
 *   numa tela generica). US Navy (so fita metrica) sempre disponivel;
 *   dobras cutaneas Jackson-Pollock 7 pontos TAMBEM, mas so depois que
 *   `report.skinfold_self_report_unlocked` vier true — o backend so
 *   libera isso depois que o TREINADOR ja tiver lancado 1a avaliacao por
 *   dobra presencial deste plano (decisao do Renan: confia na tecnica do
 *   aluno pinçando a dobra sozinho so apos ele ja ter sido calibrado ao
 *   vivo). `body_fat_percent`/`body_fat_source` nunca vem deste
 *   formulario direto — mesmo mandando dobras, o servidor que calcula.
 * - o painel tem DOIS slots independentes (ver mountPanel): o formulario
 *   (#assess-form-slot) so' e' montado uma vez e sobrevive aos refreshes;
 *   so o relatorio de leitura (#assess-report-slot) e recriado a cada
 *   fetch de avaliacoes.json — inclusive logo apos um POST bem-sucedido,
 *   pra' o aluno ver a propria avaliacao nova na hora.
 */

(function () {
  'use strict';

  var assessmentReport = window.CurvaAssessmentReport;
  var MEASUREMENT_LABELS = assessmentReport.measurementLabels;
  var escapeHtml = assessmentReport.escapeHtml;

  // Pescoço + cintura (+ quadril nas mulheres) sao as 3 medidas que entram
  // na formula US Navy (public_workouts/formulas.py::estimate_body_fat_navy)
  // — ficam sempre visiveis no formulario. O resto entra atras do <details>
  // pra nao intimidar quem so quer lancar peso + essas 3 medidas.
  var PRIMARY_MEASUREMENT_KEYS = ['pescoco', 'cintura', 'quadril'];
  var SECONDARY_MEASUREMENT_KEYS = ['ombro', 'peito', 'abdomen', 'braco', 'coxa', 'panturrilha'];

  // Dobras cutaneas (mm) do protocolo Jackson-Pollock de 7 pontos — mesmos
  // nomes de public_workouts/management/commands/add_public_workout_assessment.py
  // (--dobra-<key>). So aparecem no formulario quando o backend confirma
  // que o treinador ja calibrou o aluno presencialmente (ver docstring do
  // topo do arquivo) — nunca por decisao do proprio JS.
  var SKINFOLD_KEYS = ['peitoral', 'axilar', 'triceps', 'subescapular', 'abdomen', 'iliaca', 'coxa'];
  var SKINFOLD_LABELS = {
    peitoral: 'Peitoral',
    axilar: 'Axilar média',
    triceps: 'Tríceps',
    subescapular: 'Subescapular',
    abdomen: 'Abdominal',
    iliaca: 'Supra-ilíaca',
    coxa: 'Coxa',
  };

  function planSlug() {
    return document.body.getAttribute('data-plan-slug');
  }

  function pad2(n) {
    return n < 10 ? '0' + n : String(n);
  }

  function todayIso() {
    var d = new Date();
    return d.getFullYear() + '-' + pad2(d.getMonth() + 1) + '-' + pad2(d.getDate());
  }

  // Mesmo padrao de static/js/student_app/pwa.js (getCookie/postJson), sem
  // reusar aquele arquivo direto: e de outro corredor (aluno autenticado
  // do box, com seu proprio bundle) e este aqui roda em paginas publicas
  // sem o resto do app do aluno carregado.
  function getCookie(name) {
    var parts = (document.cookie || '').split(';');
    for (var i = 0; i < parts.length; i++) {
      var part = parts[i].trim();
      if (part.indexOf(name + '=') === 0) {
        return decodeURIComponent(part.slice(name.length + 1));
      }
    }
    return '';
  }

  function postJson(url, payload) {
    return window.fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken'),
        'X-Requested-With': 'XMLHttpRequest',
      },
      body: JSON.stringify(payload || {}),
    }).then(function (response) {
      return response.text().then(function (text) {
        var data = {};
        if (text) {
          try { data = JSON.parse(text); } catch (e) { /* corpo nao-JSON */ }
        }
        return { ok: response.ok, status: response.status, data: data };
      });
    });
  }

  // Idade so entra na formula de dobras cutaneas (Jackson-Pollock) — nao e
  // persistida no backend (mesmo padrao do --age do management command:
  // entra so na hora do calculo). Guardar no localStorage evita perguntar
  // de novo a cada avaliacao, sem precisar de coluna nova no banco.
  function skinfoldAgeStorageKey() {
    return 'pw-assess-age-' + (planSlug() || '');
  }

  function storedAge() {
    try { return localStorage.getItem(skinfoldAgeStorageKey()) || ''; } catch (e) { return ''; }
  }

  function rememberAge(value) {
    try { localStorage.setItem(skinfoldAgeStorageKey(), value); } catch (e) { /* modo anonimo */ }
  }

  /* ══ FORMULARIO DE AUTOAVALIACAO (escrita) ═══════════════════
   * POST /renan/<slug>/avaliacoes — ver docstring do topo do arquivo.
   */

  function measurementFieldHtml(key) {
    return (
      '<label class="assess-field">' +
        '<span class="assess-field-label">' + escapeHtml(MEASUREMENT_LABELS[key]) + '</span>' +
        '<span class="assess-field-input-wrap">' +
          '<input type="number" inputmode="decimal" step="0.1" min="0" data-measure="' + key + '">' +
          '<span class="assess-field-suffix">cm</span>' +
        '</span>' +
      '</label>'
    );
  }

  function skinfoldFieldHtml(key) {
    return (
      '<label class="assess-field">' +
        '<span class="assess-field-label">' + escapeHtml(SKINFOLD_LABELS[key]) + '</span>' +
        '<span class="assess-field-input-wrap">' +
          '<input type="number" inputmode="decimal" step="0.1" min="0" data-skinfold="' + key + '">' +
          '<span class="assess-field-suffix">mm</span>' +
        '</span>' +
      '</label>'
    );
  }

  // So injetada no formulario quando o backend confirma
  // skinfold_self_report_unlocked (ver ensureSkinfoldSection) — nunca
  // presente por padrao.
  function skinfoldSectionHtml() {
    var fields = SKINFOLD_KEYS.map(skinfoldFieldHtml).join('');
    return (
      '<details class="assess-form-more" id="assess-skinfold-details">' +
        '<summary>+ dobras cutâneas (Pollock 7 pontos, com adipômetro)</summary>' +
        '<div class="assess-form-sub">Liberado porque o treinador já fez uma avaliação presencial com adipômetro em você. ' +
          'Preencha as 7 dobras (mm) e a idade — os dois juntos calculam o %gordura.</div>' +
        '<div class="assess-form-grid assess-form-grid--secondary">' +
          '<label class="assess-field">' +
            '<span class="assess-field-label">Idade</span>' +
            '<input type="number" inputmode="numeric" step="1" min="1" id="assess-f-age" value="' +
              escapeHtml(storedAge()) + '">' +
          '</label>' +
          fields +
        '</div>' +
      '</details>'
    );
  }

  function ensureSkinfoldSection(form) {
    if (form.querySelector('#assess-skinfold-details')) return;
    var notesField = form.querySelector('.assess-field--notes');
    if (!notesField) return;
    var wrapper = document.createElement('div');
    wrapper.innerHTML = skinfoldSectionHtml();
    notesField.parentNode.insertBefore(wrapper.firstChild, notesField);
  }

  function buildFormHtml() {
    var primaryFields = PRIMARY_MEASUREMENT_KEYS.map(measurementFieldHtml).join('');
    var secondaryFields = SECONDARY_MEASUREMENT_KEYS.map(measurementFieldHtml).join('');

    return (
      '<form class="assess-form-card" id="assess-form">' +
        '<div class="assess-form-head">' +
          '<div class="assess-form-title">Registrar nova avaliação</div>' +
          '<div class="assess-form-sub">Meça em jejum, sempre no mesmo horário — fita métrica em volta do corpo, sem apertar.</div>' +
        '</div>' +
        '<div class="assess-form-grid">' +
          '<label class="assess-field">' +
            '<span class="assess-field-label">Data</span>' +
            '<input type="date" id="assess-f-date" required>' +
          '</label>' +
          '<label class="assess-field">' +
            '<span class="assess-field-label">Peso</span>' +
            '<span class="assess-field-input-wrap">' +
              '<input type="number" inputmode="decimal" step="0.1" min="0" id="assess-f-weight">' +
              '<span class="assess-field-suffix">kg</span>' +
            '</span>' +
          '</label>' +
          primaryFields +
        '</div>' +
        '<details class="assess-form-more">' +
          '<summary>+ outras medidas (ombro, peito, abdômen, braço, coxa, panturrilha)</summary>' +
          '<div class="assess-form-grid assess-form-grid--secondary">' + secondaryFields + '</div>' +
        '</details>' +
        '<label class="assess-field assess-field--notes">' +
          '<span class="assess-field-label">Observações (opcional)</span>' +
          '<textarea id="assess-f-notes" rows="2" placeholder="Sono, adesão à dieta, como você está se sentindo…"></textarea>' +
        '</label>' +
        '<div class="assess-form-foot">' +
          '<button type="submit" class="assess-form-submit">Salvar avaliação</button>' +
          '<span class="assess-form-feedback" id="assess-f-feedback" role="status" aria-live="polite"></span>' +
        '</div>' +
      '</form>'
    );
  }

  function readFormPayload(form) {
    var payload = {};
    var dateEl = form.querySelector('#assess-f-date');
    payload.measured_at = dateEl ? dateEl.value : '';

    var weightEl = form.querySelector('#assess-f-weight');
    if (weightEl && weightEl.value) payload.weight_kg = parseFloat(weightEl.value);

    var measurements = {};
    Array.prototype.forEach.call(form.querySelectorAll('[data-measure]'), function (input) {
      if (input.value) measurements[input.getAttribute('data-measure')] = parseFloat(input.value);
    });
    if (Object.keys(measurements).length) payload.measurements = measurements;

    var notesEl = form.querySelector('#assess-f-notes');
    if (notesEl && notesEl.value.trim()) payload.notes = notesEl.value.trim();

    return payload;
  }

  // null = secao de dobras nem existe ou o aluno nao tocou nela.
  // 'partial' = comecou a preencher mas faltam dobras (bloqueia o envio).
  // objeto = as 7 preenchidas.
  function collectSkinfoldValues(form) {
    var inputs = form.querySelectorAll('[data-skinfold]');
    if (!inputs.length) return null;
    var values = {};
    var filled = 0;
    Array.prototype.forEach.call(inputs, function (input) {
      if (input.value) {
        values[input.getAttribute('data-skinfold')] = parseFloat(input.value);
        filled += 1;
      }
    });
    if (filled === 0) return null;
    return filled < SKINFOLD_KEYS.length ? 'partial' : values;
  }

  function setFeedback(el, kind, message) {
    if (!el) return;
    el.textContent = message;
    el.className = 'assess-form-feedback' + (kind ? ' assess-form-feedback--' + kind : '');
  }

  function clearEnteredValues(form) {
    Array.prototype.forEach.call(form.querySelectorAll('input[type="number"], textarea'), function (el) {
      if (el.id === 'assess-f-age') return; // idade fica — lembrada pra proxima avaliacao.
      el.value = '';
    });
  }

  function bindForm(form, onSaved) {
    form.addEventListener('submit', function (event) {
      event.preventDefault();
      var slug = planSlug();
      var feedback = form.querySelector('#assess-f-feedback');
      var payload = readFormPayload(form);

      var skinfolds = collectSkinfoldValues(form);
      if (skinfolds === 'partial') {
        setFeedback(feedback, 'error', 'Preencha as 7 dobras cutâneas, ou deixe todas em branco.');
        return;
      }
      if (skinfolds) {
        var ageEl = form.querySelector('#assess-f-age');
        var age = ageEl && ageEl.value ? parseFloat(ageEl.value) : null;
        if (!age) {
          setFeedback(feedback, 'error', 'Informe a idade para calcular pelas dobras cutâneas.');
          return;
        }
        payload.skinfolds = skinfolds;
        payload.age = age;
      }

      if (payload.weight_kg === undefined && payload.measurements === undefined && payload.skinfolds === undefined) {
        setFeedback(feedback, 'error', 'Informe ao menos o peso, uma medida ou as dobras cutâneas.');
        return;
      }

      var submitBtn = form.querySelector('.assess-form-submit');
      if (submitBtn) submitBtn.disabled = true;
      setFeedback(feedback, null, 'Salvando…');

      postJson('/renan/' + slug + '/avaliacoes', payload)
        .then(function (result) {
          if (submitBtn) submitBtn.disabled = false;
          if (result.status === 401) {
            setFeedback(feedback, 'error', 'Sua sessão expirou — ');
            var link = document.createElement('a');
            link.href = '/treinos/login?next=' + encodeURIComponent('/renan/' + slug);
            link.textContent = 'faça login novamente';
            feedback.appendChild(link);
            feedback.appendChild(document.createTextNode(' e tente de novo.'));
            return;
          }
          if (!result.ok) {
            setFeedback(feedback, 'error', (result.data && result.data.error) || 'Não foi possível salvar. Tente de novo.');
            return;
          }
          setFeedback(feedback, 'success', 'Avaliação salva ✓');
          if (payload.age) rememberAge(String(payload.age));
          clearEnteredValues(form);
          if (onSaved) onSaved();
        })
        .catch(function () {
          if (submitBtn) submitBtn.disabled = false;
          setFeedback(feedback, 'error', 'Falha de conexão. Tente de novo.');
        });
    });
  }

  // Dois slots: o formulario (montado uma vez, sobrevive aos refreshes) e o
  // relatorio de leitura (recriado a cada fetch — ver loadReport).
  //
  // Dois hospedeiros possiveis:
  // - `#workout-panel-avaliacao` (template unico, Onda B3): o painel de
  //   nivel superior JA existe no HTML (bottom nav proprio cuida de
  //   mostrar/esconder via .is-tab-active) — so injeta os dois slots
  //   dentro dele, nunca cria um `#tab-avaliacoes` novo ali.
  // - `.tabs` (paginas legadas dos 10 clientes reais): comportamento
  //   original, inalterado — cria `#tab-avaliacoes` como irmao de `.tabs`,
  //   escondido ate o showTab() generico ativar.
  function mountPanel() {
    var existing = document.getElementById('tab-avaliacoes');
    if (existing) return existing;

    var unifiedHost = document.getElementById('workout-panel-avaliacao');
    if (unifiedHost) {
      if (unifiedHost.querySelector('#assess-form-slot')) return unifiedHost;
      var mount = document.createElement('div');
      mount.className = 'assess-wrap';
      mount.innerHTML =
        '<div id="assess-form-slot"></div>' +
        '<div id="assess-report-slot"><div class="assess-empty">Carregando avaliações…</div></div>';
      unifiedHost.appendChild(mount);
      return unifiedHost;
    }

    var tabsRow = document.querySelector('.tabs');
    if (!tabsRow) return null;
    var panel = document.createElement('div');
    panel.id = 'tab-avaliacoes';
    panel.style.display = 'none';
    panel.innerHTML =
      '<div class="assess-wrap">' +
        '<div id="assess-form-slot"></div>' +
        '<div id="assess-report-slot"><div class="assess-empty">Carregando avaliações…</div></div>' +
      '</div>';
    tabsRow.insertAdjacentElement('afterend', panel);
    return panel;
  }

  function loadReport(panel, formSlot, form, reportSlot) {
    var slug = planSlug();
    return fetch('/renan/' + slug + '/avaliacoes.json')
      .then(function (response) {
        if (!response.ok) throw new Error('bad status');
        return response.json();
      })
      .then(function (report) {
        var isUnified = panel.id === 'workout-panel-avaliacao';
        reportSlot.innerHTML = assessmentReport.buildPanel(report, isUnified);
        var hasHistory = report.assessments.length > 0;
        if (isUnified) {
          panel.classList.toggle('has-assessment-history', hasHistory);
          if (hasHistory) formSlot.parentElement.insertBefore(reportSlot, formSlot);
          else formSlot.parentElement.insertBefore(formSlot, reportSlot);
        }
        var newAssessmentButton = reportSlot.querySelector('[data-assess-new]');
        if (newAssessmentButton) {
          newAssessmentButton.addEventListener('click', function () {
            var reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
            formSlot.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'start' });
            var dateInput = formSlot.querySelector('#assess-f-date');
            if (dateInput) dateInput.focus({ preventScroll: true });
          });
        }
        if (report.skinfold_self_report_unlocked) ensureSkinfoldSection(form);
      })
      .catch(function () {
        reportSlot.innerHTML = assessmentReport.renderError();
      });
  }

  function init() {
    var slug = planSlug();
    var panel = mountPanel();
    if (!slug || !panel) return;

    var formSlot = panel.querySelector('#assess-form-slot');
    var reportSlot = panel.querySelector('#assess-report-slot');

    formSlot.innerHTML = buildFormHtml();
    var form = formSlot.querySelector('#assess-form');
    var dateEl = form.querySelector('#assess-f-date');
    if (dateEl) dateEl.value = todayIso();
    bindForm(form, function () { loadReport(panel, formSlot, form, reportSlot); });

    loadReport(panel, formSlot, form, reportSlot);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
