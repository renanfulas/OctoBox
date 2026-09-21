import json

from django.core.management.base import BaseCommand

from public_workouts.funnel_analytics import build_acquisition_report


class Command(BaseCommand):
    help = 'Relatório agregado de aquisição Curva; não altera dados ou assinaturas.'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, choices=(7, 30, 90), default=30)
        parser.add_argument('--conversion-days', type=int, choices=(7, 14, 30), default=7)

    def handle(self, *args, **options):
        report = build_acquisition_report(
            window_days=options['days'], conversion_days=options['conversion_days'],
        )
        self.stdout.write(json.dumps(report, ensure_ascii=False, indent=2))
