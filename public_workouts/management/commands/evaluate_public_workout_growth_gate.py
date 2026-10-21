import json

from django.core.management.base import BaseCommand, CommandError
from django.db.utils import ProgrammingError
from django.utils.dateparse import parse_date

from public_workouts.growth_gate import evaluate_growth_readiness


class Command(BaseCommand):
    help = 'Avalia evidências acumuladas antes de aumentar tráfego pago do Curva.'

    def add_arguments(self, parser):
        parser.add_argument('--as-of', help='Data final YYYY-MM-DD; padrão: hoje local.')
        parser.add_argument('--observation-days', type=int, default=28)
        parser.add_argument('--consecutive-green-days', type=int, default=14)
        parser.add_argument('--strict', action='store_true', help='Falha se o gate ainda não estiver pronto.')

    def handle(self, *args, **options):
        as_of = parse_date(options['as_of']) if options.get('as_of') else None
        if options.get('as_of') and as_of is None:
            raise CommandError('--as-of deve usar YYYY-MM-DD')
        try:
            result = evaluate_growth_readiness(
                as_of=as_of,
                observation_days=options['observation_days'],
                consecutive_green_days=options['consecutive_green_days'],
            )
        except ValueError as exc:
            raise CommandError(str(exc)) from exc
        except ProgrammingError as exc:
            raise CommandError(
                'Snapshots Curva não estão disponíveis neste banco. Rode as migrations antes de avaliar o gate.'
            ) from exc
        self.stdout.write(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        if options['strict'] and not result['ready_to_scale']:
            raise CommandError('Gate Curva não está pronto para escalar tráfego pago.')
