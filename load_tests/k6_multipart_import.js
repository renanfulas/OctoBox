import http from 'k6/http';
import { check, sleep } from 'k6';
import { SharedArray } from 'k6/data';

const HOST = __ENV.HOST || 'http://127.0.0.1:8000';
const USER = __ENV.TEST_USER || 'test';
const PASS = __ENV.TEST_PASS || 'pass';

export let options = {
  vus: 10,
  duration: '5m',
  thresholds: {
    'http_req_duration': ['p(95)<3000'],
    'errors': ['rate<0.05'],
  },
};

function login() {
  let res = http.post(`${HOST}/api/auth/login`, JSON.stringify({ username: USER, password: PASS }), { headers: { 'Content-Type': 'application/json' } });
  if (res.status === 200) {
    try { return res.json('token'); } catch (e) { return null; }
  }
  return null;
}

// Carrega um CSV de exemplo do disco local (pré-gerado)
const csvFiles = new SharedArray('csvs', function() {
  return [__ENV.CSV_FILE || 'students_seed.csv'];
});

export default function () {
  let token = login();
  let headers = token ? { 'Authorization': `Bearer ${token}` } : {};

  let filePath = csvFiles[0];
  let f = open(filePath, 'b');

  let formData = {
    file: http.file(f, filePath, 'text/csv'),
    notify: 'false'
  };

  let res = http.post(`${HOST}/api/imports`, formData, { headers: headers });
  check(res, { 'import upload accepted': (r) => r.status === 200 || r.status === 201 });

  sleep(1);
}
