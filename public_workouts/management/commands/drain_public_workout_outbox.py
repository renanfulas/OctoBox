from django.core.management.base import BaseCommand

from public_workouts.outbox import drain_public_workout_outbox


class Command(BaseCommand):
    help = 'Envia mensagens pendentes da outbox Curva com retry/backoff.'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=25)

    def handle(self, *args, **options):
        result = drain_public_workout_outbox(limit=max(1, options['limit']))
        self.stdout.write(self.style.SUCCESS(str(result)))
