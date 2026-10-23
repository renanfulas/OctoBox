"""Garante que o relatório extraído carrega nas páginas unificadas e legadas."""

import pytest
from django.test import override_settings
from playwright.sync_api import Page, expect

from tests.e2e.curva_login import sign_in_owner


@pytest.fixture(autouse=True)
def _cleanup(django_db_blocker):
    from public_workouts.models import PublicWorkoutAssessment, PublicWorkoutProgram

    def clear():
        PublicWorkoutAssessment.objects.filter(plan_slug__in=['bruno', 'rafael']).delete()
        PublicWorkoutProgram.objects.filter(slug='bruno').delete()

    with django_db_blocker.unblock():
        clear()
    yield
    with django_db_blocker.unblock():
        clear()


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
@override_settings(DEBUG=True)
def test_assessment_report_loads_after_split(page: Page, live_server):
    from public_workouts.schema import build_example_payload
    from public_workouts.services import publish_program, record_assessment

    publish_program(slug='bruno', payload=build_example_payload())
    record_assessment(
        plan_slug='bruno', measured_at='2026-09-01', weight_kg=70,
        measurements={'cintura': 80},
    )
    record_assessment(
        plan_slug='bruno', measured_at='2026-10-01', weight_kg=69,
        measurements={'cintura': 78},
    )

    sign_in_owner(page, live_server.url, 'bruno')
    response = page.goto(f'{live_server.url}/renan/bruno/preview')
    assert response.status == 200
    assert any(cookie['name'] == 'renan_slug' for cookie in page.context.cookies()), response.header_value('set-cookie')
    report_response = page.request.get(f'{live_server.url}/renan/bruno/avaliacoes.json')
    assert report_response.status == 200, report_response.text()
    page.locator('[data-workout-cycle-nav][data-cycle-key="avaliacao"]').click()
    panel = page.locator('#workout-panel-avaliacao')
    expect(panel.locator('#assess-form')).to_be_attached()
    expect(panel.locator('#assess-report-slot')).to_contain_text('Evolução de peso')
    expect(panel.locator('.assess-silhouette')).to_be_visible()


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
@override_settings(DEBUG=True)
def test_assessment_report_loads_on_legacy_page(page: Page, live_server):
    from public_workouts.services import record_assessment

    record_assessment(
        plan_slug='rafael', measured_at='2026-10-01', weight_kg=72,
        measurements={'cintura': 82},
    )
    sign_in_owner(page, live_server.url, 'rafael')
    page.goto(f'{live_server.url}/renan/rafael')
    expect(page.locator('#assess-form')).to_be_attached()
    expect(page.locator('#assess-report-slot')).to_contain_text('Cintura')
