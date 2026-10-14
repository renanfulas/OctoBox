"""Contrato de navegador da calculadora de anilhas separada do load tracker."""

import pytest
from django.test import override_settings
from playwright.sync_api import Page, expect


_MOVEMENT_SLUG = 'curva-e2e-plate-squat'


@pytest.fixture(autouse=True)
def _cleanup_plate_calculator_e2e(django_db_blocker):
    from public_workouts.models import PublicWorkoutMovement, PublicWorkoutProgram

    def cleanup():
        PublicWorkoutProgram.objects.filter(slug='bruno').delete()
        PublicWorkoutMovement.objects.filter(slug=_MOVEMENT_SLUG).delete()

    with django_db_blocker.unblock():
        cleanup()
    yield
    with django_db_blocker.unblock():
        cleanup()


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
@override_settings(DEBUG=True)
def test_plate_calculator_applies_weight_only_to_draft(page: Page, live_server):
    from public_workouts.models import PublicWorkoutMovement, PublicWorkoutMovementEquipment
    from public_workouts.schema import build_example_payload
    from public_workouts.services import publish_program

    PublicWorkoutMovement.objects.create(
        slug=_MOVEMENT_SLUG, label_pt='Agachamento com barra',
        equipment_type=PublicWorkoutMovementEquipment.BARBELL,
        logged_weight_includes_bar=True,
    )
    payload = build_example_payload()
    payload['program_id'] = 'curva-e2e-plate-calculator'
    payload['days'][0]['blocks'][0]['movements'][0]['movement_slug'] = _MOVEMENT_SLUG
    publish_program(slug='bruno', payload=payload)

    page.goto(f'{live_server.url}/renan/bruno/preview-b3')
    page.locator('[data-workout-cycle-nav][data-cycle-key="treino"]').click()
    page.locator('[data-workout-load-toggle]').click()
    widget = page.locator('[data-workout-load-input]')
    expect(widget).to_be_visible()
    calculator = widget.locator('[data-workout-plate-calculator]')
    expect(calculator).to_be_visible()

    weight = widget.locator('[data-workout-load-field]')
    weight.fill('50')
    calculator.locator('summary').click()
    expect(calculator.locator('[data-plate-target-display]')).to_have_text('50')
    calculator.locator('[data-plate-target-step="2.5"]').click()
    expect(calculator.locator('[data-plate-target-display]')).to_have_text('52,5')
    expect(calculator.locator('[data-plate-result]')).to_contain_text('De cada lado:')
    calculator.locator('[data-plate-use-total]').click()

    expect(weight).to_have_value('52.5')
    expect(weight).to_have_attribute('data-dirty', '1')
    expect(widget.locator('[data-workout-load-status]')).to_be_empty()

    page.wait_for_timeout(750)  # debounce do rascunho local
    page.reload()
    page.locator('[data-workout-cycle-nav][data-cycle-key="treino"]').click()
    page.locator('[data-workout-load-toggle]').click()
    widget = page.locator('[data-workout-load-input]')
    expect(widget.locator('[data-workout-load-field]')).to_have_value('52.5')
    expect(widget.locator('[data-workout-load-status]')).to_contain_text('Rascunho neste aparelho')
