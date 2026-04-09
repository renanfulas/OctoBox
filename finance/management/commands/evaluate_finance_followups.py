from django.core.management.base import BaseCommand

from finance.follow_up_tracker import evaluate_pending_finance_follow_ups


class Command(BaseCommand):
    help = 'Avalia follow-ups financeiros realizados cujo outcome ja venceu a janela configurada.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--window',
            choices=['7d', '15d', '30d'],
            default='',
            help='Avalia apenas uma janela especifica de outcome.',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=0,
            help='Limita a quantidade de follow-ups avaliados nesta execucao.',
        )

    def handle(self, *args, **options):
        window = options.get('window') or None
        limit = options.get('limit') or None
        if limit is not None and limit <= 0:
            limit = None

        evaluated = evaluate_pending_finance_follow_ups(window=window, limit=limit)
        window_label = window or 'todas as janelas'
        self.stdout.write(
            self.style.SUCCESS(
                f'Follow-ups financeiros avaliados: {evaluated} ({window_label}).'
            )
        )
