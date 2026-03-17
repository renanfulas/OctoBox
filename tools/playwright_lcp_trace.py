from playwright.sync_api import sync_playwright
import json

URL = "http://127.0.0.1:8000"
TRACE_PATH = "trace.zip"
LCP_JSON = "lcp.json"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()

    context.tracing.start(screenshots=True, snapshots=True, sources=True)

    # Inject a PerformanceObserver early to capture LCP entries reliably
    page.add_init_script("""() => {
        window.__lcp = [];
        try {
            new PerformanceObserver((list) => {
                for (const entry of list.getEntries()) {
                    window.__lcp.push({
                        renderTime: entry.renderTime || entry.startTime,
                        size: entry.size || null,
                        url: entry.url || null,
                        element: entry.element ? entry.element.tagName : null
                    });
                }
            }).observe({type: 'largest-contentful-paint', buffered: true});
        } catch (e) {
            window.__lcp_error = String(e);
        }
    }""")

    page.goto(URL, wait_until="load", timeout=60000)
    page.wait_for_timeout(2500)

    # Read captured LCP entries from the page global
    lcp = page.evaluate("""() => {
        try {
            return window.__lcp || [];
        } catch (err) {
            return {error: String(err)};
        }
    }""")

    context.tracing.stop(path=TRACE_PATH)

    with open(LCP_JSON, "w", encoding="utf-8") as f:
        json.dump(lcp, f, ensure_ascii=False, indent=2)

    print(f"Saved trace to {TRACE_PATH} and LCP entries to {LCP_JSON}")
    browser.close()
