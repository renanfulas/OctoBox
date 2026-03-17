from playwright.sync_api import sync_playwright
from pathlib import Path

URL = 'http://127.0.0.1:8000/dashboard/'
OUT_HTML = 'debug_login_page.html'

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()
    page.goto(URL, wait_until='domcontentloaded', timeout=30000)
    page.wait_for_timeout(1000)
    info = {
        'url': page.url,
        'has_password': bool(page.locator('input[type="password"]').count()),
        'has_username': bool(page.locator('input[name="username"]').count() or page.locator('input[id*="user"]').count())
    }
    html = page.content()
    Path(OUT_HTML).write_text(html, encoding='utf-8')
    print(info)
    browser.close()
