"""Mobile browser contract for the public payment form and its return states."""

import pytest
from playwright.sync_api import Browser, expect


@pytest.mark.e2e
def test_signup_checkout_success_and_cancel_states_render_on_mobile(browser: Browser, live_server):
    context = browser.new_context(viewport={"width": 390, "height": 844})
    page = context.new_page()
    try:
        for path, content_selector in (
            ("/checkout/?plan=monthly", ".checkout-form-card"),
            ("/checkout/sucesso/", ".checkout-result"),
            ("/checkout/cancelado/", ".checkout-result"),
        ):
            page.goto(f"{live_server.url}{path}")
            expect(page.locator(content_selector)).to_be_visible()
            expect(page.locator(".checkout-nav")).to_have_css("position", "static")
            expect(page.locator(".checkout-nav")).to_have_css("backdrop-filter", "none")
            assert page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth"), path
            if content_selector == ".checkout-result":
                expect(page.locator(".checkout-result")).to_have_css("backdrop-filter", "none")
    finally:
        context.close()
