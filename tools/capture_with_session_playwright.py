import os
import json

# Prepare Django environment and create a session for the test user
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from django.contrib.auth import get_user_model
from django.contrib.sessions.backends.db import SessionStore
from django.utils import timezone

User = get_user_model()
user = User.objects.filter(username='autotest').first()
if not user:
    raise SystemExit('User autotest not found')

s = SessionStore()
s['_auth_user_id'] = str(user.pk)
s['_auth_user_backend'] = 'django.contrib.auth.backends.ModelBackend'
try:
    s['_auth_user_hash'] = user.get_session_auth_hash()
except Exception:
    s['_auth_user_hash'] = ''
s['django_timezone'] = str(timezone.get_current_timezone_name())
s.save()
session_key = s.session_key
print('created session', session_key)

# Now run Playwright with the created sessionid cookie
from playwright.sync_api import sync_playwright
BASE = os.environ.get('BASE_URL', 'http://127.0.0.1:8000')
OUT = 'playwright_capture_session'
os.makedirs(OUT, exist_ok=True)
logs = []
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(locale='pt-BR', user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64)')
    # inject session cookie
    cookie = {
        'name': 'sessionid',
        'value': session_key,
        'domain': '127.0.0.1',
        'path': '/',
        'httpOnly': True,
        'secure': False,
    }
    try:
        context.add_cookies([cookie])
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
            logs.append({'event': 'response', 'url': url, 'status': status, 'snippet': text[:1000]})

    page.on('console', on_console)
    page.on('pageerror', on_page_error)
    page.on('response', on_response)

    print('navigating to dashboard...')
    try:
        page.goto(f'{BASE}/dashboard/', timeout=30000)
    except Exception:
        pass

    # capture
    page.screenshot(path=os.path.join(OUT, 'dashboard.png'), full_page=True)
    with open(os.path.join(OUT, 'dashboard.html'), 'w', encoding='utf-8') as f:
        f.write(page.content())
    with open(os.path.join(OUT, 'console_logs.json'), 'w', encoding='utf-8') as f:
        json.dump(logs, f, indent=2, ensure_ascii=False)

    context.close()
    browser.close()

print('done, outputs in', OUT)
