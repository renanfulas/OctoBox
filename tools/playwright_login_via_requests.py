"""
ARQUIVO: login automatizado e captura de métricas com Playwright e requests.

POR QUE ELE EXISTE:
- Permite autenticar via requests, transferir sessão para o Playwright e capturar métricas do dashboard autenticado.

O QUE ESTE ARQUIVO FAZ:
1. Realiza login via requests e obtém o token CSRF.
2. Transfere o cookie de sessão para o navegador Playwright.
3. Permite capturar traces e métricas autenticadas do dashboard.

PONTOS CRITICOS:
- Mudanças podem quebrar o fluxo de login automatizado ou a captura de métricas autenticadas.
"""
import requests
import re
import os
from playwright.sync_api import sync_playwright
import json

BASE = "http://127.0.0.1:8000"
LOGIN = BASE + "/login/"
DASH = BASE + "/dashboard/"

USER = os.getenv('OCTOBOX_TEST_USER', 'renan')
PASS = os.getenv('OCTOBOX_TEST_PASS', 'abc')
TRACE = "trace_dashboard_requests.zip"
LCP = "lcp_dashboard_requests.json"
OUT = "largest_elements_dashboard_requests.json"

s = requests.Session()
# GET login page to fetch CSRF token
r = s.get(LOGIN)
if r.status_code != 200:
    print('login GET failed', r.status_code)
else:
    token = None
    m = re.search(r'name=["\']csrfmiddlewaretoken["\']\s+value=["\']([^"\']+)["\']', r.text)
    if m:
        token = m.group(1)
    data = {'username': USER, 'password': PASS, 'csrfmiddlewaretoken': token, 'next': '/dashboard/'}
    headers = {'Referer': LOGIN}
    post = s.post(LOGIN, data=data, headers=headers)
    print('POST', post.status_code)
    # check if sessionid is set
    sid = s.cookies.get('sessionid')
    print('sessionid present?', bool(sid))

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(viewport={'width':1280,'height':800})
        # set cookies from requests session into playwright
        if sid:
            context.add_cookies([{
                'name': 'sessionid',
                'value': sid,
                'domain': '127.0.0.1',
                'path': '/',
                'httpOnly': True,
                'secure': False
            }])
        page = context.new_page()
        page.add_init_script(r"""() => {
            window.__lcp = [];
            try {
                new PerformanceObserver((list) => {
                    for (const entry of list.getEntries()) {
                        window.__lcp.push({
                            renderTime: entry.renderTime || entry.startTime,
                            size: entry.size || null,
                            url: entry.url || null,
                            element: entry.element ? (entry.element.tagName + (entry.element.className ? '.'+entry.element.className : '')) : null
                        });
                    }
                }).observe({type: 'largest-contentful-paint', buffered: true});
            } catch (e) {
                window.__lcp_error = String(e);
            }
        }""")
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        page.goto(DASH, wait_until='load', timeout=30000)
        page.wait_for_timeout(2000)
        lcp = page.evaluate("() => { try { return window.__lcp || []; } catch(e) { return {error: String(e)} } }")

        data = page.evaluate(r"""() => {
            function isVisible(el){
                if(!el) return false;
                const style = getComputedStyle(el);
                if(style && (style.visibility==='hidden' || style.display==='none' || parseFloat(style.opacity)===0)) return false;
                const rect = el.getBoundingClientRect();
                if(rect.width===0 || rect.height===0) return false;
                const vw = Math.max(document.documentElement.clientWidth || 0, window.innerWidth || 0);
                const vh = Math.max(document.documentElement.clientHeight || 0, window.innerHeight || 0);
                if(rect.bottom < 0 || rect.top > vh) return false;
                return true;
            }
            function textSnippet(s){
                if(!s) return '';
                return s.replace(/\s+/g,' ').trim().slice(0,120);
            }
            const all = Array.from(document.querySelectorAll('body *'));
            const items = [];
            for(const el of all){
                try{
                    if(!isVisible(el)) continue;
                    const r = el.getBoundingClientRect();
                    const area = Math.round(r.width * r.height);
                    const tag = el.tagName.toLowerCase();
                    const classes = el.className || '';
                    const text = textSnippet(el.innerText || el.alt || el.title || '');
                    items.push({tag, classes, text, width: Math.round(r.width), height: Math.round(r.height), area, top: Math.round(r.top)});
                }catch(e){ }
            }
            items.sort((a,b)=>b.area - a.area);
            return items.slice(0,20);
        }""")

        context.tracing.stop(path=TRACE)
        with open(LCP, 'w', encoding='utf-8') as f:
            json.dump(lcp, f, ensure_ascii=False, indent=2)
        with open(OUT, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print('Saved', TRACE, LCP, OUT)
        browser.close()
