"""Read-only aggregate census of encrypted PII in a tenant or public schema."""

from __future__ import annotations

import json
import re

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django_tenants.utils import get_public_schema_name, schema_context

from control.models import Box
from shared_support.crypto_codec import decode
from shared_support.crypto_keyring import CryptoKeyringError, load_crypto_keyring


_SCHEMA_RE = re.compile(r"^box_[a-z0-9_-]{1,59}$")
_PII_FIELDS = (
    ("students", "Student", "phone", False),
    ("students", "Student", "cpf", False),
    ("students", "Student", "email", True),
    ("onboarding", "StudentIntake", "phone", False),
    ("onboarding", "StudentIntake", "email", False),
    ("communications", "WhatsAppContact", "phone", False),
    ("communications", "WhatsAppMessageLog", "body", False),
)
_SHARED_PII_FIELDS = (
    ("student_identity", "StudentInvitationDelivery", "recipient", False),
    ("student_identity", "StudentIdentity", "email", True),
    ("student_identity", "StudentAppInvitation", "invited_email", False),
    ("public_workouts", "PublicWorkoutAccount", "email", True),
    ("public_workouts", "PublicWorkoutCheckoutLead", "email", True),
    ("public_workouts", "PublicWorkoutWaitlistEntry", "email", True),
    ("signup", "PendingSignup", "email", False),
    ("auth", "User", "email", True),
)


def summarize_raw_values(values, *, keyring, logical_limit=None, plaintext_field=False):
    """Classify raw DB values and return counts/length aggregates only."""

    counts = {}
    total = 0
    max_stored_characters = 0
    max_readable_plaintext_characters = 0
    readable_over_logical_limit = 0

    for raw_value in values:
        if plaintext_field:
            status = "unencrypted_plaintext" if raw_value not in (None, "") else "empty"
            plaintext = raw_value
            is_readable = True
        else:
            result = decode(raw_value, keyring=keyring)
            status = result.status
            plaintext = result.plaintext
            is_readable = result.is_readable
        counts[status] = counts.get(status, 0) + 1
        total += 1
        if raw_value is not None:
            max_stored_characters = max(max_stored_characters, len(raw_value))
        if is_readable and plaintext is not None:
            plaintext_length = len(plaintext)
            max_readable_plaintext_characters = max(
                max_readable_plaintext_characters,
                plaintext_length,
            )
            if logical_limit is not None and plaintext_length > logical_limit:
                readable_over_logical_limit += 1

    return {
        "rows": total,
        "format_counts": dict(sorted(counts.items())),
        "max_stored_characters": max_stored_characters,
        "max_readable_plaintext_characters": max_readable_plaintext_characters,
        "readable_over_logical_limit": readable_over_logical_limit,
    }


class Command(BaseCommand):
    help = "Gera census read-only e agregado de formatos de PII em um tenant ou no schema shared."

    def add_arguments(self, parser):
        scope = parser.add_mutually_exclusive_group(required=True)
        scope.add_argument(
            "--schema",
            help="Schema box_<slug> exato, cadastrado em control.Box.",
        )
        scope.add_argument(
            "--shared",
            action="store_true",
            help="Analisa somente a allowlist do schema shared/public.",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=500,
            help="Quantidade de valores lidos por lote (1–10000).",
        )

    def handle(self, *args, **options):
        shared_scope = options["shared"]
        schema_name = get_public_schema_name() if shared_scope else options["schema"]
        batch_size = options["batch_size"]
        if not shared_scope and not _SCHEMA_RE.fullmatch(schema_name):
            raise CommandError("Informe um schema válido no formato box_<slug>.")
        if batch_size < 1 or batch_size > 10000:
            raise CommandError("batch-size deve estar entre 1 e 10000.")
        if connection.vendor != "postgresql":
            raise CommandError("A census exige PostgreSQL tenant-aware.")

        try:
            keyring = load_crypto_keyring()
        except CryptoKeyringError as exc:
            raise CommandError("Configuração do keyring PII inválida; nenhum dado foi lido.") from exc

        if not shared_scope:
            with schema_context(get_public_schema_name()):
                if not Box.objects.filter(schema_name=schema_name).exists():
                    raise CommandError("O schema informado não corresponde a um box cadastrado.")

        from communications.models import WhatsAppContact, WhatsAppMessageLog
        from onboarding.models import StudentIntake
        from students.models import Student
        from django.contrib.auth import get_user_model
        from public_workouts.models import (
            PublicWorkoutAccount,
            PublicWorkoutCheckoutLead,
            PublicWorkoutWaitlistEntry,
        )
        from signup.models import PendingSignup
        from student_identity.models import (
            StudentAppInvitation,
            StudentIdentity,
            StudentInvitationDelivery,
        )

        model_map = {
            ("students", "Student"): Student,
            ("onboarding", "StudentIntake"): StudentIntake,
            ("communications", "WhatsAppContact"): WhatsAppContact,
            ("communications", "WhatsAppMessageLog"): WhatsAppMessageLog,
            ("student_identity", "StudentInvitationDelivery"): StudentInvitationDelivery,
            ("student_identity", "StudentIdentity"): StudentIdentity,
            ("student_identity", "StudentAppInvitation"): StudentAppInvitation,
            ("public_workouts", "PublicWorkoutAccount"): PublicWorkoutAccount,
            ("public_workouts", "PublicWorkoutCheckoutLead"): PublicWorkoutCheckoutLead,
            ("public_workouts", "PublicWorkoutWaitlistEntry"): PublicWorkoutWaitlistEntry,
            ("signup", "PendingSignup"): PendingSignup,
            ("auth", "User"): get_user_model(),
        }
        fields = _SHARED_PII_FIELDS if shared_scope else _PII_FIELDS
        report = {"scope": "shared" if shared_scope else "tenant", "schema": schema_name, "fields": []}

        try:
            with schema_context(schema_name):
                with transaction.atomic():
                    # Make the entire census transaction read-only. This also
                    # allows bounded server-side cursor reads on PostgreSQL.
                    with connection.cursor() as guard_cursor:
                        guard_cursor.execute("SET TRANSACTION READ ONLY")

                    for app_label, model_name, field_name, plaintext_field in fields:
                        model = model_map[(app_label, model_name)]
                        field = model._meta.get_field(field_name)
                        table_sql = connection.ops.quote_name(model._meta.db_table)
                        column_sql = connection.ops.quote_name(field.column)
                        query = f"SELECT {column_sql} FROM {table_sql}"

                        with connection.chunked_cursor() as cursor:
                            cursor.itersize = batch_size
                            cursor.execute(query)
                            def raw_values():
                                while rows := cursor.fetchmany(batch_size):
                                    for row in rows:
                                        yield row[0]

                            aggregates = summarize_raw_values(
                                raw_values(),
                                keyring=keyring,
                                logical_limit=field.max_length,
                                plaintext_field=plaintext_field,
                            )
                        report["fields"].append({
                            "model": model_name,
                            "field": field_name,
                            "stored_plaintext": plaintext_field,
                            **aggregates,
                        })
        except CommandError:
            raise
        except Exception as exc:
            # Database errors can contain query details; suppress raw details
            # so this operational report never emits stored PII.
            raise CommandError("Census interrompida; relatório agregado não foi concluído.") from exc

        self.stdout.write(json.dumps(report, ensure_ascii=False, sort_keys=True))
