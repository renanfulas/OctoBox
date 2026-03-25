import http from 'k6/http';
import { check, sleep } from 'k6';
import { Trend } from 'k6/metrics';

const HOST = __ENV.HOST || 'http://127.0.0.1:8000';
const USER = __ENV.TEST_USER || 'test';
const PASS = __ENV.TEST_PASS || 'pass';

export let options = {
  stages: [
    { duration: '1m', target: 20 },
    { duration: '3m', target: 50 },
    { duration: '5m', target: 100 },
    { duration: '2m', target: 0 },
  ],
  thresholds: {
    'http_req_duration': ['p(95)<5000'],
    'errors': ['rate<0.05'],
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

  // Cria snapshot (operação pesada)
  let snapRes = http.post(`${HOST}/api/snapshots/create`, JSON.stringify({ note: 'stress test snapshot' }), Object.assign({}, headers, { headers: { 'Content-Type': 'application/json', ...(headers.headers || {}) } }));
  check(snapRes, { 'snapshot create accepted': (r) => r.status === 200 || r.status === 202 });
  reqTrend.add(snapRes.timings.duration);

  // Tenta restaurar um snapshot (se tiver id retornado)
  if (snapRes.status === 201 || snapRes.status === 200) {
    let body = snapRes.json();
    let id = body && (body.id || body.snapshot_id);
    if (id) {
      let restore = http.post(`${HOST}/api/snapshots/restore`, JSON.stringify({ id: id }), Object.assign({}, headers, { headers: { 'Content-Type': 'application/json', ...(headers.headers || {}) } }));
      check(restore, { 'restore requested': (r) => r.status === 200 || r.status === 202 || r.status === 201 });
      reqTrend.add(restore.timings.duration);
    }
  }

  sleep(1);
}

export function handleSummary(data) {
  return { 'snapshot_summary.json': JSON.stringify(data) };
}
