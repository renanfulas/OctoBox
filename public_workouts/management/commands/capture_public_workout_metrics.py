import json

from django.core.management.base import BaseCommand
from django.utils import timezone

from public_workouts.metrics import capture_daily_metrics
from public_workouts.models import PublicWorkoutMetricSnapshot


class Command(BaseCommand):
    help = 'Captura o snapshot diario do cockpit comercial e operacional Curva.'

    def handle(self, *args, **options):
        previous = PublicWorkoutMetricSnapshot.objects.exclude(
            metric_date=timezone.localdate(),
        ).order_by('-metric_date').first()
        snapshot = capture_daily_metrics()
        gate = snapshot.payload.get('growth_gate', {})
        previous_status = (
            (previous.payload or {}).get('growth_gate', {}).get('status') if previous else None
        )
        actionable = gate.get('status') != 'green' or gate.get('status') != previous_status
        if actionable:
            self.stdout.write(json.dumps(snapshot.payload, ensure_ascii=False, indent=2))
        else:
            self.stdout.write('NO_ACTION: gate verde e sem mudanca desde o snapshot anterior.')
