"""Fail closed for the retired SQLite restore placeholder.

This command historically validated a ZIP/SQLite snapshot, printed a success
message, and never restored the application database. Keep the command name
discoverable so old operator instructions fail with a clear explanation.
The supported tenant recovery flow is documented in
``docs/rollout/restore-and-rollback-drill.md`` and uses the isolated PostgreSQL
restore script; this command must never imply that recovery succeeded.
"""

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Desativado: este placeholder não restaura bancos de dados."

    def add_arguments(self, parser):
        parser.add_argument("snapshot_zip", help="Argumento legado; nenhuma restauração será executada.")
        parser.add_argument(
            "--force",
            action="store_true",
            help="Argumento legado sem efeito; não habilita restauração.",
        )

    def handle(self, *args, **options):
        raise CommandError(
            "restore_snapshot está desativado: o comando legado não restaurava o banco. "
            "Siga docs/rollout/restore-and-rollback-drill.md e use o fluxo PostgreSQL "
            "isolado scripts/linux/restore_tenant_schema.sh."
        )
