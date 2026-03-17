from playwright.sync_api import sync_playwright
import json

URL = "http://127.0.0.1:8000"
OUT = "largest_elements.json"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context(viewport={'width':1280,'height':800})
    page = context.new_page()
    page.goto(URL, wait_until='load', timeout=60000)
    page.wait_for_timeout(1000)

    data = page.evaluate(r"""() => {
        function isVisible(el){
            if(!el) return false;
            const style = getComputedStyle(el);
            if(style && (style.visibility==='hidden' || style.display==='none' || parseFloat(style.opacity)===0)) return false;
            const rect = el.getBoundingClientRect();
            if(rect.width===0 || rect.height===0) return false;
            const vw = Math.max(document.documentElement.clientWidth || 0, window.innerWidth || 0);
            const vh = Math.max(document.documentElement.clientHeight || 0, window.innerHeight || 0);
            // check if element is inside viewport
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

    print(f'Saved top elements to {OUT}')
    browser.close()
