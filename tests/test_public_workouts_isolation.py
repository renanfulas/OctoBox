"""
ARQUIVO: testes de isolamento entre o corredor de treinos e o SaaS de box
(Categoria 5 do R.T, docs/plans/public-workouts-produtizacao-corda.md).

POR QUE ELE EXISTE:
- provam que a regra D.00 continua valendo: sao regressao de ARQUITETURA,
  quebram quando alguem religa o acoplamento que as Ondas B0/B1/B2
  deliberadamente evitaram — nao quando "algo para de funcionar".

Este arquivo cresce a cada onda que o CORDA entrega. V1 (movimento pending
nao aparece no picker do coach) ja tinha teste proprio desde a Onda A0
(`public_workouts/test_extract_movements.py::test_extraction_never_touches_student_app_movement_library`)
— nao duplicado aqui. V2 (template) entra abaixo, agora que A1/A2 publicaram
de verdade.
"""

from datetime import date
from decimal import Decimal

from django.test import TestCase

from finance.model_definitions import Payment as BoxPayment
from public_workouts.billing import create_payment_with_notice_schedule
from public_workouts.models import (
    PublicWorkoutAccount,
    PublicWorkoutMealPlan,
    PublicWorkoutNutritionProfile,
    PublicWorkoutProfessional,
    PublicWorkoutSubscription,
)
from public_workouts.schema import build_example_payload
from public_workouts.services import publish_program
from student_identity.models import StudentAppInvitation
from student_identity.public_workout_login import request_login_token


class PublicWorkoutsIsolationTests(TestCase):
    def test_charging_consultancy_does_not_create_a_finance_payment_row(self):
        # V3 do CORDA: cobranca de consultoria nunca entra no financeiro do box.
        before = BoxPayment.objects.count()

        account = PublicWorkoutAccount.objects.create(email='isolamento@example.com')
        subscription = PublicWorkoutSubscription.objects.create(account=account, plan_slug='giovanna')
        create_payment_with_notice_schedule(
            subscription=subscription, due_date=date(2026, 3, 10), gross_amount=Decimal('89.90')
        )

        self.assertEqual(BoxPayment.objects.count(), before)

    def test_login_of_training_account_does_not_create_a_student_app_invitation(self):
        # V5 do CORDA: PublicWorkoutLoginToken e proprio, nunca StudentAppInvitation.
        before = StudentAppInvitation.objects.count()

        request_login_token(email='semconvite@example.com', base_url='https://octoboxfit.com.br')

        self.assertEqual(StudentAppInvitation.objects.count(), before)

    def test_publishing_a_program_does_not_create_an_operations_workout_template(self):
        # V2 do CORDA: publicar PublicWorkoutProgram nunca escreve em
        # WorkoutTemplate (operations, TENANT_APP) — o corredor de
        # consultoria nao "e" o WOD do box, mesmo os dois falando de treino.
        from operations.model_definitions import WorkoutTemplate

        before = WorkoutTemplate.objects.count()

        publish_program(slug='giovanna', payload=build_example_payload())

        self.assertEqual(WorkoutTemplate.objects.count(), before)

    def test_corridor_billing_module_does_not_import_stripe_router_or_services(self):
        # N2/S3 do CORDA: o corredor nunca importa o roteador nem os
        # servicos do box — teria endpoint/checkout proprios quando a
        # Onda B2 (Slice B) chegar. Checagem estatica: nenhum modulo do
        # corredor referencia integrations.stripe.router/services no
        # texto-fonte.
        import ast
        import pathlib

        corridor_files = list(pathlib.Path('public_workouts').rglob('*.py'))
        offending = []
        for path in corridor_files:
            tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
            for node in ast.walk(tree):
                module = None
                if isinstance(node, ast.ImportFrom) and node.module:
                    module = node.module
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.startswith('integrations.stripe'):
                            offending.append(f'{path}: import {alias.name}')
                if module and module.startswith('integrations.stripe.router'):
                    offending.append(f'{path}: from {module} import ...')
                if module and module.startswith('integrations.stripe.services'):
                    offending.append(f'{path}: from {module} import ...')

        self.assertEqual(offending, [], f'corredor importando stripe do box: {offending}')

    def test_nutrition_models_have_no_foreign_key_outside_public_workouts(self):
        # Entrega 6, Fase 4 (D.00, guardrails operacionais): PublicWorkoutProfessional
        # nao referencia StudentIdentity nem nenhum outro model do box —
        # so' entra num vinculo com Box/conta Connect no dia em que o
        # multi-personal chegar de verdade (D.5).
        offending = []
        for model in (PublicWorkoutProfessional, PublicWorkoutNutritionProfile, PublicWorkoutMealPlan):
            for field in model._meta.get_fields():
                related_model = getattr(field, 'related_model', None)
                if related_model is None:
                    continue
                if related_model._meta.app_label != 'public_workouts':
                    offending.append(f'{model.__name__}.{field.name} -> {related_model._meta.app_label}.{related_model.__name__}')

        self.assertEqual(offending, [], f'modelo de nutricao com FK fora de public_workouts: {offending}')
