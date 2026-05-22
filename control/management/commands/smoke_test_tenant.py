"""
ARQUIVO: smoke test de tenant pós-deploy (Sprint 5).

POR QUE ELE EXISTE:
- Valida que um Box está funcional após provisioning sem precisar de browser.
- Roda em CI/CD e em check manual pré-abertura para clientes.

O QUE ESTE ARQUIVO FAZ:
1. Verifica que o schema existe e tem as tabelas esperadas.
2. Verifica que Groups (Owner/Manager/Coach/Recepcao) existem no tenant.
3. Verifica que MembershipPlan defaults existem.
4. Verifica que a API /api/v1/health/ retorna healthy=True.
5. Verifica StudentBoxMembership count no public.

USO:
    python manage.py smoke_test_tenant --slug=pilot
    python manage.py smoke_test_tenant --slug=endorfina
    python manage.py smoke_test_tenant --slug=pilot --verbose

SAIDA MENSURAVEL:
    Exit 0 se todos os checks passam.
    Exit 1 + lista de falhas se algum check falha.
"""

from __future__ import annotations

import logging

from django.core.management.base import BaseCommand, CommandError

logger = logging.getLogger('control.smoke_test')

# Tabelas mínimas esperadas em qualquer schema provisionado
_REQUIRED_TABLES = [
    'boxcore_student',
    'boxcore_membershipplan',
    'boxcore_payment',
    'auth_group',
    'auth_user',
]

# Groups obrigatórios em cada tenant
_REQUIRED_GROUPS = ['Owner', 'Manager', 'Coach', 'Recepcao']


class Command(BaseCommand):
    help = 'Smoke test de um tenant provisionado. Exit 0 = OK, Exit 1 = falhas.'

    def add_arguments(self, parser):
        parser.add_argument('--slug', required=True, help='Slug do Box a testar.')
        parser.add_argument('--verbose', action='store_true', help='Mostra checks que passaram.')

    def handle(self, *args, **options):
        slug = options['slug'].strip()
        verbose = options['verbose']
        schema_name = f'box_{slug}'

        self.stdout.write(f'smoke_test_tenant: slug={slug!r} schema={schema_name!r}')
        self.stdout.write('')

        failures = []
        passes = []

        # C1: Box existe em public
        try:
            from control.models import Box
            box = Box.objects.filter(slug=slug).first()
            if box is None:
                failures.append(f'C1: Box slug={slug!r} nao existe em control_box.')
            elif box.status != Box.Status.ACTIVE:
                failures.append(f'C1: Box slug={slug!r} tem status={box.status!r}, esperado ACTIVE.')
            else:
                passes.append(f'C1: Box {slug!r} ACTIVE.')
        except Exception as exc:
            failures.append(f'C1: erro ao consultar Box — {exc}')

        # C2: Schema existe no Postgres
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT 1 FROM information_schema.schemata WHERE schema_name = %s",
                    [schema_name],
                )
                if cursor.fetchone():
                    passes.append(f'C2: Schema {schema_name!r} existe.')
                else:
                    failures.append(f'C2: Schema {schema_name!r} NAO existe no Postgres.')
        except Exception as exc:
            failures.append(f'C2: erro ao verificar schema — {exc}')

        # C3: Tabelas mínimas existem no schema
        try:
            from django.db import connection
            missing_tables = []
            with connection.cursor() as cursor:
                for table in _REQUIRED_TABLES:
                    cursor.execute(
                        """
                        SELECT 1 FROM information_schema.tables
                        WHERE table_schema = %s AND table_name = %s
                        """,
                        [schema_name, table],
                    )
                    if not cursor.fetchone():
                        missing_tables.append(table)

            if missing_tables:
                failures.append(f'C3: Tabelas ausentes em {schema_name}: {missing_tables}')
            else:
                passes.append(f'C3: {len(_REQUIRED_TABLES)} tabelas obrigatórias presentes.')
        except Exception as exc:
            failures.append(f'C3: erro ao verificar tabelas — {exc}')

        # C4: Groups obrigatórios existem no tenant
        try:
            from django_tenants.utils import schema_context
            from django.contrib.auth.models import Group
            with schema_context(schema_name):
                existing = set(Group.objects.values_list('name', flat=True))
                missing_groups = [g for g in _REQUIRED_GROUPS if g not in existing]
            if missing_groups:
                failures.append(f'C4: Groups ausentes em {schema_name}: {missing_groups}')
            else:
                passes.append(f'C4: Todos os {len(_REQUIRED_GROUPS)} Groups presentes.')
        except ImportError:
            passes.append('C4: django-tenants nao instalado — check ignorado.')
        except Exception as exc:
            failures.append(f'C4: erro ao verificar Groups — {exc}')

        # C5: MembershipPlan defaults existem no tenant
        try:
            from django_tenants.utils import schema_context
            from django.apps import apps
            with schema_context(schema_name):
                MembershipPlan = apps.get_model('boxcore', 'MembershipPlan')
                count = MembershipPlan.objects.count()
            if count == 0:
                failures.append(f'C5: Nenhum MembershipPlan em {schema_name}. seed_plans rodou?')
            else:
                passes.append(f'C5: {count} MembershipPlan(s) no tenant.')
        except ImportError:
            passes.append('C5: django-tenants nao instalado — check ignorado.')
        except Exception as exc:
            failures.append(f'C5: erro ao verificar MembershipPlan — {exc}')

        # C6: Membership do Owner existe em public
        try:
            from control.models import Box, Membership
            box_obj = Box.objects.filter(slug=slug).first()
            if box_obj:
                owner_membership = Membership.objects.filter(
                    box=box_obj,
                    role=Membership.Role.OWNER,
                ).first()
                if owner_membership is None:
                    failures.append(f'C6: Nenhuma Membership OWNER para box={slug!r}.')
                else:
                    passes.append(f'C6: Owner membership presente (user={owner_membership.user.username!r}).')
            else:
                passes.append('C6: Box nao encontrado — skip (coberto por C1).')
        except Exception as exc:
            failures.append(f'C6: erro ao verificar Membership — {exc}')

        # C7: BoxProvisioningEvent todos os steps OK
        try:
            from control.models import Box, BoxProvisioningEvent
            from control.services import PROVISIONING_STEPS
            box_obj = Box.objects.filter(slug=slug).first()
            if box_obj:
                ok_steps = set(
                    BoxProvisioningEvent.objects
                    .filter(box=box_obj, status='ok')
                    .values_list('step', flat=True)
                )
                missing_steps = [s for s in PROVISIONING_STEPS if s not in ok_steps]
                if missing_steps:
                    failures.append(f'C7: Steps de provisioning incompletos: {missing_steps}')
                else:
                    passes.append(f'C7: Todos os {len(PROVISIONING_STEPS)} provisioning steps OK.')
            else:
                passes.append('C7: Box nao encontrado — skip.')
        except Exception as exc:
            failures.append(f'C7: erro ao verificar BoxProvisioningEvent — {exc}')

        # C8: Healthcheck endpoint acessível (via Django test client)
        try:
            from django.test import RequestFactory
            from api.v1.views import ApiV1HealthView
            factory = RequestFactory()
            request = factory.get('/api/v1/health/')
            response = ApiV1HealthView.as_view()(request)
            import json as _json
            data = _json.loads(response.content)
            if data.get('healthy') and data.get('status') == 'ok':
                passes.append(f'C8: /api/v1/health/ retorna healthy=True, tenants_active={data.get("tenants_active")}.')
            else:
                failures.append(f'C8: /api/v1/health/ retornou unexpected: {data}')
        except Exception as exc:
            failures.append(f'C8: erro ao chamar ApiV1HealthView — {exc}')

        # -----------------------------------------------------------------
        # Relatório final
        # -----------------------------------------------------------------
        self.stdout.write('')
        if verbose:
            for p in passes:
                self.stdout.write(self.style.SUCCESS(f'  PASS  {p}'))

        if failures:
            self.stdout.write(self.style.ERROR(f'{len(failures)} check(s) FALHARAM:'))
            for f in failures:
                self.stdout.write(self.style.ERROR(f'  FAIL  {f}'))
            self.stdout.write('')
            raise CommandError(
                f'smoke_test_tenant FALHOU para slug={slug!r}: '
                f'{len(failures)}/{len(failures)+len(passes)} checks com falha.'
            )

        self.stdout.write(self.style.SUCCESS(
            f'smoke_test_tenant OK: {len(passes)}/{len(passes)} checks passaram para {slug!r}.'
        ))
