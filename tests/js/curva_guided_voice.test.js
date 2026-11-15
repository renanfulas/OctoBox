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
