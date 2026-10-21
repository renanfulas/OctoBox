from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from public_workouts.models import (
    PublicWorkoutExperiment,
    PublicWorkoutExperimentStatus,
    PublicWorkoutExperimentVariant,
)


class Command(BaseCommand):
    help = 'Cria ou atualiza um experimento Curva sem promover variantes automaticamente.'

    def add_arguments(self, parser):
        parser.add_argument('--key', required=True)
        parser.add_argument('--name', required=True)
        parser.add_argument('--hypothesis', default='')
        parser.add_argument('--variant', action='append', required=True, help='chave:peso; repita para cada variante')
        parser.add_argument('--conversion-days', type=int, default=7)
        parser.add_argument('--minimum-sample-size', type=int, default=100)
        parser.add_argument('--start', action='store_true')

    @transaction.atomic
    def handle(self, *args, **options):
        variants = []
        for raw in options['variant']:
            try:
                key, raw_weight = raw.rsplit(':', 1)
                weight = int(raw_weight)
            except (TypeError, ValueError):
                raise CommandError(f'Variante inválida: {raw}. Use chave:peso.')
            key = key.strip()
            if not key or weight < 1:
                raise CommandError(f'Variante inválida: {raw}. Peso precisa ser positivo.')
            variants.append((key, weight))
        if len({key for key, _weight in variants}) < 2:
            raise CommandError('Informe pelo menos duas variantes diferentes.')
        if not 1 <= options['conversion_days'] <= 30:
            raise CommandError('conversion-days precisa estar entre 1 e 30.')
        if options['minimum_sample_size'] < 1:
            raise CommandError('minimum-sample-size precisa ser positivo.')

        defaults = {
            'name': options['name'],
            'hypothesis': options['hypothesis'],
            'conversion_days': options['conversion_days'],
            'minimum_sample_size': options['minimum_sample_size'],
        }
        if options['start']:
            defaults.update(status=PublicWorkoutExperimentStatus.RUNNING, starts_at=timezone.now())
        experiment, created = PublicWorkoutExperiment.objects.update_or_create(
            key=options['key'], defaults=defaults,
        )
        active_keys = []
        for key, weight in variants:
            PublicWorkoutExperimentVariant.objects.update_or_create(
                experiment=experiment,
                key=key,
                defaults={'name': key.replace('-', ' ').title(), 'allocation_weight': weight, 'is_active': True},
            )
            active_keys.append(key)
        experiment.variants.exclude(key__in=active_keys).update(is_active=False)
        action = 'criado' if created else 'atualizado'
        self.stdout.write(self.style.SUCCESS(
            f'Experimento {experiment.key} {action} com {len(active_keys)} variantes; status={experiment.status}.',
        ))
