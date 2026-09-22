from django.core.management.base import BaseCommand

from public_workouts.models import PublicWorkoutSubscription
from public_workouts.operations import (
    ensure_recurring_review_work_items,
    ensure_required_work_items,
)


class Command(BaseCommand):
    help = 'Reconcilia work items Curva ausentes de forma idempotente.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        if options['dry_run']:
            self.stdout.write(
                f'{PublicWorkoutSubscription.objects.count()} assinaturas seriam avaliadas; nenhuma escrita realizada.'
            )
            return

        created = []
        for subscription_id in PublicWorkoutSubscription.objects.values_list('id', flat=True).iterator():
            created.extend(ensure_required_work_items(subscription_id))
        created.extend(ensure_recurring_review_work_items())
        self.stdout.write(self.style.SUCCESS(f'{len(created)} work items criados.'))
