"""Contrato E2E do editor nutricional usado pela profissional."""

import json

import pytest
from django.contrib.auth import get_user_model
from django.conf import settings
from django.test import Client
from django.urls import reverse
from playwright.sync_api import Page, expect

from public_workouts.models import (
    PublicWorkoutAccount,
    PublicWorkoutMealPlan,
    PublicWorkoutProfessional,
    PublicWorkoutProfessionalRole,
)


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_nutritionist_builds_and_publishes_plan_without_editing_json(page: Page, live_server):
    password = 'E2E-nutrition-strong-456'
    user = get_user_model().objects.create_superuser(
        username='__e2e_nutrition_admin__',
        email='nutrition-admin@example.test',
        password=password,
    )
    account = PublicWorkoutAccount.objects.create(email='nutrition-student@example.test')
    professional = PublicWorkoutProfessional.objects.create(
        name='Nutricionista E2E',
        role=PublicWorkoutProfessionalRole.NUTRICAO,
        registration_council='CRN',
        registration_number='E2E-1',
    )
    try:
        auth_client = Client()
        auth_client.force_login(user)
        page.context.add_cookies([{
            'name': settings.SESSION_COOKIE_NAME,
            'value': auth_client.cookies[settings.SESSION_COOKIE_NAME].value,
            'url': live_server.url,
        }])

        page.goto(f'{live_server.url}{reverse("admin:public_workouts_publicworkoutmealplan_add")}')
        editor = page.locator('[data-nutrition-editor]')
        expect(editor).to_be_visible()
        expect(editor.locator('[data-nutrition-targets] input')).to_have_count(4)

        target_values = ['2400', '180', '260', '70']
        for field, value in zip(editor.locator('[data-nutrition-targets] input').all(), target_values):
            field.fill(value)

        editor.locator('[data-add-meal]').click()
        meal = editor.locator('.nutrition-editor__meal')
        expect(meal).to_be_visible()
        meal.locator('input[data-key="label"]').fill('Café da manhã')
        meal.locator('input[data-key="time"]').fill('07:00')
        meal.locator('input[data-key="food"]').first.fill('Ovo inteiro')
        meal.locator('input[data-key="quantity"]').first.fill('3 unidades')
        for key, value in (
            ('kcal', '210'), ('protein_g', '18'), ('carbs_g', '1.5'), ('fat_g', '15'),
        ):
            meal.locator(f'input[data-key="{key}"]').fill(value)

        payload = json.loads(page.locator('#id_payload').input_value())
        assert payload['daily_targets']['kcal'] == 2400
        assert payload['meals'][0]['items'][0]['food'] == 'Ovo inteiro'

        page.locator('#id_account').select_option(str(account.pk))
        page.locator('#id_authored_by').select_option(str(professional.pk))
        page.locator('input[name="_save"]').click()
        page.wait_for_url('**/publicworkoutmealplan/')

        plan = PublicWorkoutMealPlan.objects.get(account=account)
        assert plan.is_active is True
        assert plan.payload['meals'][0]['label'] == 'Café da manhã'
        expect(page.locator('body')).not_to_have_text('Server Error')
    finally:
        PublicWorkoutMealPlan.objects.filter(account=account).delete()
        account.delete()
        professional.delete()
        user.delete()
