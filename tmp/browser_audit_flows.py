import json
from pathlib import Path

from playwright.sync_api import sync_playwright


BASE_URL = "http://127.0.0.1:8000"
USERNAME = "qa_owner"
PASSWORD = "QaOwner!2026"
OUT_PATH = Path("tmp/browser_audit_report.json")


def record_basic_page_state(page):
    return page.evaluate(
        """() => ({
            url: window.location.pathname + window.location.search + window.location.hash,
            title: document.title,
            activePanels: Array.from(document.querySelectorAll('.is-tab-active, .is-active'))
                .map((node) => node.id || node.getAttribute('data-panel') || node.className)
                .slice(0, 20),
        })"""
    )


def login(page):
    page.goto(f"{BASE_URL}/login/", wait_until="networkidle")
    page.fill("#id_username", USERNAME)
    page.fill("#id_password", PASSWORD)
    page.click('[data-action="confirm-login"]')
    page.wait_for_load_state("networkidle")


def audit_dashboard(page, result):
    page.goto(f"{BASE_URL}/dashboard/", wait_until="networkidle")
    result["initial"] = record_basic_page_state(page)
    result["toolbar_present"] = page.locator("#toggle-dashboard-layout").count() > 0
    if result["toolbar_present"]:
        page.click("#toggle-dashboard-layout")
        page.wait_for_timeout(300)
        result["after_toggle"] = {
            "button_text": page.locator("#toggle-dashboard-layout").inner_text(),
            "reset_visible": page.locator("#reset-dashboard-layout").is_visible(),
            "status": page.locator("#dashboard-layout-status").inner_text(),
        }


def audit_students(page, result):
    page.goto(f"{BASE_URL}/alunos/", wait_until="networkidle")
    result["initial"] = record_basic_page_state(page)
    result["student_row_count"] = page.locator("[data-student-row]").count()
    result["open_tab_triggers"] = page.locator('[data-action^="open-tab-"]').evaluate_all(
        """nodes => nodes.map(node => ({
            action: node.getAttribute('data-action'),
            text: (node.textContent || '').trim(),
            targetExists: !!document.getElementById(node.getAttribute('data-action').replace('open-tab-', 'tab-'))
        }))"""
    )

    trigger_effects = []
    for idx in range(page.locator('[data-action^="open-tab-"]').count()):
        trigger = page.locator('[data-action^="open-tab-"]').nth(idx)
        action = trigger.get_attribute("data-action")
        before = record_basic_page_state(page)
        trigger.click()
        page.wait_for_timeout(250)
        after = record_basic_page_state(page)
        trigger_effects.append(
            {
                "action": action,
                "before_url": before["url"],
                "after_url": after["url"],
                "before_active": before["activePanels"],
                "after_active": after["activePanels"],
                "changed": before != after,
            }
        )
    result["trigger_effects"] = trigger_effects

    if result["student_row_count"] > 0:
        first_href = page.locator("[data-student-row]").first.get_attribute("data-href")
        page.locator("[data-student-row]").first.click()
        page.wait_for_load_state("networkidle")
        result["row_navigation"] = {
            "target_href": first_href,
            "final_url": page.evaluate("() => window.location.pathname + window.location.hash"),
        }


def audit_finance(page, result):
    page.goto(f"{BASE_URL}/financeiro/", wait_until="networkidle")
    result["initial"] = record_basic_page_state(page)
    cards = page.locator('[data-action^="open-tab-finance-"]')
    card_results = []
    for idx in range(cards.count()):
        card = cards.nth(idx)
        action = card.get_attribute("data-action")
        before = record_basic_page_state(page)
        card.click()
        page.wait_for_timeout(250)
        after = record_basic_page_state(page)
        card_results.append(
            {
                "action": action,
                "before_active": before["activePanels"],
                "after_active": after["activePanels"],
                "changed": before != after,
            }
        )
    result["trigger_effects"] = card_results


def audit_class_grid(page, result):
    page.goto(f"{BASE_URL}/grade-aulas/", wait_until="networkidle")
    result["initial"] = record_basic_page_state(page)
    result["monthly_trigger_present"] = page.locator("#open-monthly-calendar-preview").count() > 0
    result["weekly_head_present"] = page.locator('[data-action="open-weekly-modal-full"]').count() > 0
    result["weekly_day_count"] = page.locator("#weekly-board [data-day-date]").count()

    if result["monthly_trigger_present"]:
        page.click("#open-monthly-calendar-preview")
        page.wait_for_timeout(250)
        result["monthly_modal_open"] = page.locator("#class-monthly-modal").evaluate("node => node.open")
        page.click("#close-monthly-calendar")
        page.wait_for_timeout(250)
        result["monthly_modal_closed"] = not page.locator("#class-monthly-modal").evaluate("node => node.open")

    if result["weekly_head_present"]:
        page.click('[data-action="open-weekly-modal-full"]')
        page.wait_for_timeout(250)
        result["weekly_modal_full_open"] = page.locator("#class-weekly-modal").evaluate("node => node.open")
        page.click("#close-weekly-modal")
        page.wait_for_timeout(250)

    if result["weekly_day_count"] > 0:
        page.locator("#weekly-board [data-day-date]").first.click()
        page.wait_for_timeout(250)
        result["weekly_modal_day_open"] = {
            "open": page.locator("#class-weekly-modal").evaluate("node => node.open"),
            "title": page.locator("#class-weekly-modal-title").inner_text(),
        }
        page.click("#close-weekly-modal")
        page.wait_for_timeout(250)


def audit_reception(page, result):
    page.goto(f"{BASE_URL}/operacao/recepcao/", wait_until="networkidle")
    result["initial"] = record_basic_page_state(page)
    forms = page.locator('[data-action="manage-reception-payment"]')
    result["payment_form_count"] = forms.count()
    if forms.count() > 0:
        first_form = forms.first
        select = first_form.locator('[data-role="reception-payment-method"]')
        submit = first_form.locator('[data-role="reception-payment-submit"]')
        if select.count() and submit.count():
            before = submit.inner_text()
            select.select_option("pix")
            page.wait_for_timeout(200)
            after_pix = submit.inner_text()
            select.select_option(label="Dinheiro") if select.locator('option[label="Dinheiro"]').count() else None
            page.wait_for_timeout(200)
            after_second = submit.inner_text()
            result["submit_label_switch"] = {
                "before": before,
                "after_pix": after_pix,
                "after_second": after_second,
            }


def main():
    report = {"flows": {}, "console": [], "page_errors": []}

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        page.on("console", lambda msg: report["console"].append({"type": msg.type, "text": msg.text}))
        page.on("pageerror", lambda err: report["page_errors"].append(str(err)))

        login(page)

        flows = {
            "dashboard": audit_dashboard,
            "students": audit_students,
            "finance": audit_finance,
            "class_grid": audit_class_grid,
            "reception": audit_reception,
        }

        for key, fn in flows.items():
            flow_result = {}
            try:
                fn(page, flow_result)
                flow_result["status"] = "ok"
            except Exception as exc:
                flow_result["status"] = "error"
                flow_result["error"] = repr(exc)
            report["flows"][key] = flow_result

        browser.close()

    OUT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(OUT_PATH.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
