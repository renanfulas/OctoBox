from playwright.sync_api import sync_playwright
import os, json

BASE = os.environ.get('BASE_URL', 'http://127.0.0.1:8000')
USER = os.environ.get('AUTO_USER', 'autotest')
PASS = os.environ.get('AUTO_PASS', 'Aut0Test!')
OUT_DIR = 'playwright_capture_click'

os.makedirs(OUT_DIR, exist_ok=True)
logs = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(locale='pt-BR')
    page = context.new_page()

    def on_console(msg):
        try:
            loc = msg.location
        except Exception:
            loc = None
        logs.append({'event': 'console', 'type': msg.type, 'text': msg.text, 'location': loc})

    def on_page_error(err):
        logs.append({'event': 'pageerror', 'error': str(err)})

    def on_response(response):
        try:
            status = response.status
        except Exception:
            status = None
        try:
            url = response.url
        except Exception:
            url = ''
        if url and any(p in url for p in ['/login', '/dashboard', '/operacao', '/api/']):
            try:
                text = response.text()
            except Exception:
                text = ''
            logs.append({'event': 'response', 'url': url, 'status': status, 'text_snippet': text[:1000]})

    page.on('console', on_console)
    page.on('pageerror', on_page_error)
    page.on('response', on_response)

    page.goto(f'{BASE}/login/', timeout=30000)
    page.fill('input[name="username"]', USER)
    page.fill('input[name="password"]', PASS)
    page.click('button[type="submit"]')

    # navigate explicitly to dashboard (avoid role-based redirect)
    try:
        page.goto(f'{BASE}/dashboard/', timeout=30000)
    except Exception:
        pass

    # try to click the overdue card article
    try:
        # click article that has eyebrow text
        sel = 'article:has(p.eyebrow:has-text("Cobrancas em atraso"))'
        page.wait_for_selector(sel, timeout=5000)
        page.click(sel)
    except Exception as e:
        logs.append({'event': 'click-error', 'error': str(e)})

    page.screenshot(path=os.path.join(OUT_DIR, 'after_click.png'), full_page=True)
    with open(os.path.join(OUT_DIR, 'after_click.html'), 'w', encoding='utf-8') as f:
        f.write(page.content())
    with open(os.path.join(OUT_DIR, 'console_logs.json'), 'w', encoding='utf-8') as f:
        json.dump(logs, f, indent=2, ensure_ascii=False)

    context.close()
    browser.close()

print('done, outputs in', OUT_DIR)
