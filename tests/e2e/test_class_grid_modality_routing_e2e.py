from datetime import datetime, time, timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from playwright.sync_api import Page, expect

from operations.models import ClassSession, ClassType, WorkoutProgram
from operations.workout_program_catalog import ensure_default_workout_programs


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_calendar_requires_track_and_displays_parallel_modalities(page: Page, live_server, e2e_owner_credentials):
    ensure_default_workout_programs()
    actor = get_user_model().objects.get(username=e2e_owner_credentials['username'])
    crossfit = WorkoutProgram.objects.get(slug='crossfit')
    hyrox = WorkoutProgram.objects.get(slug='hyrox')

    page.goto(f'{live_server.url}/login/funcionario/')
    page.locator('#id_username').fill(e2e_owner_credentials['username'])
    page.locator('#id_password').fill(e2e_owner_credentials['password'])
    page.locator('button[type="submit"]').click()
    page.wait_for_url('**/operacao/**', timeout=15_000)
    page.goto(f'{live_server.url}/grade-aulas/')
    planner_program = page.locator('#planner-board select[name="workout_program"]')
    expect(planner_program).to_be_visible()
    expect(planner_program).to_have_value('')
    expect(planner_program).to_have_attribute('required', '')

    page.locator('[data-action="open-monthly-calendar"]').first.click()
    monthly_dialog = page.locator('#class-monthly-modal[open]')
    expect(monthly_dialog).to_be_visible()
    page.locator('#toggle-monthly-rotation').click()
    rotation_program = page.locator('#class-grid-weekend-rotation select[name="workout_program"]')
    expect(rotation_program).to_be_visible()
    expect(rotation_program).to_have_value('')
    expect(rotation_program).to_have_attribute('required', '')
    page.locator('#close-monthly-calendar').click()

    tomorrow = timezone.localdate() + timedelta(days=1)
    scheduled_at = timezone.make_aware(datetime.combine(tomorrow, time(19, 0)))
    for program, class_type in ((crossfit, ClassType.CROSS), (hyrox, ClassType.HYROX)):
        ClassSession.objects.create(
            title='Aula 19h',
            workout_program=program,
            class_type=class_type,
            coach=actor,
            scheduled_at=scheduled_at,
            duration_minutes=60,
            capacity=16,
        )

    page.reload()
    parallel_cards = page.locator('.weekly-session-chip').filter(has_text='Aula 19h')
    expect(parallel_cards).to_have_count(2)
    expect(parallel_cards.filter(has_text='CrossFit')).to_have_count(1)
    expect(parallel_cards.filter(has_text='HYROX')).to_have_count(1)


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_recurring_planner_skip_existing_control_is_mobile_friendly(page: Page, live_server, e2e_owner_credentials):
    page.set_viewport_size({'width': 390, 'height': 844})
    page.goto(f'{live_server.url}/login/funcionario/')
    page.locator('#id_username').fill(e2e_owner_credentials['username'])
    page.locator('#id_password').fill(e2e_owner_credentials['password'])
    page.locator('button[type="submit"]').click()
    page.wait_for_url('**/operacao/**', timeout=15_000)
    page.goto(f'{live_server.url}/grade-aulas/#planner-board')

    planner = page.locator('#planner-board')
    skip_row = planner.locator('.class-grid-checkbox')
    skip_checkbox = planner.locator('input[name="skip_existing"]')
    expect(skip_row).to_be_visible()
    expect(skip_row).to_contain_text('Pular aulas que já existirem nesse mesmo horário')
    expect(planner.locator('.class-grid-skip-existing__help')).to_contain_text(
        'mesma data e horário'
    )
    expect(skip_checkbox).to_be_checked()

    mobile_control = planner.locator('input:not([type="checkbox"]):not([type="hidden"]), select').first
    expect(mobile_control).to_be_visible()
    control_style = mobile_control.evaluate(
        '(element) => ({fontSize: getComputedStyle(element).fontSize, height: element.getBoundingClientRect().height})'
    )
    assert control_style['fontSize'] == '16px', control_style
    assert control_style['height'] >= 48, control_style

    row_box = skip_row.bounding_box()
    assert row_box is not None and row_box['height'] >= 48
    skip_row.click(position={'x': row_box['width'] - 12, 'y': row_box['height'] / 2})
    expect(skip_checkbox).not_to_be_checked()
    skip_row.click(position={'x': row_box['width'] - 12, 'y': row_box['height'] / 2})
    expect(skip_checkbox).to_be_checked()

    widths = page.evaluate(
        '({viewport: document.documentElement.clientWidth, content: document.documentElement.scrollWidth})'
    )
    assert widths['content'] <= widths['viewport'], widths
