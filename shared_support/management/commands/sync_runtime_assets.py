from django.core.management import call_command
from django.core.management.base import BaseCommand

from shared_support.static_assets import clear_runtime_css_cache, sync_static_to_staticfiles


class Command(BaseCommand):
    help = "Sincroniza static/ com staticfiles/ para manter o runtime local coerente."

    def add_arguments(self, parser):
        parser.add_argument(
            "--subpaths",
            nargs="*",
            default=["css", "js"],
            help="Subpastas dentro de static/ que devem ser espelhadas para staticfiles/.",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Limpa staticfiles/ antes de sincronizar.",
        )
        parser.add_argument(
            "--collectstatic",
            action="store_true",
            help="Executa collectstatic --noinput depois da sincronizacao para validar o espelho local.",
        )

    def handle(self, *args, **options):
        synced = sync_static_to_staticfiles(
            subpaths=options["subpaths"],
            clear=options["clear"],
        )
        clear_runtime_css_cache()

        if not synced:
            self.stdout.write(self.style.WARNING("Nenhum asset foi sincronizado."))
        else:
            for item in synced:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Sincronizado: {item['source']} -> {item['target']}"
                    )
                )

        if options["collectstatic"]:
            call_command("collectstatic", interactive=False, verbosity=0)
            self.stdout.write(self.style.SUCCESS("collectstatic executado com sucesso."))
