"""
ARQUIVO: harness HTTP da simulacao E2E de 30 dias de operacao de um box.

POR QUE ELE EXISTE:
- A simulacao precisa exercitar o app pelas MESMAS rotas que um humano usa
  (HTTP + CSRF + sessao), nao pelo ORM. Sem isso nao se mede UX real nem se
  encontra bug de view/template/permissao.

O QUE ESTE ARQUIVO FAZ:
1. Sessao HTTP por persona, com CSRF automatico e cookies.
2. Journal de toda chamada (persona, dia, acao, rota, status, latencia).
3. Classificacao automatica de incidente: CRASH (5xx), BLOCK (403/404/400
   inesperado), SLOW (acima do orcamento de latencia da tela).

PONTOS CRITICOS:
- Nao esconder erro: toda resposta inesperada vira incidente no journal.
- Latencia medida com o servidor de desenvolvimento -> serve para comparar
  telas entre si, nao como numero absoluto de producao.
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field, asdict

import requests

BASE = 'http://127.0.0.1:8000'
CSRF_RE = re.compile(r'name="csrfmiddlewaretoken" value="([^"]+)"')
SLOW_MS = 1200.0


@dataclass
class Call:
    persona: str
    role: str
    day: int
    action: str
    method: str
    path: str
    status: int
    ms: float
    kind: str = 'ok'          # ok | crash | block | slow | miss
    note: str = ''


class Journal:
    def __init__(self):
        self.calls: list[Call] = []
        self.notes: list[dict] = []

    def add(self, call: Call):
        self.calls.append(call)

    def note(self, persona, day, kind, text):
        self.notes.append({'persona': persona, 'day': day, 'kind': kind, 'text': text})

    def dump(self, path):
        with open(path, 'w') as fh:
            json.dump({
                'calls': [asdict(c) for c in self.calls],
                'notes': self.notes,
            }, fh, indent=1)


JOURNAL = Journal()


class Persona:
    """Uma pessoa usando o app. Mantem sessao e cookies proprios."""

    def __init__(self, name, role, iq=100):
        self.name = name
        self.role = role
        self.iq = iq
        self.s = requests.Session()
        self.s.headers['User-Agent'] = f'OctoBoxSim/{role}'
        self.day = 0
        self.last_html = ''

    # ---------- baixo nivel ----------
    def _csrf(self, url_for_token=None):
        tok = self.s.cookies.get('csrftoken')
        if tok:
            return tok
        if url_for_token:
            self.s.get(BASE + url_for_token, timeout=30)
            return self.s.cookies.get('csrftoken')
        return None

    def get(self, path, action='', expect=(200,), **kw):
        return self._req('GET', path, action or path, expect, **kw)

    def post(self, path, data=None, action='', expect=(200, 302), **kw):
        data = dict(data or {})
        tok = self._csrf(path if path else None)
        # o token do form vale mais que o do cookie quando a pagina ja foi lida
        m = CSRF_RE.search(self.last_html or '')
        data.setdefault('csrfmiddlewaretoken', m.group(1) if m else (tok or ''))
        headers = kw.pop('headers', {})
        headers.setdefault('Referer', BASE + path)
        return self._req('POST', path, action or path, expect, data=data, headers=headers, **kw)

    def _req(self, method, path, action, expect, **kw):
        kw.setdefault('timeout', 60)
        kw.setdefault('allow_redirects', True)
        t0 = time.perf_counter()
        try:
            r = self.s.request(method, BASE + path, **kw)
            ms = (time.perf_counter() - t0) * 1000
            status = r.status_code
        except Exception as exc:                      # noqa: BLE001
            ms = (time.perf_counter() - t0) * 1000
            JOURNAL.add(Call(self.name, self.role, self.day, action, method, path, 0, ms,
                             'crash', f'{type(exc).__name__}: {exc}'))
            return None
        kind, note = 'ok', ''
        if status >= 500:
            kind, note = 'crash', r.text[:300]
        elif status not in expect:
            kind = 'block'
            note = f'esperado {expect}, veio {status}'
        elif ms > SLOW_MS:
            kind, note = 'slow', f'{ms:.0f}ms'
        JOURNAL.add(Call(self.name, self.role, self.day, action, method, path, status, ms, kind, note))
        # sessao perdida: o POST vira redirect para o login e o trabalho some
        if '/login/' in r.url and path != '/login/funcionario/' and not path.startswith('/login'):
            JOURNAL.add(Call(self.name, self.role, self.day, action, method, path, status, ms,
                             'block', 'sessao expirada: redirecionado ao login, dados do form perdidos'))
        if status == 429:
            JOURNAL.add(Call(self.name, self.role, self.day, action, method, path, status, ms,
                             'block', 'rate limit (429)'))
        if 'text/html' in r.headers.get('Content-Type', ''):
            self.last_html = r.text
        return r

    # ---------- fluxos ----------
    def login_staff(self, username, password, retries=6):
        for attempt in range(retries):
            self.get('/login/funcionario/', action='abrir login')
            r = self.post('/login/funcionario/', {'username': username, 'password': password},
                          action='login staff', expect=(200, 302, 429))
            if r is not None and r.status_code == 429:
                JOURNAL.note(self.name, self.day, 'throttle',
                             'login bloqueado por rate limit compartilhado por IP (8/5min)')
                time.sleep(35)
                continue
            ok = bool(r) and r.status_code == 200 and '/login' not in r.url
            if ok:
                return True
            time.sleep(5)
        JOURNAL.note(self.name, self.day, 'blocker', 'login falhou apos varias tentativas')
        return False
