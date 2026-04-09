from django.core.management.base import BaseCommand, CommandError

from shared_support.static_assets import detect_static_drift


class Command(BaseCommand):
    help = "Detecta quando static/ e staticfiles/ ficaram fora de sincronia."

    def add_arguments(self, parser):
        parser.add_argument(
            "--subpaths",
            nargs="*",
            default=["css", "js"],
            help="Subpastas dentro de static/ que devem ser auditadas.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=20,
            help="Numero maximo de divergencias exibidas no terminal.",
        )
        parser.add_argument(
            "--strict",
            action="store_true",
            help="Falha com exit code != 0 quando houver drift detectado.",
        )

    def handle(self, *args, **options):
        drift = detect_static_drift(subpaths=options["subpaths"])
        if not drift:
            self.stdout.write(self.style.SUCCESS("Sem static drift: static/ e staticfiles/ estao sincronizados."))
            return

        limit = max(1, options["limit"])
        total = len(drift)
        self.stdout.write(
            self.style.WARNING(
                f"Detectado static drift em {total} arquivo(s). "
                "O runtime pode estar usando assets visuais desatualizados."
            )
        )

        for item in drift[:limit]:
            self.stdout.write(f"- {item['reason']}: {item['path']}")

        if total > limit:
            self.stdout.write(f"... e mais {total - limit} arquivo(s).")

        self.stdout.write("")
        self.stdout.write("Proximo passo sugerido:")
        self.stdout.write("- Rode `./manage.py collectstatic --noinput` para regenerar os assets coletados.")
        self.stdout.write("- Para espelho local rapido, use `./manage.py sync_runtime_assets --collectstatic`.")

        if options["strict"]:
            raise CommandError("Static drift detectado.")
