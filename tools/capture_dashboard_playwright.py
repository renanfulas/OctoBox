from playwright.sync_api import sync_playwright
import os
import json
import requests

BASE = os.environ.get('BASE_URL', 'http://127.0.0.1:8000')
USER = os.environ.get('AUTO_USER', 'autotest')
PASS = os.environ.get('AUTO_PASS', 'Aut0Test!')
OUT_DIR = 'playwright_capture'

os.makedirs(OUT_DIR, exist_ok=True)
logs = []

# Try to login via requests first and transfer cookies to Playwright
session = requests.Session()
login_get = session.get(f"{BASE}/login/")
csrf = None
if 'csrfmiddlewaretoken' in login_get.text:
    import re
    m = re.search(r'name="csrfmiddlewaretoken" value="([^\"]+)"', login_get.text)
    if m:
        csrf = m.group(1)

login_data = {'username': USER, 'password': PASS}
if csrf:
    login_data['csrfmiddlewaretoken'] = csrf

resp = session.post(f"{BASE}/login/?next=/dashboard/", data=login_data, headers={'Referer': f"{BASE}/login/"}, allow_redirects=False)
logged_via_requests = resp.status_code in (200, 302)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36', locale='pt-BR')
    # transfer cookies from requests session
    try:
        cookies = []
        for c in session.cookies:
            cookies.append({
                'name': c.name,
                'value': c.value,
                'domain': c.domain,
                'path': c.path,
                'httpOnly': c._rest.get('HttpOnly', False) if hasattr(c, '_rest') else False,
            })
        # Playwright expects cookie 'url' or domain; use url method for simplicity
        for c in cookies:
            c['url'] = BASE
        context.add_cookies(cookies)
    except Exception:
        pass

    page = context.new_page()

    def on_console(msg):
        try:
            loc = msg.location
        except Exception:
            loc = None
        logs.append({'event': 'console', 'type': msg.type, 'text': msg.text, 'location': loc})

    def on_page_error(err):
        logs.append({'event': 'pageerror', 'error': str(err)})

    def on_request_failed(request):
        failure = request.failure
        logs.append({'event': 'requestfailed', 'url': request.url, 'failure': str(failure)})

    def on_response(response):
        try:
            status = response.status
        except Exception:
            status = None
        try:
            url = response.url
        except Exception:
            url = ''
        # log responses for key paths to aid debugging
        if url and any(p in url for p in ['/login', '/dashboard', '/operacao', '/api/']):
            try:
                text = response.text()
            except Exception:
                text = ''
            logs.append({'event': 'response', 'url': url, 'status': status, 'text_snippet': text[:1000]})

    page.on('console', on_console)
    page.on('pageerror', on_page_error)
    page.on('requestfailed', on_request_failed)
    page.on('response', on_response)

    print('navigating to login...')
    page.goto(f'{BASE}/login/', timeout=60000)

    print('filling credentials...')
    page.fill('input[name="username"]', USER)
    page.fill('input[name="password"]', PASS)

    # submit and wait for either dashboard or error
    page.click('button[type="submit"]')

    try:
        page.wait_for_url(f'{BASE}/dashboard/', timeout=15000)
        print('dashboard loaded')
    except Exception:
        print('dashboard not reached, capturing current page')

    # capture screenshot and HTML
    screenshot_path = os.path.join(OUT_DIR, 'dashboard.png')
    page.screenshot(path=screenshot_path, full_page=True)

    html = page.content()
    with open(os.path.join(OUT_DIR, 'dashboard.html'), 'w', encoding='utf-8') as f:
        f.write(html)

    # write logs
    with open(os.path.join(OUT_DIR, 'console_logs.json'), 'w', encoding='utf-8') as f:
        json.dump(logs, f, indent=2, ensure_ascii=False)

    context.close()
    browser.close()

print('capture complete, outputs in', OUT_DIR)
