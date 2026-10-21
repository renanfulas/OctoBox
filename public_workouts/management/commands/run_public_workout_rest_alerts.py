import signal

from django.core.management.base import BaseCommand

from public_workouts.rest_alerts import RestAlertWorker, dispatch_due, expire_overdue


def _stop(_signum, _frame):
    # SystemExit interrompe a espera no socket na hora; um envio cortado no
    # meio vence pelo lease em vez de repetir um aviso atrasado.
    raise SystemExit(0)


class Command(BaseCommand):
    help = (
        'Worker do aviso push do fim do descanso (modo foco da Curva): dorme até o '
        'próximo horário pendente e envia na hora. Um só ativo por banco (advisory lock).'
    )

    def add_arguments(self, parser):
        parser.add_argument('--once', action='store_true', help='Envia o que já venceu e sai (diagnóstico).')
        parser.add_argument('--max-idle', type=float, default=15.0)

    def handle(self, *args, **options):
        if options['once']:
            expire_overdue()
            self.stdout.write(self.style.SUCCESS(str(dispatch_due())))
            return
        signal.signal(signal.SIGTERM, _stop)
        RestAlertWorker(max_idle=max(1.0, options['max_idle'])).run()
