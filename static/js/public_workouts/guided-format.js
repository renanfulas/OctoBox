/* Textos e formatação do treino guiado (modo foco).
 *
 * Puro: sem DOM, sem rede, sem armazenamento — testado em tests/js com node:test.
 * A view (guided-focus.js) só posiciona o que sai daqui; mudar uma frase não
 * exige tocar em layout nem em comando de sessão.
 */
(function () {
  'use strict';

  var ROLE = {
    warmup: 'Preparação', feeder: 'Aproximação', top_set: 'Série principal',
    max_set: 'Série máxima', legacy_unknown: 'Série livre',
  };
  var MOVEMENT_SOURCE = {
    fixed_kg: 'Carga prescrita',
    percentage: 'Calculada pelo seu RM',
    phase_progressive: 'Sugestão da fase',
    rir_estimate: 'Estimativa pelo esforço',
    last_observed: 'Referência da última sessão, não uma prescrição',
  };
  var STAGE_SOURCE = {
    manual: 'Carga escolhida por você',
    fixed_kg: 'Carga definida pelo profissional',
    percent_of_top: 'Aproximação calculada pela série principal',
    percent_of_rm: 'Calculada pelo seu RM',
    suggested_top: 'Referência para a série principal',
  };
  var numberFormat = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 2 });

  function toNumber(value) {
    if (value === null || value === undefined || value === '') return null;
    var parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }

  function decimal(value) {
    var parsed = toNumber(value);
    return parsed === null ? '' : numberFormat.format(parsed);
  }

  function kg(value) {
    var parsed = toNumber(value);
    return parsed === null ? '' : numberFormat.format(parsed) + ' kg';
  }

  function mixedRoles(movement) {
    return movement.series.some(function (series) { return series.role !== movement.series[0].role; });
  }

  function setLabel(movement, series, setNumber) {
    if (movement.freeform) return 'Série livre ' + setNumber;
    var total = movement.series.length;
    var base = mixedRoles(movement)
      ? (ROLE[series.role] || 'Série') + ' · ' + setNumber + ' de ' + total
      : 'Série ' + setNumber + ' de ' + total;
    return base + (series.required === false ? ' · opcional' : '');
  }

  function setShortLabel(movement, setNumber) {
    var series = movement.series[setNumber - 1] || movement.series[0];
    if (movement.freeform) return 'Série livre ' + setNumber;
    if (!mixedRoles(movement)) return 'Série ' + setNumber;
    var sameRole = movement.series.filter(function (item) { return item.role === series.role; });
    var label = ROLE[series.role] || 'Série';
    if (sameRole.length === 1) return label;
    var ordinal = movement.series.slice(0, setNumber).filter(function (item) { return item.role === series.role; }).length;
    return label + ' ' + ordinal;
  }

  function repsText(series) {
    if (!series || series.reps == null) return '';
    return series.reps_max != null && series.reps_max !== series.reps
      ? series.reps + '–' + series.reps_max + ' reps' : series.reps + ' reps';
  }

  function metaText(movement, series) {
    var parts = [];
    var reps = repsText(series);
    if (reps) parts.push(reps);
    // O texto livre de RIR do programa só vale para prescrição legada; numa etapa
    // estruturada (stage_id), aquecimento sem rir_target não herda o RIR da série principal.
    if (series.rir_target != null && series.rir_target !== '') parts.push('RIR ' + decimal(series.rir_target));
    else if (movement.rirSpec && !series.stage_id) parts.push(movement.rirSpec);
    if (parts.length) return 'Meta ' + parts.join(' · ');
    return movement.freeform ? 'Quantidade livre: registre o que fez' : '';
  }

  function loadSource(movement, series) {
    if (!movement.allowLoad) return 'Exercício sem registro de carga';
    if (movement.topTargetKg != null && series.top_factor != null) return 'Calculada pela sua Top alvo';
    if (series.load_source && STAGE_SOURCE[series.load_source]) return STAGE_SOURCE[series.load_source];
    if (MOVEMENT_SOURCE[movement.loadKind]) return MOVEMENT_SOURCE[movement.loadKind];
    return '';
  }

  /* Linha embaixo da carga. `base` é o valor que veio preenchido (sugestão ou
     carga da série anterior do mesmo papel); o que o aluno digita nunca some. */
  function weightSource(movement, series, draft) {
    if (draft.base == null && draft.weight == null) {
      // Sem histórico neste programa: um registro basta para o app calcular as próximas semanas.
      if (movement.loadKind === 'free' && movement.anchorKg == null && series.role === 'top_set') {
        return { text: 'Primeira vez aqui: informe a carga que usar. Nas próximas semanas o app calcula sozinho.', reset: null };
      }
      var canUseTop = series.top_factor != null && movement.topTargetKg == null && movement.loadKind !== 'fixed_kg';
      return {
        text: canUseTop ? 'Sem sugestão em kg · defina a Top alvo acima ou informe a carga' : 'Sem sugestão em kg · informe a carga usada',
        reset: null,
      };
    }
    if (draft.weight != null && draft.weight === draft.base) {
      if (draft.fromPrevious) return { text: 'Mesma carga da sua série anterior · ajuste se precisar', reset: null };
      var source = loadSource(movement, series);
      return { text: (source ? source + ' · ' : '') + 'ajuste se precisar', reset: null };
    }
    if (draft.base == null) return { text: 'Carga informada por você', reset: null };
    return {
      text: (draft.fromPrevious ? 'Série anterior ' : 'Sugerido ') + kg(draft.base) + ' ·',
      reset: 'Voltar para ' + kg(draft.base),
    };
  }

  function ctaText(movement, draft) {
    if (movement.allowLoad && draft.weight != null && draft.reps != null) {
      return 'Registrar ' + decimal(draft.weight) + ' kg × ' + draft.reps;
    }
    if (draft.reps != null) return 'Registrar ' + draft.reps + ' reps';
    if (movement.allowLoad && draft.weight != null && !draft.repsRequired) return 'Registrar ' + kg(draft.weight);
    return 'Registrar série';
  }

  function valueText(movement, entry, withRir) {
    var weight = toNumber(entry.weight_kg);
    var reps = toNumber(entry.reps);
    var main = movement.allowLoad && weight !== null
      ? decimal(weight) + ' kg' + (reps !== null ? ' × ' + reps : '')
      : (reps !== null ? reps + ' reps' : 'Série feita');
    var rir = toNumber(entry.rir);
    return main + (withRir !== false && rir !== null ? ' · RIR ' + decimal(rir) : '');
  }

  function rirText(value) {
    if (value == null) return '';
    return value === 0 ? 'Não faria outra repetição' : 'Ainda faria ' + decimal(value) + (value > 1 ? ' reps' : ' rep');
  }

  function clock(seconds) {
    var safe = Math.max(0, Math.round(seconds));
    return Math.floor(safe / 60) + ':' + String(safe % 60).padStart(2, '0');
  }

  function spokenDuration(seconds) {
    if (seconds < 60) return seconds + ' segundos';
    var minutes = Math.floor(seconds / 60);
    var rest = seconds % 60;
    return minutes + (minutes > 1 ? ' minutos' : ' minuto') + (rest ? ' e ' + rest + ' segundos' : '');
  }

  function parseWeight(text) {
    var normalized = String(text == null ? '' : text).trim().replace(',', '.');
    if (!normalized) return null;
    if (!/^\d{1,4}(\.\d{1,2})?$/.test(normalized)) return undefined;
    var parsed = Number(normalized);
    return parsed <= 9999.99 ? parsed : undefined;
  }

  function parseReps(text) {
    var normalized = String(text == null ? '' : text).trim();
    if (!normalized) return null;
    if (!/^\d{1,3}$/.test(normalized)) return undefined;
    var parsed = Number(normalized);
    return parsed >= 1 ? parsed : undefined;
  }

  /* Passo do stepper sem acumular erro de ponto flutuante (2,5 + 2,5 + ...). */
  function stepWeight(value, delta) {
    return Math.max(0, Math.round((value + delta) * 100) / 100);
  }

  /* "Semana passada 100 kg → Hoje 107,5 kg · +8%": a conta da carga de hoje,
     legível num relance. Datas ISO (AAAA-MM-DD) comparadas em UTC, sem fuso. */
  function isoDays(iso) {
    var parts = String(iso || '').split('-').map(Number);
    return parts.length === 3 && parts.every(Number.isFinite) ? Date.UTC(parts[0], parts[1] - 1, parts[2]) / 86400000 : null;
  }
  function whenLabel(anchorOn, todayIso) {
    var from = isoDays(anchorOn);
    var to = isoDays(todayIso);
    if (from === null || to === null || to < from) return 'Último registro';
    var days = to - from;
    if (days < 7) return 'Último treino';
    if (days < 14) return 'Semana passada';
    return 'Há ' + Math.floor(days / 7) + ' semanas';
  }
  function periodText(period) {
    if (!period || !period.week) return '';
    return 'Semana ' + period.week + (period.total ? ' de ' + period.total : '') + (period.phase ? ' · ' + period.phase : '');
  }
  var ANCHORED_KINDS = { phase_progressive: true, last_observed: true };

  function loadPlan(movement, series, options) {
    options = options || {};
    if (!movement || !series || !movement.allowLoad || movement.topTargetKg != null) return null;
    var today = toNumber(series.weight_kg);
    if (today === null) return null;
    var period = periodText(options.period);
    var factor = toNumber(series.top_factor);
    if (factor !== null && factor < 1) {
      var top = (movement.series || []).filter(function (row) {
        return row.role === 'top_set' && toNumber(row.weight_kg) !== null;
      })[0];
      if (!top) return null;
      return {
        fromLabel: 'Série principal hoje', fromKg: Number(top.weight_kg),
        toLabel: 'Esta série', toKg: today, delta: Math.round(factor * 100) + '%', tone: 'derived',
        why: period || 'Calculada pela série principal',
      };
    }
    var anchor = toNumber(movement.anchorKg);
    if (anchor === null || anchor <= 0 || !movement.anchorOn || !ANCHORED_KINDS[movement.loadKind]) return null;
    // Multiplica antes de dividir: (107,5 / 100 - 1) * 100 dá 7,4999… em ponto flutuante.
    var pct = Math.round((today - anchor) * 100 / anchor);
    return {
      fromLabel: whenLabel(movement.anchorOn, options.today), fromKg: anchor,
      toLabel: 'Hoje', toKg: today,
      delta: pct === 0 ? 'Mesma carga' : (pct > 0 ? '+' : '−') + Math.abs(pct) + '%',
      tone: pct > 0 ? 'up' : (pct < 0 ? 'down' : 'same'),
      why: movement.loadKind === 'phase_progressive'
        ? (period ? period + ' · cálculo automático' : 'Cálculo automático pela periodização')
        : 'Sua última carga registrada',
    };
  }

  window.CurvaGuidedFormat = {
    ROLE: ROLE, decimal: decimal, kg: kg, setLabel: setLabel, setShortLabel: setShortLabel,
    repsText: repsText, metaText: metaText, loadSource: loadSource, weightSource: weightSource,
    ctaText: ctaText, valueText: valueText, rirText: rirText, clock: clock,
    spokenDuration: spokenDuration, parseWeight: parseWeight, parseReps: parseReps,
    stepWeight: stepWeight, loadPlan: loadPlan, whenLabel: whenLabel,
  };
}());
