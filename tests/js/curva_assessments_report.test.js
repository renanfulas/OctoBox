const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(
  path.join(__dirname, '../../static/js/public_workouts/assessments-report.js'), 'utf8',
);
const sandbox = { window: {} };
vm.runInNewContext(source, sandbox);
const reportView = sandbox.window.CurvaAssessmentReport;

test('mostra estado vazio nas páginas legada e unificada', () => {
  const report = { assessments: [] };
  assert.match(reportView.buildPanel(report, false), /Nenhuma avaliação/);
  assert.match(reportView.buildPanel(report, true), /Comece sua linha do tempo/);
});

test('renderiza evolução e escapa valores textuais', () => {
  const report = {
    assessments: [
      { measured_at: '2026-09-01', weight_kg: 70, measurements: { cintura: 80 } },
      { measured_at: '2026-10-01', weight_kg: 69, measurements: { cintura: 78 } },
    ],
    summary: { measurements: { cintura: { current: 78, delta: -2 } } },
    indicators: { bmi: { value: 22, delta: -1, classification: { level: 'ok', label: '<script>' } } },
  };
  const html = reportView.buildPanel(report, true);
  assert.match(html, /Evolução de peso/);
  assert.match(html, /Silhueta corporal/);
  assert.match(html, /&lt;script&gt;/);
  assert.doesNotMatch(html, /<script>/);
  assert.match(html, /Nova avaliação/);
});
