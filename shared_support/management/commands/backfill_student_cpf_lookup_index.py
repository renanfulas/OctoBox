"""Backfill or verify exact-lookup HMACs for encrypted Student CPF values."""

from __future__ import annotations

import json
import re

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.db.models import Count
from django_tenants.utils import get_public_schema_name, schema_context

from control.models import Box
from control.tenant_write_fence import tenant_write_guarded_command
from shared_support.crypto_fields import generate_cpf_blind_index
from students.models import Student


_SCHEMA_RE = re.compile(r"^box_[a-z0-9_-]{1,59}$")


class Command(BaseCommand):
    help = (
        "Faz dry-run, backfill ou verificação agregada do índice de CPF de um "
        "único tenant explícito."
    )

    def add_arguments(self, parser):
        parser.add_argument("--schema", required=True, help="Schema box_<slug> cadastrado.")
        action = parser.add_mutually_exclusive_group()
        action.add_argument("--apply", action="store_true", help="Grava somente índices atualmente vazios.")
        action.add_argument("--verify", action="store_true", help="Recalcula e compara; não grava.")
        parser.add_argument("--batch-size", type=int, default=250)
        parser.add_argument("--limit", type=int, default=0, help="Limita linhas percorridas; 0 significa sem limite.")

    @tenant_write_guarded_command()
    def handle(self, *args, **options):
        schema_name = options["schema"]
        batch_size = options["batch_size"]
        after_id = 0
        limit = options["limit"]
        apply_changes = options["apply"]
        verify = options["verify"]

        if not _SCHEMA_RE.fullmatch(schema_name):
            raise CommandError("Informe um schema válido no formato box_<slug>.")
        if connection.vendor != "postgresql":
            raise CommandError("O backfill exige PostgreSQL tenant-aware.")
        if not 1 <= batch_size <= 5000:
            raise CommandError("batch-size deve estar entre 1 e 5000.")
        if limit < 0:
            raise CommandError("limit não pode ser negativo.")
        if not getattr(settings, "PHONE_BLIND_INDEX_KEY", ""):
            raise CommandError("PHONE_BLIND_INDEX_KEY ausente; nenhum dado foi alterado.")

        with schema_context(get_public_schema_name()):
            if not Box.objects.filter(schema_name=schema_name).exists():
                raise CommandError("O schema informado não corresponde a um box cadastrado.")

        counts = {
            "rows_scanned": 0,
            "nonempty_cpf": 0,
            "missing_index": 0,
            "written": 0,
            "drift": 0,
            "write_conflicts": 0,
        }
        cursor_id = after_id

        try:
            with schema_context(schema_name):
                while True:
                    remaining = limit - counts["rows_scanned"] if limit else batch_size
                    if limit and remaining <= 0:
                        break
                    current_batch_size = min(batch_size, remaining) if limit else batch_size
                    queryset = Student.objects.filter(pk__gt=cursor_id).order_by("pk")
                    if not verify:
                        queryset = queryset.filter(cpf_lookup_index="")
                    queryset = queryset.only("pk", "cpf", "cpf_lookup_index")

                    if apply_changes:
                        with transaction.atomic():
                            rows = list(queryset.select_for_update()[:current_batch_size])
                            self._process_rows(
                                rows,
                                counts=counts,
                                apply_changes=True,
                                verify=False,
                            )
                    else:
                        rows = list(queryset[:current_batch_size])
                        self._process_rows(
                            rows,
                            counts=counts,
                            apply_changes=False,
                            verify=verify,
                        )

                    if not rows:
                        break
                    cursor_id = rows[-1].pk

        except CommandError:
            raise
        except Exception as exc:
            # ORM conversion errors may refer to stored PII. Keep the operator
            # message aggregate-only; already committed batches are resumable.
            raise CommandError(
                "Operação interrompida ao ler ou gravar um lote; nenhum valor de CPF foi exibido."
            ) from exc

        with schema_context(schema_name):
            duplicate_groups = (
                Student.objects.exclude(cpf_lookup_index="")
                .values("cpf_lookup_index")
                .annotate(row_count=Count("pk"))
                .filter(row_count__gt=1)
                .count()
            )

        mode = "apply" if apply_changes else "verify" if verify else "dry-run"
        report = {
            "schema": schema_name,
            "mode": mode,
            **counts,
            "stored_duplicate_index_groups": duplicate_groups,
            "complete_target_scan": not bool(limit),
        }
        self.stdout.write(json.dumps(report, ensure_ascii=False, sort_keys=True))

        if verify and (counts["missing_index"] or counts["drift"] or duplicate_groups):
            raise CommandError("Verificação de CPF encontrou índice ausente, divergente ou duplicado.")

    @staticmethod
    def _process_rows(rows, *, counts, apply_changes, verify):
        for student in rows:
            counts["rows_scanned"] += 1
            expected_index = generate_cpf_blind_index(student.cpf)
            if expected_index:
                counts["nonempty_cpf"] += 1
            if not student.cpf_lookup_index and expected_index:
                counts["missing_index"] += 1
                if apply_changes:
                    updated = Student.objects.filter(
                        pk=student.pk,
                        cpf_lookup_index="",
                    ).update(cpf_lookup_index=expected_index)
                    if updated:
                        counts["written"] += 1
                    else:
                        counts["write_conflicts"] += 1
            elif verify and student.cpf_lookup_index != expected_index:
                counts["drift"] += 1


__all__ = ["Command"]
