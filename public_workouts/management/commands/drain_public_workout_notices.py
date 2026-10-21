"""
ARQUIVO: comando que roda a regua de avisos e a trava de D+2 do corredor
de treinos (Onda B2 do CORDA).

POR QUE ELE EXISTE:
- roda num systemd timer (ver infra/hostgator-vps/systemd/
  octobox-public-workout-notices.timer), sem Celery (D.3 do CORDA).

PONTO CRITICO:
- Idempotente por design (ver public_workouts/billing.py::drain_due_notices):
  rodar duas vezes no mesmo minuto nao duplica envio nem reenvia
  suspensao (P1 do CORDA).
"""

from __future__ import annotations

from django.core.management.base import BaseCommand

from public_workouts.billing import drain_due_notices


class Command(BaseCommand):
    help = 'Envia avisos de cobranca vencidos e suspende assinaturas do corredor sem pagamento ha 2+ dias.'

    def handle(self, *args, **options):
        result = drain_due_notices()
        self.stdout.write(
            self.style.SUCCESS(
                f'avisos enviados={result["sent"]} pulados={result["skipped"]} suspensoes={result["suspended"]}'
            )
        )
