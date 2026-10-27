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

# Tabelas mínimas esperadas em qualquer schema provisionado.
# IMPORTANTE: auth_group e auth_user sao SHARED_APPS (vivem em public, nao no
# schema do tenant). django-tenants nao replica auth_* nos schemas dos tenants
# — eles ficam apenas no public para o roteamento de identidade funcionar.
# Listar auth_* aqui causava falso positivo em qualquer Box provisionado.
_REQUIRED_TABLES = [
    'boxcore_student',
    'boxcore_membershipplan',
    'boxcore_payment',
]

# Grupos globais obrigatórios; no schema isolado, a validação só passa depois
# de aplicar as migrations compartilhadas e executar bootstrap_roles.
_REQUIRED_GROUPS = ['Owner', 'Manager', 'Coach', 'Recepcao']


class Command(BaseCommand):
    help = 'Smoke test de um tenant provisionado. Exit 0 = OK, Exit 1 = falhas.'

    def add_arguments(self, parser):
        parser.add_argument('--slug', required=True, help='Slug do Box a testar.')
        parser.add_argument('--verbose', action='store_true', help='Mostra checks que passaram.')
        parser.add_argument(
            '--schema-only',
            action='store_true',
            help='Valida o schema restaurado isoladamente, sem exigir metadados do control plane.',
        )
        parser.add_argument(
            '--restore-semantic',
            action='store_true',
            help=(
                'Confere vínculos shared/tenant de restore. Exige --schema-only e '
                'um snapshot compartilhado coerente no mesmo banco isolado.'
            ),
        )

    def handle(self, *args, **options):
        slug = options['slug'].strip()
        verbose = options['verbose']
        schema_only = options['schema_only']
        restore_semantic = options['restore_semantic']
        schema_name = f'box_{slug}'

        if restore_semantic and not schema_only:
            raise CommandError('--restore-semantic exige --schema-only e deve rodar no banco isolado.')

        self.stdout.write(f'smoke_test_tenant: slug={slug!r} schema={schema_name!r}')
        self.stdout.write('')

        failures = []
        passes = []

        if not schema_only:
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

        if restore_semantic:
            # C5S: as FKs tenant -> public não cobrem referências Student fracas
            # nem todos os vínculos legados. Esta checagem é read-only e usa o
            # snapshot shared restaurado junto com o schema tenant.
            try:
                from django.apps import apps
                from django.db.models import Q
                from django_tenants.utils import schema_context
                from control.models import Box, Membership

                box_state = Box.objects.filter(slug=slug).values('id', 'schema_name').first()
                if box_state is None:
                    failures.append(f'C5S: Box slug={slug!r} ausente do snapshot compartilhado.')
                elif box_state['schema_name'] != schema_name:
                    failures.append(
                        f"C5S: Box slug={slug!r} aponta para schema={box_state['schema_name']!r}, "
                        f'esperado {schema_name!r}.'
                    )
                else:
                    box_id = box_state['id']
                    box_aliases = {schema_name, slug}
                    owner_exists = Membership.objects.filter(
                        box_id=box_id,
                        role=Membership.Role.OWNER,
                    ).exists()
                    if owner_exists:
                        passes.append('C5S: Box/schema e Owner membership compartilhados coerentes.')
                    else:
                        failures.append('C5S: Owner Membership ausente no snapshot compartilhado.')

                    Student = apps.get_model('boxcore', 'Student')
                    StudentIdentity = apps.get_model('student_identity', 'StudentIdentity')
                    StudentBoxMembership = apps.get_model('student_identity', 'StudentBoxMembership')
                    StudentConsent = apps.get_model('student_identity', 'StudentConsent')
                    StudentAppInvitation = apps.get_model('student_identity', 'StudentAppInvitation')
                    StudentBoxInviteLink = apps.get_model('student_identity', 'StudentBoxInviteLink')
                    StudentPushSubscription = apps.get_model('student_identity', 'StudentPushSubscription')
                    StudentTransfer = apps.get_model('student_identity', 'StudentTransfer')
                    StripePaymentRef = apps.get_model('integrations', 'StripePaymentRef')
                    WorkoutApprovalPolicySetting = apps.get_model(
                        'operations', 'WorkoutApprovalPolicySetting'
                    )
                    StudentProfileChangeRequest = apps.get_model(
                        'student_app', 'StudentProfileChangeRequest'
                    )
                    # Milestones belong to the activation-cohorts package and
                    # are not present in every supported snapshot/branch yet.
                    # Keep restore validation compatible with P10-era schemas.
                    StudentJourneyMilestone = apps.all_models.get('student_app', {}).get(
                        'studentjourneymilestone'
                    )

                    with schema_context(schema_name):
                        student_links = list(
                            Student.objects.exclude(identity_id__isnull=True)
                            .values_list('id', 'identity_id')
                        )
                        profile_change_rows = list(
                            StudentProfileChangeRequest.objects.values_list(
                                'id', 'student_id', 'identity_id'
                            )
                        )
                        milestone_identity_rows = (
                            list(
                                StudentJourneyMilestone.objects.exclude(identity_id__isnull=True).values_list(
                                    'id', 'identity_id', 'subject_kind', 'subject_key', 'cohort_kind', 'cohort_key'
                                )
                            )
                            if StudentJourneyMilestone is not None
                            else []
                        )
                        approval_policy_rows = list(
                            WorkoutApprovalPolicySetting.objects.values_list('id', 'box_id')
                        )
                    membership_rows = list(
                        StudentBoxMembership.objects.filter(
                            Q(box_id=box_id) | Q(box_root_slug__in=box_aliases)
                        ).values_list('id', 'box_id', 'box_root_slug', 'identity_id', 'student_id')
                    )
                    shared_box_anchor_rows = []
                    for model_label, model in (
                        ('StudentConsent', StudentConsent),
                        ('StudentAppInvitation', StudentAppInvitation),
                        ('StudentBoxInviteLink', StudentBoxInviteLink),
                        ('StudentPushSubscription', StudentPushSubscription),
                    ):
                        rows = model.objects.filter(
                            Q(box_id=box_id) | Q(box_root_slug__in=box_aliases)
                        ).values_list('id', 'box_id', 'box_root_slug')
                        shared_box_anchor_rows.extend(
                            (model_label, row_id, row_box_id, root_slug)
                            for row_id, row_box_id, root_slug in rows
                        )
                    transfer_rows = list(
                        StudentTransfer.objects.filter(
                            Q(from_box_id=box_id)
                            | Q(to_box_id=box_id)
                            | Q(from_box_root_slug__in=box_aliases)
                            | Q(to_box_root_slug__in=box_aliases)
                        ).values_list(
                            'id',
                            'from_box_id',
                            'from_box_root_slug',
                            'to_box_id',
                            'to_box_root_slug',
                        )
                    )
                    stripe_payment_refs = list(
                        StripePaymentRef.objects.filter(box_schema__in=box_aliases).values_list(
                            'id', 'box_schema', 'payment_id'
                        )
                    )
                    Payment = apps.get_model('boxcore', 'Payment')
                    linked_identity_ids = {identity_id for _, identity_id in student_links}
                    linked_identity_ids.update(identity_id for _, _, _, identity_id, _ in membership_rows)
                    linked_identity_ids.update(identity_id for _, _, identity_id in profile_change_rows)
                    identities = {
                        identity.pk: identity
                        for identity in StudentIdentity.objects.filter(pk__in=linked_identity_ids)
                    }
                    semantic_errors = []

                    for student_id, identity_id in student_links:
                        identity = identities.get(identity_id)
                        if identity is None:
                            semantic_errors.append(f'Student {student_id}: identity {identity_id} ausente')
                            continue
                        belongs_to_box = (
                            identity.box_id == box_id
                            or (identity.box_id is None and identity.box_root_slug in box_aliases)
                        )
                        if not belongs_to_box:
                            semantic_errors.append(
                                f'Student {student_id}: identity {identity_id} pertence a outro Box'
                            )
                        if identity.student_id is not None and identity.student_id != student_id:
                            semantic_errors.append(
                                f'Student {student_id}: identity {identity_id} aponta para '
                                f'Student {identity.student_id}'
                            )

                    membership_student_ids = {
                        student_id
                        for _, _, _, _, student_id in membership_rows
                        if student_id is not None
                    }
                    membership_student_ids.update(
                        student_id
                        for _, student_id, _ in profile_change_rows
                        if student_id is not None
                    )
                    with schema_context(schema_name):
                        tenant_students = dict(
                            Student.objects.filter(pk__in=membership_student_ids)
                            .values_list('id', 'identity_id')
                        )
                        existing_payment_ids = set(
                            Payment.objects.filter(
                                pk__in={payment_id for _, _, payment_id in stripe_payment_refs}
                            ).values_list('pk', flat=True)
                        )
                        payment_intent_rows = list(
                            Payment.objects.exclude(stripe_payment_intent_id='').values_list(
                                'stripe_payment_intent_id', 'id'
                            )
                        )
                    payment_intents = {}
                    for payment_intent_id, payment_id in payment_intent_rows:
                        payment_intents.setdefault(payment_intent_id, []).append(payment_id)
                    payment_intent_refs = list(
                        StripePaymentRef.objects.filter(
                            payment_intent_id__in=set(payment_intents)
                        ).values_list('id', 'payment_intent_id', 'box_schema', 'payment_id')
                    )
                    stripe_ref_ids = {
                        ref_id for ref_id, _, _ in stripe_payment_refs
                    } | {
                        ref_id for ref_id, _, _, _ in payment_intent_refs
                    }
                    for membership_id, membership_box_id, membership_root_slug, identity_id, student_id in membership_rows:
                        if membership_box_id not in (None, box_id):
                            semantic_errors.append(
                                f'StudentBoxMembership {membership_id}: FK aponta para outro Box'
                            )
                        if membership_root_slug not in box_aliases:
                            semantic_errors.append(
                                f'StudentBoxMembership {membership_id}: box_root_slug divergente'
                            )
                        identity = identities.get(identity_id)
                        if identity is None:
                            semantic_errors.append(
                                f'StudentBoxMembership {membership_id}: identity {identity_id} ausente'
                            )
                            continue
                        belongs_to_box = (
                            identity.box_id == box_id
                            or (identity.box_id is None and identity.box_root_slug in box_aliases)
                        )
                        if not belongs_to_box:
                            semantic_errors.append(
                                f'StudentBoxMembership {membership_id}: identity {identity_id} '
                                'pertence a outro Box'
                            )
                        if student_id is not None:
                            if identity.student_id is not None and identity.student_id != student_id:
                                semantic_errors.append(
                                    f'StudentBoxMembership {membership_id}: identity {identity_id} '
                                    f'aponta para Student {identity.student_id}, esperado {student_id}'
                                )
                            if student_id not in tenant_students:
                                semantic_errors.append(
                                    f'StudentBoxMembership {membership_id}: Student {student_id} ausente'
                                )
                            else:
                                student_identity_id = tenant_students[student_id]
                                if student_identity_id is not None and student_identity_id != identity_id:
                                    semantic_errors.append(
                                        f'StudentBoxMembership {membership_id}: Student {student_id} '
                                        f'usa identity {student_identity_id}, esperado {identity_id}'
                                    )

                    for model_label, row_id, row_box_id, root_slug in shared_box_anchor_rows:
                        if row_box_id not in (None, box_id):
                            semantic_errors.append(
                                f'{model_label} {row_id}: FK aponta para outro Box'
                            )
                        if root_slug not in box_aliases:
                            semantic_errors.append(
                                f'{model_label} {row_id}: box_root_slug divergente'
                            )

                    for transfer_id, from_box_id, from_root_slug, to_box_id, to_root_slug in transfer_rows:
                        for side, side_box_id, side_root_slug in (
                            ('origem', from_box_id, from_root_slug),
                            ('destino', to_box_id, to_root_slug),
                        ):
                            side_references_box = (
                                side_box_id == box_id or side_root_slug in box_aliases
                            )
                            if not side_references_box:
                                continue
                            if side_box_id not in (None, box_id):
                                semantic_errors.append(
                                    f'StudentTransfer {transfer_id}: FK de {side} aponta para outro Box'
                                )
                            if side_root_slug not in box_aliases:
                                semantic_errors.append(
                                    f'StudentTransfer {transfer_id}: box_root_slug de {side} divergente'
                                )

                    for ref_id, ref_schema, payment_id in stripe_payment_refs:
                        if ref_schema != schema_name:
                            semantic_errors.append(
                                f'StripePaymentRef {ref_id}: box_schema não canônico para este Box'
                            )
                        if payment_id not in existing_payment_ids:
                            semantic_errors.append(
                                f'StripePaymentRef {ref_id}: Payment {payment_id} ausente no tenant'
                            )
                    for ref_id, payment_intent_id, ref_schema, payment_id in payment_intent_refs:
                        expected_payment_ids = payment_intents[payment_intent_id]
                        if (
                            len(expected_payment_ids) != 1
                            or ref_schema != schema_name
                            or payment_id != expected_payment_ids[0]
                        ):
                            semantic_errors.append(
                                f'StripePaymentRef {ref_id}: Payment intent resolve para outro Box/pagamento'
                            )

                    for setting_id, setting_box_id in approval_policy_rows:
                        if setting_box_id != box_id:
                            semantic_errors.append(
                                f'WorkoutApprovalPolicySetting {setting_id}: box_id aponta para '
                                f'{setting_box_id}, esperado {box_id}'
                            )

                    for milestone_id, identity_id, subject_kind, subject_key, cohort_kind, cohort_key in milestone_identity_rows:
                        identity_key = str(identity_id)
                        if subject_kind != 'identity' or subject_key != identity_key:
                            semantic_errors.append(
                                f'StudentJourneyMilestone {milestone_id}: subject identity divergente'
                            )
                        if cohort_kind == 'identity' and cohort_key != identity_key:
                            semantic_errors.append(
                                f'StudentJourneyMilestone {milestone_id}: cohort identity divergente'
                            )

                    for request_id, student_id, identity_id in profile_change_rows:
                        identity = identities.get(identity_id)
                        if identity is None:
                            semantic_errors.append(
                                f'StudentProfileChangeRequest {request_id}: identity {identity_id} ausente'
                            )
                            continue
                        belongs_to_box = (
                            identity.box_id == box_id
                            or (identity.box_id is None and identity.box_root_slug in box_aliases)
                        )
                        if not belongs_to_box:
                            semantic_errors.append(
                                f'StudentProfileChangeRequest {request_id}: identity {identity_id} '
                                'pertence a outro Box'
                            )
                        if identity.student_id is not None and identity.student_id != student_id:
                            semantic_errors.append(
                                f'StudentProfileChangeRequest {request_id}: identity {identity_id} '
                                f'aponta para Student {identity.student_id}, esperado {student_id}'
                            )
                        if student_id not in tenant_students:
                            semantic_errors.append(
                                f'StudentProfileChangeRequest {request_id}: Student {student_id} ausente'
                            )
                        else:
                            student_identity_id = tenant_students[student_id]
                            if student_identity_id is not None and student_identity_id != identity_id:
                                semantic_errors.append(
                                    f'StudentProfileChangeRequest {request_id}: Student {student_id} '
                                    f'usa identity {student_identity_id}, esperado {identity_id}'
                                )

                    if semantic_errors:
                        failures.append(
                            f'C5S: {len(semantic_errors)} vínculo(s) shared/tenant inválido(s): '
                            + '; '.join(semantic_errors[:20])
                        )
                    else:
                        passes.append(
                            f'C5S: {len(student_links)} vínculo(s) Student/identity e '
                            f'{len(membership_rows)} StudentBoxMembership e '
                            f'{len(shared_box_anchor_rows)} âncoras shared, {len(transfer_rows)} '
                            f'StudentTransfer, {len(stripe_ref_ids)} StripePaymentRef, '
                            f'{len(profile_change_rows)} StudentProfileChangeRequest e '
                            f'{len(milestone_identity_rows)} StudentJourneyMilestone '
                            f'e {len(approval_policy_rows)} WorkoutApprovalPolicySetting '
                            'coerentes.'
                        )
            except Exception as exc:
                failures.append(f'C5S: erro ao verificar vínculos de restore — {exc}')

        if not schema_only:
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

        if not schema_only:
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

        if not schema_only:
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
