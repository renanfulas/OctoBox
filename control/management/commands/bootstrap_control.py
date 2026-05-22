"""
Aplica control.0001_initial bypassando o check de consistência do Django.

POR QUE EXISTE:
- student_identity/migrations/0001_initial.py foi squashado com dependência em
  control.0001_initial. Em produção o 0001_initial antigo (sem essa dependência)
  já estava aplicado, então `migrate --noinput` falha com InconsistentMigrationHistory.
- Este comando aplica control.0001_initial isoladamente, contornando o check,
  para que o `migrate` subsequente possa prosseguir normalmente.

QUANDO USAR:
- Apenas uma vez, no deploy que introduziu control.0001_initial em produção.
- O comando é idempotente: se control.0001_initial já estiver registrado em
  django_migrations, não faz nada.
"""

from django.core.management.base import BaseCommand
from django.db import connection
from django.db.migrations import loader as migrations_loader
from django.db.migrations.executor import MigrationExecutor
from django.utils.timezone import now


class Command(BaseCommand):
    help = "Aplica control.0001_initial bypassando InconsistentMigrationHistory."

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM django_migrations WHERE app='control' AND name='0001_initial'"
            )
            already_applied = cursor.fetchone()[0] > 0

        if already_applied:
            self.stdout.write(self.style.SUCCESS("control.0001_initial já aplicado — nada a fazer."))
            return

        self.stdout.write("Aplicando control.0001_initial (bypass consistency check)...")

        original_check = migrations_loader.MigrationLoader.check_consistent_history
        migrations_loader.MigrationLoader.check_consistent_history = lambda self, conn: None

        try:
            executor = MigrationExecutor(connection)
            migration = executor.loader.get_migration("control", "0001_initial")
            state = executor.loader.project_state(("control", "0001_initial"), at_end=False)
            new_state = state.clone()

            with connection.schema_editor() as schema_editor:
                migration.apply(new_state, schema_editor)

            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO django_migrations (app, name, applied) VALUES ('control', '0001_initial', %s)",
                    [now()],
                )

            self.stdout.write(self.style.SUCCESS("control.0001_initial aplicado com sucesso."))
        finally:
            migrations_loader.MigrationLoader.check_consistent_history = original_check
