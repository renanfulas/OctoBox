"""Rotate encrypted PII for one explicitly selected tenant or shared field.

Dry-run is the default. Apply mode reads raw stored values, authenticates each
old value, and updates only if the ciphertext still matches what was read.
Checkpoint files contain only target metadata and the last primary key.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django_tenants.utils import get_public_schema_name, schema_context

from control.models import Box
from control.tenant_write_fence import tenant_write_guarded_command
from shared_support.crypto_codec import decode, encode
from shared_support.crypto_keyring import CryptoKeyringError, load_crypto_keyring


_SCHEMA_RE = re.compile(r"^box_[a-z0-9_-]{1,59}$")


def _rotation_targets():
    """Return the allowlisted encrypted fields eligible for key rotation."""

    from communications.models import WhatsAppContact, WhatsAppMessageLog
    from onboarding.models import StudentIntake
    from students.models import Student

    return {
        "Student": {"phone": Student, "cpf": Student},
        "StudentIntake": {"phone": StudentIntake, "email": StudentIntake},
        "WhatsAppContact": {"phone": WhatsAppContact},
        "WhatsAppMessageLog": {"body": WhatsAppMessageLog},
    }


def _shared_rotation_targets():
    """Return PII fields stored in public/shared tables eligible for rotation."""

    from student_identity.models import StudentAppInvitation, StudentInvitationDelivery
    from signup.models import PendingSignup

    return {
        "StudentInvitationDelivery": {"recipient": StudentInvitationDelivery},
        "StudentAppInvitation": {"invited_email": StudentAppInvitation},
        "PendingSignup": {"email": PendingSignup},
    }


def _write_checkpoint(path: Path, payload: dict) -> None:
    """Atomically persist non-PII resume metadata beside the chosen path."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            json.dump(payload, handle, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    finally:
        if temporary_path and temporary_path.exists():
            temporary_path.unlink()


class Command(BaseCommand):
    help = "Faz dry-run ou rotação condicional da cifra PII em um tenant ou no schema shared."

    def add_arguments(self, parser):
        scope = parser.add_mutually_exclusive_group(required=True)
        scope.add_argument("--schema", help="Schema box_<slug> cadastrado.")
        scope.add_argument("--shared", action="store_true", help="Rotaciona apenas a allowlist shared/public.")
        model_choices = tuple(dict.fromkeys((*_rotation_targets(), *_shared_rotation_targets())))
        parser.add_argument("--model", required=True, choices=model_choices)
        parser.add_argument("--field", required=True, help="Campo cifrado allowlisted do modelo.")
        mode = parser.add_mutually_exclusive_group()
        mode.add_argument("--apply", action="store_true", help="Grava envelopes com a chave ativa.")
        mode.add_argument("--verify", action="store_true", help="Só classifica se restam formatos antigos.")
        cursor = parser.add_mutually_exclusive_group()
        cursor.add_argument("--after-pk", default="", help="Retoma após esta PK (modo sem checkpoint).")
        cursor.add_argument("--checkpoint", help="Arquivo JSON local com cursor retomável; fora do Git.")
        parser.add_argument("--batch-size", type=int, default=250)
        parser.add_argument("--limit", type=int, default=0, help="Limita registros lidos; 0 significa sem limite.")

    @tenant_write_guarded_command()
    def handle(self, *args, **options):
        shared_scope = options["shared"]
        schema_name = get_public_schema_name() if shared_scope else options["schema"]
        model_name = options["model"]
        field_name = options["field"]
        apply_changes = options["apply"]
        verify = options["verify"]
        mode = "apply" if apply_changes else "verify" if verify else "dry-run"
        batch_size = options["batch_size"]
        limit = options["limit"]

        if not shared_scope and not _SCHEMA_RE.fullmatch(schema_name):
            raise CommandError("Informe um schema válido no formato box_<slug>.")
        if not 1 <= batch_size <= 5000 or limit < 0:
            raise CommandError("batch-size deve ser 1–5000 e limit não pode ser negativo.")
        target_maps = _shared_rotation_targets() if shared_scope else _rotation_targets()
        model_map = target_maps.get(model_name)
        if model_map is None:
            raise CommandError("O modelo não pertence ao escopo selecionado para rotação.")
        model = model_map.get(field_name)
        if model is None:
            raise CommandError("O campo não está na allowlist de rotação criptográfica.")
        if connection.vendor != "postgresql":
            raise CommandError("A rotação exige PostgreSQL tenant-aware.")
        if shared_scope and model_name == "PendingSignup" and field_name == "email":
            if not getattr(settings, "PENDING_SIGNUP_EMAIL_LOOKUP_INDEX_READY", False):
                raise CommandError(
                    "Ative e verifique o HMAC de PendingSignup antes de rotacionar email."
                )
            if not getattr(settings, "EMAIL_BLIND_INDEX_KEY", ""):
                raise CommandError(
                    "EMAIL_BLIND_INDEX_KEY ausente; nenhum email foi rotacionado."
                )
        field = model._meta.get_field(field_name)
        pk_field = model._meta.pk
        if pk_field.get_internal_type() not in {"AutoField", "BigAutoField", "SmallAutoField"}:
            raise CommandError("O modelo não tem uma chave primária inteira retomável.")

        try:
            keyring = load_crypto_keyring()
            active_key_id, _ = keyring.active()
        except CryptoKeyringError as exc:
            raise CommandError("Keyring PII inválido ou sem chave ativa; nenhum dado foi lido.") from exc

        if not shared_scope:
            with schema_context(get_public_schema_name()):
                if not Box.objects.filter(schema_name=schema_name).exists():
                    raise CommandError("O schema informado não corresponde a um box cadastrado.")

        checkpoint_path = Path(options["checkpoint"]) if options["checkpoint"] else None
        target = {
            "scope": "shared" if shared_scope else "tenant",
            "schema": schema_name,
            "model": model_name,
            "field": field_name,
            "mode": mode,
            "active_key_id": active_key_id,
        }
        after_pk = 0
        if options["after_pk"]:
            try:
                after_pk = int(options["after_pk"])
            except (TypeError, ValueError) as exc:
                raise CommandError("after-pk deve ser um inteiro não negativo.") from exc
            if after_pk < 0:
                raise CommandError("after-pk deve ser um inteiro não negativo.")
        if checkpoint_path and checkpoint_path.exists():
            try:
                checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                raise CommandError("Checkpoint ilegível; nenhum dado foi alterado.") from exc
            if not isinstance(checkpoint, dict):
                raise CommandError("Checkpoint ilegível; nenhum dado foi alterado.")
            if any(checkpoint.get(key) != value for key, value in target.items()):
                raise CommandError("Checkpoint pertence a outro alvo ou modo.")
            try:
                after_pk = int(checkpoint.get("last_pk", 0))
            except (TypeError, ValueError) as exc:
                raise CommandError("Checkpoint contém cursor inválido.") from exc
            if after_pk < 0:
                raise CommandError("Checkpoint contém cursor inválido.")
        elif checkpoint_path:
            _write_checkpoint(checkpoint_path, {**target, "last_pk": 0, "complete": False})

        counts = {
            "rows_scanned": 0,
            "empty": 0,
            "already_active": 0,
            "eligible": 0,
            "would_write": 0,
            "written": 0,
            "unreadable": 0,
        }
        last_pk = after_pk
        scan_exhausted = False
        table_sql = connection.ops.quote_name(model._meta.db_table)
        pk_sql = connection.ops.quote_name(pk_field.column)
        value_sql = connection.ops.quote_name(field.column)

        try:
            with schema_context(schema_name):
                while True:
                    remaining = limit - counts["rows_scanned"] if limit else batch_size
                    if limit and remaining <= 0:
                        break
                    current_batch_size = min(batch_size, remaining) if limit else batch_size
                    try:
                        with transaction.atomic():
                            with connection.cursor() as cursor:
                                if not apply_changes:
                                    cursor.execute("SET TRANSACTION READ ONLY")
                                cursor.execute(
                                    f"SELECT {pk_sql}, {value_sql} FROM {table_sql} "
                                    f"WHERE {pk_sql} > %s ORDER BY {pk_sql} LIMIT %s",
                                    [last_pk, current_batch_size],
                                )
                                rows = cursor.fetchall()
                                for primary_key, raw_value in rows:
                                    result = decode(raw_value, keyring=keyring)
                                    if result.status == "empty":
                                        counts["empty"] += 1
                                        continue
                                    if not result.is_readable:
                                        counts["unreadable"] += 1
                                        continue
                                    if result.status == "envelope" and result.key_id == active_key_id:
                                        counts["already_active"] += 1
                                        continue

                                    counts["eligible"] += 1
                                    if not apply_changes:
                                        counts["would_write"] += 1
                                        continue

                                    replacement = encode(result.plaintext, keyring=keyring)
                                    cursor.execute(
                                        f"UPDATE {table_sql} SET {value_sql} = %s "
                                        f"WHERE {pk_sql} = %s AND {value_sql} IS NOT DISTINCT FROM %s",
                                        [replacement, primary_key, raw_value],
                                    )
                                    if cursor.rowcount != 1:
                                        raise _ConcurrentUpdate
                                    counts["written"] += 1
                        if rows:
                            last_pk = rows[-1][0]
                            counts["rows_scanned"] += len(rows)
                            if checkpoint_path:
                                _write_checkpoint(
                                    checkpoint_path,
                                    {**target, "last_pk": last_pk, "complete": False},
                                )
                        else:
                            scan_exhausted = True
                            if checkpoint_path:
                                _write_checkpoint(
                                    checkpoint_path,
                                    {**target, "last_pk": last_pk, "complete": True},
                                )
                            break
                    except _ConcurrentUpdate as exc:
                        raise CommandError(
                            "Um valor mudou durante o lote; lote revertido e checkpoint mantido. "
                            "Repita a partir do mesmo cursor."
                        ) from exc
        except CommandError:
            raise
        except Exception as exc:
            raise CommandError(
                "Rotação interrompida; nenhum valor de PII foi exibido. "
                "Retome pelo checkpoint depois de investigar o erro."
            ) from exc

        report = {
            **target,
            "active_key_id": active_key_id,
            "batch_size": batch_size,
            "last_pk": last_pk,
            "complete_scan": scan_exhausted,
            "checkpoint": str(checkpoint_path) if checkpoint_path else None,
            **counts,
        }
        self.stdout.write(json.dumps(report, ensure_ascii=False, sort_keys=True))


class _ConcurrentUpdate(Exception):
    """Signal that an optimistic raw-value update lost its compare-and-swap."""
