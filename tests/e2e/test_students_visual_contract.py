from pathlib import Path

import pytest
from playwright.sync_api import Page, expect, sync_playwright


VIEWPORTS = {
    "desktop": {"width": 1440, "height": 1100},
    "mobile": {"width": 390, "height": 844},
}

THEMES = ("light", "dark")


@pytest.fixture(scope="session")
def students_visual_credentials(test_tenant, django_db_blocker):
    if test_tenant is None:
        pytest.skip("students visual E2E requires django-tenants/PostgreSQL test tenant")

    username = "__students_visual_owner__"
    password = "Students-visual-456"

    with django_db_blocker.unblock():
        from django.contrib.auth import get_user_model
        from django.contrib.auth.models import Group
        from django.core.management import call_command

        from access.roles import ROLE_OWNER
        from control.models import Membership

        call_command("bootstrap_roles", verbosity=0)

        User = get_user_model()
        user, _ = User.objects.get_or_create(
            username=username,
            defaults={"email": "students-visual-owner@example.test"},
        )
        user.set_password(password)
        user.save()

        try:
            user.groups.add(Group.objects.get(name=ROLE_OWNER))
        except Group.DoesNotExist:
            pass

        Membership.objects.get_or_create(
            user=user,
            box=test_tenant,
            defaults={
                "role": Membership.Role.OWNER,
                "is_primary_box": True,
            },
        )

    return {"username": username, "password": password}


def _login(page: Page, base_url: str, credentials: dict[str, str]) -> None:
    page.goto(f"{base_url}/login/funcionario/")
    page.locator("#id_username").fill(credentials["username"])
    page.locator("#id_password").fill(credentials["password"])
    page.locator('button[type="submit"]').click()
    page.wait_for_url("**/operacao/**", timeout=15_000)


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("viewport_name,viewport", VIEWPORTS.items())
@pytest.mark.parametrize("theme", THEMES)
def test_students_page_visual_baseline_contract(
    live_server,
    students_visual_credentials,
    viewport_name: str,
    viewport: dict[str, int],
    theme: str,
):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(viewport=viewport)
        page = context.new_page()

        _login(page, live_server.url, students_visual_credentials)

        page.evaluate(
            """theme => {
                window.localStorage.setItem("octobox-theme", theme);
                document.body.dataset.theme = theme;
            }""",
            theme,
        )
        page.goto(f"{live_server.url}/alunos/")
        page.wait_for_load_state("networkidle")

        expect(page.locator('body[data-theme="%s"]' % theme)).to_be_visible()

        hero = page.locator('[data-panel="students-hero"]')
        expect(hero).to_be_visible()
        assert "hero--system" in hero.get_attribute("class")
        assert "hero--command" in hero.get_attribute("class")
        assert "operation-hero" in hero.get_attribute("class")
        assert "student-hero" in hero.get_attribute("class")

        kpi_grid = page.locator(".kpi-command-grid.student-kpi-grid")
        expect(kpi_grid).to_be_visible()
        expect(page.locator(".kpi-command-card.student-kpi-card")).to_have_count(4)

        first_kpi = page.locator(".kpi-command-card").first
        expect(first_kpi).to_be_visible()
        assert first_kpi.get_attribute("data-panel") == "metric-card"

        expect(page.locator(".operation-hero-action-rail .button").first).to_be_visible()

        active_directory_panel = page.locator(
            ".students-tab-panel--directory.is-tab-active"
        ).first
        directory_trigger = page.locator('[data-target-panel="tab-students-directory"]').first
        if active_directory_panel.count() == 0 and directory_trigger.count():
            directory_trigger.click()
            page.wait_for_timeout(250)

        expect(active_directory_panel).to_be_visible()
        assert page.locator(".students-tab-surface").count() >= 2
        expect(page.locator(".student-directory-table")).to_be_visible()

        overflow = page.evaluate(
            "() => Math.max(0, document.documentElement.scrollWidth - document.documentElement.clientWidth)"
        )
        assert overflow <= 1

        screenshot_dir = Path("tmp") / "visual_contract" / "students"
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=screenshot_dir / f"students-{viewport_name}-{theme}.png", full_page=True)

        context.close()
        browser.close()
