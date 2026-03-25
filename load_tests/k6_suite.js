import http from 'k6/http';
import { check, sleep } from 'k6';
import { Trend } from 'k6/metrics';

// Ajuste as variáveis abaixo conforme seu ambiente
const HOST = __ENV.HOST || 'http://127.0.0.1:8000';
const USER = __ENV.TEST_USER || 'test';
const PASS = __ENV.TEST_PASS || 'pass';

export let options = {
  scenarios: {
    smoke: { executor: 'constant-vus', vus: 5, duration: '1m' },
    ramp: { executor: 'ramping-vus', startVUs: 0, stages: [
      { duration: '2m', target: 10 },
      { duration: '5m', target: 100 },
      { duration: '10m', target: 200 },
      { duration: '5m', target: 0 },
    ]},
    spike: { executor: 'constant-vus', vus: 300, duration: '1m', startTime: '20m' },
  },
  thresholds: {
    'http_req_duration': ['p(95)<2000'],
    'errors': ['rate<0.03'],
  },
};

let reqTrend = new Trend('req_duration');

function login() {
  let res = http.post(`${HOST}/api/auth/login`, JSON.stringify({ username: USER, password: PASS }), { headers: { 'Content-Type': 'application/json' } });
  if (res.status === 200) {
    try { return res.json('token'); } catch (e) { return null; }
  }
  return null;
}

export default function () {
  let token = login();
  let headers = token ? { headers: { 'Authorization': `Bearer ${token}` } } : {};

  // 1) Listagem com filtros (paginação)
  let r1 = http.get(`${HOST}/api/students?limit=50&offset=0`, headers);
  check(r1, { 'students list OK': (r) => r.status === 200 });
  reqTrend.add(r1.timings.duration);

  // 2) Bulk update (simula um patch em lote)
  let bulkPayload = JSON.stringify({ ids: [1,2,3,4,5], data: { status: 'processed' } });
  let r2 = http.post(`${HOST}/api/items/bulk-update`, bulkPayload, Object.assign({}, headers, { headers: { 'Content-Type': 'application/json', ...(headers.headers || {}) } }));
  check(r2, { 'bulk update resp OK': (r) => r.status === 200 || r.status === 207 });
  reqTrend.add(r2.timings.duration);

  // 3) Criar job de import (simulado via JSON) e checar status
  let importPayload = JSON.stringify({ filename: 'students_seed.csv', notify: false });
  let r3 = http.post(`${HOST}/api/imports`, importPayload, Object.assign({}, headers, { headers: { 'Content-Type': 'application/json', ...(headers.headers || {}) } }));
  check(r3, { 'import create OK': (r) => r.status === 201 || r.status === 200 });
  if (r3.status === 201) {
    let jobId = r3.json('id');
    let r3s = http.get(`${HOST}/api/imports/${jobId}`, headers);
    reqTrend.add(r3s.timings.duration);
  }

  // 4) Snapshot create
  let snap = http.post(`${HOST}/api/snapshots/create`, JSON.stringify({ note: 'k6 test snapshot' }), Object.assign({}, headers, { headers: { 'Content-Type': 'application/json', ...(headers.headers || {}) } }));
  check(snap, { 'snapshot request accepted': (r) => r.status === 200 || r.status === 202 });
  reqTrend.add(snap.timings.duration);

  // 5) Webhook deliver (envia evento a um endpoint configurado)
  // Ajuste WEBHOOK_TARGET via env para testar outbox/delivery
  const WEBHOOK_TARGET = __ENV.WEBHOOK_TARGET || `${HOST}/webhook/echo`;
  let hook = http.post(WEBHOOK_TARGET, JSON.stringify({ event: 'test.event', payload: { ts: Date.now() } }), { headers: { 'Content-Type': 'application/json' } });
  reqTrend.add(hook.timings.duration);

  sleep(1);
}

export function handleSummary(data) {
  return {
    'summary.json': JSON.stringify(data),
  };
}
