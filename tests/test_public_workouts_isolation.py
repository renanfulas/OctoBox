"""
ARQUIVO: testes de isolamento entre o corredor de treinos e o SaaS de box
(Categoria 5 do R.T, docs/plans/public-workouts-produtizacao-corda.md).

POR QUE ELE EXISTE:
- provam que a regra D.00 continua valendo: sao regressao de ARQUITETURA,
  quebram quando alguem religa o acoplamento que as Ondas B0/B1/B2
  deliberadamente evitaram — nao quando "algo para de funcionar".

Este arquivo cresce a cada onda que o CORDA entrega. As checagens abaixo
cobrem o que ja existe (B0/B1/B2 slice A); os itens de V1/V2 (movimento e
template) entram quando a Frente A publicar A0/A1.
"""

from datetime import date
from decimal import Decimal

from django.test import TestCase

from finance.model_definitions import Payment as BoxPayment
from public_workouts.billing import create_payment_with_notice_schedule
from public_workouts.models import PublicWorkoutSubscription
from student_identity.models import PublicWorkoutAccount, StudentAppInvitation
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
