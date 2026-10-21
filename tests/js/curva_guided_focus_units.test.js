const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function load(file, sandbox) {
  const source = fs.readFileSync(path.join(__dirname, '../../static/js/public_workouts', file), 'utf8');
  vm.runInNewContext(source, sandbox);
  return sandbox.window;
}

const format = load('guided-format.js', { window: {}, Intl }).CurvaGuidedFormat;
const ringModule = load('guided-ring.js', { window: {} }).CurvaGuidedRing;
const timerModule = load('guided-timer.js', { window: {}, JSON }).CurvaGuidedTimer;

function fakeClock() {
  let now = 0;
  let nextId = 1;
  const queue = new Map();
  return {
    now: () => now,
    setTimeout(fn, ms) { const id = nextId++; queue.set(id, { at: now + ms, fn }); return id; },
    clearTimeout(id) { queue.delete(id); },
    advance(ms) {
      const target = now + ms;
      for (;;) {
        let nextKey = null;
        queue.forEach((item, id) => { if (item.at <= target && (nextKey === null || item.at < queue.get(nextKey).at)) nextKey = id; });
        if (nextKey === null) break;
        const item = queue.get(nextKey);
        queue.delete(nextKey);
        now = item.at;
        item.fn();
      }
      now = target;
    },
  };
}

function memoryStorage() {
  const data = new Map();
  return {
    getItem: (k) => (data.has(k) ? data.get(k) : null),
    setItem: (k, v) => data.set(k, String(v)),
    removeItem: (k) => data.delete(k),
    data,
  };
}

const mixed = {
  freeform: false, allowLoad: true, loadKind: 'phase_progressive',
  series: [
    { role: 'warmup', required: true, reps: 12, reps_max: 12 },
    { role: 'top_set', required: true, reps: 6, reps_max: 8, rir_target: 2 },
    { role: 'top_set', required: false, reps: 6, reps_max: 8 },
  ],
};
const straight = { freeform: false, allowLoad: true, series: [{ role: 'top_set', required: true }, { role: 'top_set', required: true }] };

test('rótulo da série mostra o papel só quando o exercício mistura papéis', () => {
  assert.equal(format.setLabel(mixed, mixed.series[1], 2), 'Série principal · 2 de 3');
  assert.equal(format.setLabel(mixed, mixed.series[2], 3), 'Série principal · 3 de 3 · opcional');
  assert.equal(format.setLabel(straight, straight.series[0], 1), 'Série 1 de 2');
  assert.equal(format.setShortLabel(mixed, 1), 'Preparação');
  assert.equal(format.setShortLabel(mixed, 3), 'Série principal 2');
});

test('meta usa reps e RIR estruturado, com fallback no texto do programa', () => {
  assert.equal(format.metaText(mixed, mixed.series[1]), 'Meta 6–8 reps · RIR 2');
  assert.equal(format.metaText({ ...mixed, rirSpec: 'RIR 1–2' }, mixed.series[0]), 'Meta 12 reps · RIR 1–2');
  const structuredWarmup = { ...mixed.series[0], stage_id: 'prep' };
  assert.equal(format.metaText({ ...mixed, rirSpec: 'RIR 1–2' }, structuredWarmup), 'Meta 12 reps');
  assert.equal(format.metaText({ freeform: true, series: [] }, { reps: null }), 'Quantidade livre: registre o que fez');
});

test('CTA reflete os dados e a origem da carga explica o valor preenchido', () => {
  assert.equal(format.ctaText(mixed, { weight: 62.5, reps: 8 }), 'Registrar 62,5 kg × 8');
  assert.equal(format.ctaText(mixed, { weight: 62.5, reps: null, repsRequired: true }), 'Registrar série');
  assert.equal(format.ctaText({ allowLoad: false }, { weight: null, reps: 12 }), 'Registrar 12 reps');
  assert.equal(format.weightSource(mixed, mixed.series[1], { weight: 60, base: 60 }).text, 'Sugestão da fase · ajuste se precisar');
  const changed = format.weightSource(mixed, mixed.series[1], { weight: 62.5, base: 60 });
  assert.equal(changed.reset, 'Voltar para 60 kg');
  assert.equal(format.weightSource(mixed, mixed.series[1], { weight: null, base: null }).text, 'Sem sugestão em kg · informe a carga usada');
});

test('carga alvo da Top explica a sugestão e orienta quando falta kg', () => {
  const ramp = { ...mixed, loadKind: 'free', topTargetKg: 100 };
  const derived = { role: 'feeder', top_factor: 0.7 };
  assert.equal(format.loadSource(ramp, derived), 'Calculada pela sua Top alvo');
  assert.equal(format.weightSource(ramp, derived, { weight: 70, base: 70 }).text, 'Calculada pela sua Top alvo · ajuste se precisar');
  const noTarget = { ...mixed, loadKind: 'free', topTargetKg: null };
  assert.equal(
    format.weightSource(noTarget, derived, { weight: null, base: null }).text,
    'Sem sugestão em kg · defina a Top alvo acima ou informe a carga',
  );
});

test('validação aceita vírgula e recusa texto parcial ou fração de rep', () => {
  assert.equal(format.parseWeight('62,5'), 62.5);
  assert.equal(format.parseWeight(''), null);
  assert.equal(format.parseWeight('62,555'), undefined);
  assert.equal(format.parseWeight('abc'), undefined);
  assert.equal(format.parseReps('8'), 8);
  assert.equal(format.parseReps('8.5'), undefined);
  assert.equal(format.parseReps('0'), undefined);
  assert.equal(format.stepWeight(0.1, 0.2), 0.3);
  assert.equal(format.stepWeight(2.5, -5), 0);
});

test('relógio e textos de tempo', () => {
  assert.equal(format.clock(90), '1:30');
  assert.equal(format.clock(5), '0:05');
  assert.equal(format.spokenDuration(150), '2 minutos e 30 segundos');
  assert.equal(format.valueText(mixed, { weight_kg: '60.00', reps: 8, rir: '1.5' }), '60 kg × 8 · RIR 1,5');
});

test('contagem bate 3, 2, 1, GO e termina uma única vez', () => {
  const clock = fakeClock();
  const events = [];
  ringModule.countdown({
    from: 3, goHoldMs: 600, setTimeout: clock.setTimeout, clearTimeout: clock.clearTimeout,
    onBeat: (n) => events.push(n), onGo: () => events.push('GO'), onDone: (r) => events.push(r.skipped ? 'skip' : 'done'),
  });
  clock.advance(3700);
  assert.deepEqual(events, [3, 2, 1, 'GO', 'done']);
});

test('tocar na contagem pula direto e não dispara GO depois', () => {
  const clock = fakeClock();
  const events = [];
  const run = ringModule.countdown({
    setTimeout: clock.setTimeout, clearTimeout: clock.clearTimeout,
    onBeat: (n) => events.push(n), onGo: () => events.push('GO'), onDone: (r) => events.push(r.skipped ? 'skip' : 'done'),
  });
  clock.advance(10);
  run.skip();
  clock.advance(5000);
  assert.deepEqual(events, [3, 'skip']);
});

test('anel calcula o traço pelo tempo restante', () => {
  const c = ringModule.CIRCUMFERENCE;
  assert.equal(ringModule.offsetFor(90000, 90000), 0);
  assert.equal(ringModule.offsetFor(0, 90000), c);
  assert.ok(Math.abs(ringModule.offsetFor(45000, 90000) - c / 2) < 1e-9);
});

test('descanso alinha os ticks ao segundo, sobrevive a reload e encerra uma vez', () => {
  const clock = fakeClock();
  const storage = memoryStorage();
  const ticks = [];
  let ended = 0;
  const options = {
    storage, now: clock.now, setTimeout: clock.setTimeout, clearTimeout: clock.clearTimeout,
    onTick: (s) => ticks.push(s), onEnd: () => { ended += 1; },
  };
  const timer = timerModule.create(options);
  timer.attach('sessao-1');
  timer.start(5);
  clock.advance(2000);
  assert.deepEqual(ticks, [5, 4, 3]);

  // Recarregar a página: outro timer lê o mesmo horário final.
  const reloaded = timerModule.create({ ...options, onTick: (s) => ticks.push('r' + s) });
  timer.stop();
  storage.setItem('curva-rest:sessao-1', JSON.stringify({ endAt: 5000, total: 5 }));
  reloaded.attach('sessao-1');
  assert.equal(reloaded.snapshot().seconds, 3);
  reloaded.add(30);
  assert.equal(reloaded.snapshot().total, 35);
  clock.advance(40000);
  assert.equal(reloaded.isRunning(), false);
  assert.equal(storage.data.size, 0);
});

test('pular descanso não dispara o fim e limpa o armazenamento', () => {
  const clock = fakeClock();
  const storage = memoryStorage();
  let ended = 0;
  const timer = timerModule.create({
    storage, now: clock.now, setTimeout: clock.setTimeout, clearTimeout: clock.clearTimeout,
    onEnd: () => { ended += 1; },
  });
  timer.attach('s');
  timer.start(90);
  timer.skip();
  clock.advance(100000);
  assert.equal(ended, 0);
  assert.equal(storage.data.size, 0);
  timer.start(2);
  clock.advance(3000);
  assert.equal(ended, 1);
});

test('quadro da carga mostra semana passada → hoje com a variação da periodização', () => {
  const series = [
    { role: 'warmup', weight_kg: 10, top_factor: 0.4 },
    { role: 'top_set', weight_kg: 24, top_factor: 1 },
  ];
  const movement = { allowLoad: true, loadKind: 'phase_progressive', anchorKg: 20, anchorOn: '2026-01-06', series };
  const period = { week: 3, total: 4, phase: 'Força-Hipertrofia' };
  const plan = format.loadPlan(movement, series[1], { period, today: '2026-01-13' });
  assert.deepEqual(
    [plan.fromLabel, plan.fromKg, plan.toLabel, plan.toKg, plan.delta, plan.tone],
    ['Semana passada', 20, 'Hoje', 24, '+20%', 'up'],
  );
  assert.equal(plan.why, 'Semana 3 de 4 · Força-Hipertrofia · cálculo automático');

  // Aquecimento: a conta parte da série principal de hoje.
  const warm = format.loadPlan(movement, series[0], { period, today: '2026-01-13' });
  assert.deepEqual([warm.fromLabel, warm.fromKg, warm.toLabel, warm.toKg, warm.delta], ['Série principal hoje', 24, 'Esta série', 10, '40%']);

  const deload = format.loadPlan({ ...movement, anchorKg: 30 }, series[1], { period, today: '2026-01-13' });
  assert.deepEqual([deload.delta, deload.tone], ['−20%', 'down']);
  const same = format.loadPlan({ ...movement, anchorKg: 24 }, series[1], { period, today: '2026-01-08' });
  assert.deepEqual([same.fromLabel, same.delta, same.tone], ['Último treino', 'Mesma carga', 'same']);
});

test('quadro some sem âncora, com Top alvo do aluno ou sem registro de carga', () => {
  const top = { role: 'top_set', weight_kg: 24, top_factor: 1 };
  const base = { allowLoad: true, loadKind: 'phase_progressive', anchorKg: 20, anchorOn: '2026-01-06', series: [top] };
  assert.equal(format.loadPlan({ ...base, anchorKg: null }, top, {}), null);
  assert.equal(format.loadPlan({ ...base, topTargetKg: 30 }, top, {}), null);
  assert.equal(format.loadPlan({ ...base, allowLoad: false }, top, {}), null);
  assert.equal(format.loadPlan({ ...base, loadKind: 'percentage' }, top, {}), null);
  assert.equal(format.loadPlan(base, { role: 'top_set', weight_kg: null }, {}), null);
  assert.equal(format.whenLabel('2026-01-06', '2026-01-27'), 'Há 3 semanas');
});

test('primeira vez no programa explica que um registro basta para as próximas semanas', () => {
  const first = { allowLoad: true, loadKind: 'free', anchorKg: null, series: [{ role: 'top_set', top_factor: 1 }] };
  assert.equal(
    format.weightSource(first, first.series[0], { weight: null, base: null }).text,
    'Primeira vez aqui: informe a carga que usar. Nas próximas semanas o app calcula sozinho.',
  );
});

test('variação arredonda certo em kg com meio ponto (100 → 107,5 = +8%)', () => {
  const top = { role: 'top_set', weight_kg: 107.5, top_factor: 1 };
  const movement = { allowLoad: true, loadKind: 'phase_progressive', anchorKg: 100, anchorOn: '2026-01-06', series: [top] };
  assert.equal(format.loadPlan(movement, top, { today: '2026-01-13' }).delta, '+8%');
});

test('âncora e semana vêm do HTML; entrada ruim vira "sem âncora"', () => {
  const plain = (value) => JSON.parse(JSON.stringify(value));
  assert.deepEqual(plain(format.anchorFrom('{"kg":100.0,"on":"2026-01-06"}')), { anchorKg: 100, anchorOn: '2026-01-06' });
  assert.deepEqual(plain(format.anchorFrom('{}')), { anchorKg: null, anchorOn: null });
  assert.deepEqual(plain(format.anchorFrom('não é json')), { anchorKg: null, anchorOn: null });
  assert.deepEqual(
    plain(format.periodFrom({ periodWeek: '2', periodTotal: '4', periodPhase: 'Força-Hipertrofia' })),
    { week: 2, total: 4, phase: 'Força-Hipertrofia' },
  );
  assert.equal(format.periodFrom({}), null);
});
