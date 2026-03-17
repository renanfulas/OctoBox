from playwright.sync_api import sync_playwright
import json

BASE = "http://127.0.0.1:8000"
DASH = BASE + "/dashboard/"
OUT = "largest_elements_dashboard.json"
USER = "renan"
PASS = "abc"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
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

    # go to dashboard (redirects to login)
    page.goto(DASH, wait_until='domcontentloaded', timeout=30000)

    if page.locator('input[type="password"]').count():
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
        except Exception:
            pass

    page.goto(DASH, wait_until='load', timeout=30000)
    page.wait_for_timeout(1500)

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

    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print('Saved top elements to', OUT)
    browser.close()
