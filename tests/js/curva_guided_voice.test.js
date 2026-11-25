const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '../../static/js/public_workouts/guided-voice.js'), 'utf8');
const sandbox = { window: {}, navigator: {} };
vm.runInNewContext(source, sandbox);
const Voice = sandbox.window.CurvaGuidedVoice;

// Pacote mínimo com os ids reais do gerador (scripts/coach_voice/build_coach_voice.py).
const ids = [
  'workout_start__v1', 'exercise_start__v1', 'exercise_start__v2',
  'set_prep__v1', 'set_prep_loaded__v1', 'set_feeder__v1', 'set_max__v1', 'set_plain__v1',
  'set_top__kg82_5', 'set_top_noload__v1', 'load__kg60', 'load__kg13', 'load_unknown__v1',
  'set_reps__r8', 'set_reps__r10', 'set_last__v1', 'set_last__v2',
  'rest_start__s90', 'rest_start__s15', 'set_logged__v1', 'set_logged__v2',
  'superset_next__v1', 'workout_end__v1',
];
const manifest = { beep: 'bip.mp3', clips: Object.fromEntries(ids.map((id) => [id, { file: `${id}.mp3` }])) };

function step(series, extra = {}) {
  const movement = { series: extra.series || [series, {}, {}], allowLoad: true, ...extra.movement };
  return { movement, movementIndex: extra.movementIndex ?? 0, setNumber: extra.setNumber ?? 1, series };
}

function fixture() {
  const played = [];
  const storage = new Map([[Voice.STORAGE_KEY, 'on']]);
  const voice = Voice.create({
    manifest, baseUrl: '/static/audio/coach/v2/',
    audio: { play: (url) => { played.push(url.replace('/static/audio/coach/v2/', '').replace('.mp3', '')); return Promise.resolve(); }, unlock() {}, stop() {} },
    storage: { getItem: (k) => storage.get(k) ?? null, setItem: (k, v) => storage.set(k, v) },
    wait: () => Promise.resolve(),
  });
  return { voice, played, storage };
}

const phrases = (s) => [...Voice.setPhrases(manifest, s, {})];

test('top set fala a frase inteira da carga e as reps exatas', () => {
  assert.deepEqual(phrases(step({ stage: 'top', weight_kg: 82.5, reps: 8, reps_max: 8 })),
    ['set_top__kg82_5', 'set_reps__r8']);
});

test('top set com carga fora do pacote usa a frase sem número', () => {
  assert.deepEqual(phrases(step({ stage: 'top', weight_kg: 83.75, reps: 8 })), ['set_top_noload__v1', 'set_reps__r8']);
});

test('aproximação: fase + frase de carga compartilhada', () => {
  assert.deepEqual(phrases(step({ stage: 'feeder', weight_kg: 60, reps: null })), ['set_feeder__v1', 'load__kg60']);
});

test('preparatória com carga não diz "sem peso"', () => {
  assert.deepEqual(phrases(step({ stage: 'prep', weight_kg: 13, reps: 10 })),
    ['set_prep_loaded__v1', 'load__kg13', 'set_reps__r10']);
  assert.deepEqual(phrases(step({ stage: 'prep', weight_kg: null, reps: 10 })), ['set_prep__v1', 'set_reps__r10']);
});

test('carga desconhecida em série comum pede para conferir na tela', () => {
  assert.deepEqual(phrases(step({ stage: 'plain', weight_kg: 61.25 })), ['set_plain__v1', 'load_unknown__v1']);
});

test('faixa de reps (1-3) fica na tela; exercício sem carga não fala carga', () => {
  assert.deepEqual(phrases(step({ stage: 'top', weight_kg: 82.5, reps: 1, reps_max: 3 })), ['set_top__kg82_5']);
  assert.deepEqual(phrases(step({ stage: 'feeder', weight_kg: 60 }, { movement: { allowLoad: false } })), ['set_feeder__v1']);
});

test('última série do exercício ganha o "é a última"', () => {
  const s = { stage: 'top', weight_kg: 82.5, reps: 8 };
  assert.deepEqual(phrases(step(s, { series: [{}, {}, s], setNumber: 3 })), ['set_top__kg82_5', 'set_reps__r8', 'set_last__v1']);
});

test('exercício livre não é anunciado', () => {
  assert.deepEqual(phrases(step({ stage: 'freeform' }, { movement: { freeform: true } })), []);
});

test('descanso longo: confirma e avisa já, anuncia a próxima só perto do fim', async () => {
  const { voice, played } = fixture();
  const current = step({ stage: 'feeder', weight_kg: 60 });
  const next = step({ stage: 'top', weight_kg: 82.5, reps: 8 }, { setNumber: 2 });
  await voice.setRecorded({ step: current, next, restSeconds: 90 });
  assert.deepEqual(played, ['bip', 'set_logged__v1', 'rest_start__s90']);
  await voice.restTick(40000);
  assert.equal(played.length, 3, 'meio do descanso: silêncio');
  await voice.restTick(Voice.ANNOUNCE_AT_MS);
  assert.deepEqual(played.slice(3), ['bip', 'set_top__kg82_5', 'set_reps__r8']);
  await voice.restTick(5000);
  assert.equal(played.length, 6, 'anuncia uma vez só');
});

test('descanso curto anuncia logo depois do "Descansa"', async () => {
  const { voice, played } = fixture();
  await voice.setRecorded({
    step: step({ stage: 'plain' }), next: step({ stage: 'top', weight_kg: 82.5, reps: 8 }), restSeconds: 15,
  });
  assert.deepEqual(played, ['bip', 'set_logged__v1', 'rest_start__s15', 'set_top__kg82_5', 'set_reps__r8']);
});

test('próxima série em outro exercício abre com "Próximo exercício"', async () => {
  const { voice, played } = fixture();
  await voice.setRecorded({
    step: step({ stage: 'plain' }), next: step({ stage: 'feeder', weight_kg: 60 }, { movementIndex: 1 }), restSeconds: 90,
  });
  await voice.restSkipped();
  assert.deepEqual(played.slice(3), ['bip', 'exercise_start__v1', 'set_feeder__v1', 'load__kg60']);
});

test('bi-set sem descanso: "Sem descanso" e já a série do par', async () => {
  const { voice, played } = fixture();
  await voice.setRecorded({
    step: step({ stage: 'plain' }), next: step({ stage: 'feeder', weight_kg: 60 }, { movementIndex: 1 }),
    restSeconds: 0, superset: true,
  });
  assert.deepEqual(played, ['bip', 'set_logged__v1', 'superset_next__v1', 'set_feeder__v1', 'load__kg60']);
});

test('variações revezam sem repetir na sessão', async () => {
  const { voice, played } = fixture();
  const s = step({ stage: 'plain' });
  await voice.setRecorded({ step: s, next: null });
  await voice.setRecorded({ step: s, next: null });
  assert.deepEqual(played.filter((id) => id.startsWith('set_logged')), ['set_logged__v1', 'set_logged__v2']);
});

test('toggle desligado: nada toca; encerramento completo agradece', async () => {
  const { voice, played, storage } = fixture();
  storage.set(Voice.STORAGE_KEY, 'off');
  await voice.started(step({ stage: 'top', weight_kg: 82.5 }));
  assert.deepEqual(played, []);
  storage.set(Voice.STORAGE_KEY, 'on');
  await voice.finished('complete');
  assert.deepEqual(played, ['bip', 'workout_end__v1']);
});

test('pré-cache: só as cargas, reps e descansos da prescrição, mais as fixas', () => {
  const { voice } = fixture();
  const urls = voice.urlsFor([{ series: [{ weight_kg: 82.5, reps: 8, rest_seconds: 90 }] }])
    .map((u) => u.replace('/static/audio/coach/v2/', ''));
  assert.ok(urls.includes('bip.mp3'));
  assert.ok(urls.includes('set_top__kg82_5.mp3') && urls.includes('set_reps__r8.mp3') && urls.includes('rest_start__s90.mp3'));
  assert.ok(!urls.includes('load__kg60.mp3') && !urls.includes('set_reps__r10.mp3'), 'cargas de outros treinos ficam fora');
  assert.ok(urls.includes('workout_start__v1.mp3'));
});

/* ---------- contagem intra-série (top set e AMRAP) ---------- */
const countIds = ['count_setup_top__v1', 'count_setup_max__v1', 'count_go__v1', 'count_push__v1', 'count_done_top__v1'];
for (let n = 1; n <= 30; n += 1) {
  for (let v = 1; v <= 4; v += 1) countIds.push(`count__r${n}_v${v}`);
  for (let v = 1; v <= 3; v += 1) countIds.push(`count_beyond__r${n}_v${v}`);
  ['count_half', 'count_left2', 'count_left1', 'count_last', 'count_goal', 'count_safety', 'count_stop']
    .forEach((event) => countIds.push(`${event}__r${n}`));
}
const countManifest = {
  beep: 'bip.mp3', tick: 'tick.mp3', go: 'go.mp3',
  clips: Object.fromEntries(ids.concat(countIds).map((id) => [id, { file: `${id}.mp3` }])),
};

// Relógio virtual: wait(ms) avança o tempo; o áudio "toca" na hora em que é chamado.
function countFixture() {
  let clock = 0;
  const played = [];
  const voice = Voice.create({
    manifest: countManifest, baseUrl: '/a/',
    audio: { play: (url) => { played.push({ id: url.replace('/a/', '').replace('.mp3', ''), at: clock }); return Promise.resolve(); }, unlock() {}, stop() {} },
    storage: { getItem: () => 'on', setItem() {} },
    // Espera longa (o ritmo) vira um tique do event loop, como um timer de verdade;
    // a folga entre falas (< 300 ms) resolve na hora, e a fila de áudio anda antes.
    wait: (ms) => { clock += ms; return ms >= 300 ? new Promise((resolve) => setImmediate(resolve)) : Promise.resolve(); },
    now: () => clock,
  });
  return { voice, played, ids: () => played.map((p) => p.id), advance: (ms) => { clock += ms; } };
}

const settle = () => new Promise((resolve) => setImmediate(resolve));

const plan = (series) => Voice.countPlan(countManifest, step(series));

test('contagem só na top set com meta e na AMRAP; nunca em isometria ou preparatória', () => {
  assert.equal(Voice.countMode(step({ stage: 'top', reps: 8 })), 'top');
  assert.equal(Voice.countMode(step({ stage: 'top', reps: null })), null);
  assert.equal(Voice.countMode(step({ stage: 'max', reps: null })), 'max');
  assert.equal(Voice.countMode(step({ stage: 'plain', reps: 8, amrap: true })), 'max');
  assert.equal(Voice.countMode(step({ stage: 'prep', reps: 10 })), null);
  assert.equal(Voice.countMode(step({ stage: 'top', reps: 8, hold_seconds: 30 })), null);
});

test('top set de 8: ritmo, metade, faltam duas, falta uma e a última mais lenta', () => {
  const p = plan({ stage: 'top', reps: 8, reps_max: 8 });
  assert.deepEqual([...p.reps.map((r) => r.id)], [
    'count__r1_v1', 'count__r2_v2', 'count__r3_v3', 'count_half__r4', 'count__r5_v4',
    'count_left2__r6', 'count_left1__r7', 'count_last__r8',
  ]);
  assert.deepEqual([...p.reps.map((r) => r.endMs)], [3000, 6000, 9000, 12000, 15000, 18000, 21500, 25500]);
  assert.equal(p.reps[7].pushMs, 23500, '"sobe, sobe" no fundo da última');
});

test('top set com faixa (8-10) conta até o topo da faixa', () => {
  const p = plan({ stage: 'top', reps: 8, reps_max: 10 });
  assert.equal(p.reps.length, 10);
  assert.equal(p.reps[9].id, 'count_last__r10');
});

test('AMRAP com meta 8: meta batida, aviso de técnica e incentivo até 30, cada vez mais lento', () => {
  const p = plan({ stage: 'max', reps: 8 });
  assert.deepEqual([...p.reps.slice(5, 13).map((r) => r.id)], [
    'count_left2__r6', 'count_left1__r7', 'count_goal__r8', 'count_safety__r9',
    'count_beyond__r10_v1', 'count_beyond__r11_v2', 'count_beyond__r12_v3', 'count_beyond__r13_v1',
  ]);
  assert.equal(p.reps.length, 30);
  const durations = [...p.reps].map((r, i) => r.endMs - (i ? p.reps[i - 1].endMs : 0));
  assert.deepEqual(durations.slice(6, 13), [3000, 3500, 4000, 4000, 4500, 5000, 5000]);
});

test('AMRAP sem meta: conta o ritmo e vira incentivo depois da 5ª', () => {
  const p = plan({ stage: 'max', reps: null });
  assert.deepEqual([...p.reps.slice(3, 7).map((r) => r.id)],
    ['count__r4_v4', 'count__r5_v1', 'count_safety__r6', 'count_beyond__r7_v1']);
});

test('contar comigo na top set: preparo, 3-2-1, contagem no ritmo e fechamento; preenche as reps', async () => {
  const { voice, played, ids } = countFixture();
  const reps = [];
  let done = null;
  await voice.countStart(step({ stage: 'top', reps: 3 }), { onRep: (n) => reps.push(n), onDone: (n) => { done = n; } });
  await settle();
  assert.deepEqual(ids(), ['bip', 'count_setup_top__v1', 'tick', 'tick', 'tick', 'go', 'count_go__v1',
    'count__r1_v1', 'count_left1__r2', 'count_push__v1', 'count_last__r3', 'count_done_top__v1']);
  assert.deepEqual(reps, [1, 2, 3]);
  assert.equal(done, 3);
  const at = (id) => played.find((p) => p.id === id).at;
  // Rep 1 termina 3 s depois do "valendo"; a 2ª (falta uma) leva 3,5 s.
  assert.equal(at('count__r1_v1') - at('go'), 2900);
  assert.equal(at('count_left1__r2') - at('count__r1_v1'), 3500);
  assert.equal(voice.counting(), false);
});

test('"Parei" na AMRAP para a contagem, devolve as reps contadas e fala o fechamento', async () => {
  const { voice, ids, advance } = countFixture();
  let stopped = null;
  const running = voice.countStart(step({ stage: 'max', reps: 8 }), {
    // Fez a 12ª e tocou 3 s depois do "doze" (fora da janela de tolerância).
    onRep: (n) => { if (n === 12) { advance(3000); stopped = voice.countStop(); } },
  });
  await running;
  await settle();
  assert.equal(stopped, 12);
  // "Parei" corta a fala em andamento (o incentivo da 12) e vai direto ao fechamento.
  assert.deepEqual(ids().slice(-3), ['count_beyond__r10_v1', 'count_beyond__r11_v2', 'count_stop__r12']);
  assert.equal(voice.counting(), false);
});

test('"Parei" logo depois da rep anunciada não conta essa rep (o aluno parou na anterior)', async () => {
  const { voice, ids, advance } = countFixture();
  let stopped = null;
  const running = voice.countStart(step({ stage: 'max', reps: 8 }), {
    // Parou na 11ª: larga a barra, a voz já diz "doze", e ele toca 2 s depois.
    onRep: (n) => { if (n === 12) { advance(2000); stopped = voice.countStop(); } },
  });
  await running;
  await settle();
  assert.equal(stopped, 11);
  assert.equal(ids().at(-1), 'count_stop__r11');
});

test('"Parei" logo depois da 1ª rep devolve zero e não fala fechamento', async () => {
  const { voice, ids } = countFixture();
  let stopped = null;
  await voice.countStart(step({ stage: 'max', reps: 8 }), { onRep: (n) => { if (n === 1) stopped = voice.countStop(); } });
  await settle();
  assert.equal(stopped, 0);
  assert.ok(!ids().some((id) => id.startsWith('count_stop__')));
});

test('volta do segundo plano: reps vencidas atualizam a tela sem rajada de voz', async () => {
  const { voice, ids, advance } = countFixture();
  const reps = [];
  await voice.countStart(step({ stage: 'top', reps: 8 }), {
    onRep: (n) => {
      reps.push(n);
      // Na 2ª rep o aluno abre o Spotify: os timers do app congelam por 10 s.
      if (n === 2) advance(10000);
    },
  });
  await settle();
  // A tela passa por todas; a voz cala a 3ª e a 4ª (vencidas) e retoma na 5ª.
  assert.deepEqual(reps, [1, 2, 3, 4, 5, 6, 7, 8]);
  assert.ok(!ids().includes('count__r3_v3'));
  assert.ok(!ids().includes('count_half__r4'));
  assert.deepEqual(ids().slice(ids().indexOf('count__r2_v2')),
    ['count__r2_v2', 'count__r5_v4', 'count_left2__r6', 'count_left1__r7', 'count_push__v1', 'count_last__r8', 'count_done_top__v1']);
});

test('registrar a série no meio da contagem cala a contagem', async () => {
  const { voice, ids } = countFixture();
  const top = step({ stage: 'top', reps: 8 });
  await voice.countStart(top, { onRep: (n) => { if (n === 2) voice.setRecorded({ step: top, next: null }); } });
  await settle();
  assert.ok(!ids().includes('count__r3_v3'));
  assert.equal(ids().at(-1), 'set_logged__v1');
});

test('contar comigo com outra fala tocando: corta a fala e só começa o 3-2-1 depois do preparo', async () => {
  // Regressão (navegador, 2026-11-16): com a fila ocupada, o preparo resolvia na
  // hora, o 3-2-1 entrava na fila atrás do anúncio e o áudio atrasava a contagem.
  let clock = 0;
  let hanging = null;
  const played = [];
  const voice = Voice.create({
    manifest: countManifest, baseUrl: '/a/',
    audio: {
      play: (url) => {
        const id = url.replace('/a/', '').replace('.mp3', '');
        played.push(id);
        // "Série registrada" só termina quando alguém para o player.
        return id === 'set_logged__v1' ? new Promise((resolve) => { hanging = resolve; }) : Promise.resolve();
      },
      unlock() {},
      stop() { if (hanging) { hanging(); hanging = null; } },
    },
    storage: { getItem: () => 'on', setItem() {} },
    wait: (ms) => { clock += ms; return ms >= 300 ? new Promise((resolve) => setImmediate(resolve)) : Promise.resolve(); },
    now: () => clock,
  });
  const top = step({ stage: 'top', reps: 3 });
  voice.setRecorded({ step: top, next: null });
  await settle();
  await voice.countStart(top, {});
  await settle();
  assert.deepEqual(played, ['bip', 'set_logged__v1', 'bip', 'count_setup_top__v1', 'tick', 'tick', 'tick', 'go',
    'count_go__v1', 'count__r1_v1', 'count_left1__r2', 'count_push__v1', 'count_last__r3', 'count_done_top__v1']);
});

test('fala cortada no meio não toca o resto do grupo', async () => {
  let hanging = null;
  const played = [];
  const voice = Voice.create({
    manifest: countManifest, baseUrl: '/a/',
    audio: {
      play: (url) => {
        const id = url.replace('/a/', '').replace('.mp3', '');
        played.push(id);
        return id === 'workout_start__v1' ? new Promise((resolve) => { hanging = resolve; }) : Promise.resolve();
      },
      unlock() {},
      stop() { if (hanging) { hanging(); hanging = null; } },
    },
    storage: { getItem: () => 'on', setItem() {} },
    wait: () => Promise.resolve(),
  });
  const started = voice.started(step({ stage: 'top', reps: 3 }));
  await settle();
  voice.finished('cancelled');
  await started;
  assert.deepEqual(played, ['bip', 'workout_start__v1']);
});

test('pré-cache da contagem só entra quando o treino tem top set ou AMRAP', () => {
  const { voice } = countFixture();
  const plain = voice.urlsFor([{ series: [{ stage: 'plain', reps: 10 }] }]).map((u) => u.replace('/a/', ''));
  assert.ok(!plain.some((u) => u.startsWith('count')) && !plain.includes('tick.mp3'));
  const top = voice.urlsFor([{ series: [{ stage: 'top', reps: 8 }] }]).map((u) => u.replace('/a/', ''));
  assert.ok(top.includes('tick.mp3') && top.includes('go.mp3') && top.includes('count_setup_top__v1.mp3'));
  assert.ok(top.includes('count_last__r8.mp3') && top.includes('count_stop__r5.mp3'));
  assert.ok(!top.includes('count_last__r9.mp3'), 'só as falas desta meta');
});
