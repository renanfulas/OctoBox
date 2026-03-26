import os
import sys
import json
import logging
from playwright.sync_api import sync_playwright

logger = logging.getLogger('octobox.tools')

BASE = "http://127.0.0.1:8000"
DASH = BASE + "/dashboard/"
TRACE_PATH = "trace_dashboard.zip"
LCP_JSON = "lcp_dashboard.json"

# 🚀 Segurança de Elite: Credenciais via variáveis de ambiente (Audit B105)
USER = os.environ.get("OCTOBOX_TEST_USER", "admin")
PASS = os.environ.get("OCTOBOX_TEST_PASS", "")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(viewport={'width':1280,'height':800})
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
    page.goto(DASH, wait_until='domcontentloaded', timeout=30000)

    pw_count = page.locator('input[type="password"]').count()
    if pw_count:
        page.evaluate(r"""(creds) => {
            const user = creds.user;
            const pwd = creds.pwd;
            const pw = document.querySelector('input[type="password"]');
            if(!pw) return 'no-password';
            const form = pw.form || pw.closest('form');
            if(!form) return 'no-form';
            let uname = form.querySelector('input[type="text"], input[name="username"], input[id*="user"], input[id*="id_username"], input[name*="login"], input[name*="email"]');
            if(!uname) {
                uname = document.querySelector('input[name="username"], input[id*="user"], input[type="text"]');
            }
            if(!uname) return 'no-username';
            uname.focus(); uname.value = user;
            pw.focus(); pw.value = pwd;
            try { form.submit(); return 'submitted'; } catch(e) { form.dispatchEvent(new Event('submit', {bubbles:true,cancelable:true})); return 'dispatched'; }
        }""", {"user": USER, "pwd": PASS})
        try:
            page.wait_for_url('**/dashboard/**', timeout=20000)
        except Exception as e:
            logger.warning(f"Aguardando redirecionamento: {e}")

    page.goto(DASH, wait_until='load', timeout=30000)
    page.wait_for_timeout(2500)
    lcp = page.evaluate("() => { try { return window.__lcp || []; } catch(e) { return {error: String(e)} } }")
    context.tracing.stop(path=TRACE_PATH)

    with open(LCP_JSON, 'w', encoding='utf-8') as f:
        json.dump(lcp, f, ensure_ascii=False, indent=2)

    print(f'Saved trace to {TRACE_PATH} and LCP entries to {LCP_JSON}')
    browser.close()
