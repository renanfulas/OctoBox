"""
ARQUIVO: comando institucional para disparar imports noturnos de leads.

POR QUE ELE EXISTE:
- conecta os jobs `async_night` a um scheduler simples sem exigir infraestrutura nova.
- impede disparos fora da janela economica oficial.

O QUE ESTE ARQUIVO FAZ:
1. valida se a hora local atual esta dentro da janela configurada.
2. varre os boxes ativos e, dentro do schema de cada um, verifica se existem jobs
   noturnos elegiveis para a janela atual.
3. dispara a task `dispatch_nightly_lead_import_jobs` por box quando houver trabalho.
4. permite forcar execucao manual para operacao e testes.

PONTOS CRITICOS:
- a janela usa hora local do projeto para evitar ambiguidade operacional; ela e
  global e por isso e avaliada FORA da varredura por tenant.
- `LeadImportJob` e model TENANT: contagem e disparo precisam rodar dentro do
  schema do box, via `sweep_active_tenants`.
- hoje `.delay()` executa em processo (o projeto nao tem Celery instalado; ver o
  shim de `shared_task` em `operations/tasks.py`), entao o disparo herda o schema
  da varredura. Se Celery entrar no stack, o worker roda em outro processo e o
  schema PRECISA viajar no payload da task, senao este comando volta a falhar.
- o scheduler externo deve chamar este comando recorrentemente, por exemplo a cada 30 minutos entre 00h e 04h.
"""

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from operations.services.lead_import_jobs import count_due_nightly_lead_import_jobs
from operations.tasks import dispatch_nightly_lead_import_jobs
from shared_support.tenant_sweep import (
    add_tenant_sweep_arguments,
    sweep_active_tenants,
    write_tenant_sweep_summary,
)


def is_within_night_window(*, current_time, start_hour: int, end_hour: int) -> bool:
    current_hour = current_time.hour
    if start_hour == end_hour:
        return True
    if start_hour < end_hour:
        return start_hour <= current_hour < end_hour
    return current_hour >= start_hour or current_hour < end_hour


class Command(BaseCommand):
    help = 'Dispara a fila noturna de imports de leads dentro da janela configurada.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=0,
            help='Limita quantos jobs noturnos entram no sweep desta execucao, por box.',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Executa mesmo fora da janela noturna configurada.',
        )
        add_tenant_sweep_arguments(parser)

    def handle(self, *args, **options):
        limit = options.get('limit') or getattr(settings, 'LEAD_IMPORT_NIGHT_SWEEP_LIMIT', 25)
        if limit <= 0:
            limit = getattr(settings, 'LEAD_IMPORT_NIGHT_SWEEP_LIMIT', 25)

        start_hour = getattr(settings, 'LEAD_IMPORT_NIGHT_WINDOW_START_HOUR', 0)
        end_hour = getattr(settings, 'LEAD_IMPORT_NIGHT_WINDOW_END_HOUR', 4)
        force = options.get('force', False)
        local_now = timezone.localtime()

        if not force and not is_within_night_window(
            current_time=local_now,
            start_hour=start_hour,
            end_hour=end_hour,
        ):
            self.stdout.write(
                self.style.WARNING(
                    'Fora da janela noturna de imports. '
                    f'Agora: {local_now:%H:%M}. Janela configurada: {start_hour:02d}h-{end_hour:02d}h.'
                )
            )
            return

        def _dispatch_for_box(box):
            due_jobs_count = count_due_nightly_lead_import_jobs(now=local_now)
            if not due_jobs_count:
                return {'due_jobs_count': 0, 'task_id': ''}
            async_result = dispatch_nightly_lead_import_jobs.delay(limit=limit)
            return {
                'due_jobs_count': due_jobs_count,
                'task_id': getattr(async_result, 'id', ''),
            }

        sweep = sweep_active_tenants(
            _dispatch_for_box,
            only_schema=options.get('schema') or '',
        )

        total_due = sum((result or {}).get('due_jobs_count', 0) for _, result in sweep.results)
        if not total_due:
            self.stdout.write(
                self.style.WARNING(
                    'Nenhum import noturno pendente para esta janela.'
                )
            )
            write_tenant_sweep_summary(self, sweep)
            return

        task_ids = [
            (result or {}).get('task_id', '')
            for _, result in sweep.results
            if (result or {}).get('task_id')
        ]
        task_label = ', '.join(task_ids) if task_ids else 'execucao_local'
        self.stdout.write(
            self.style.SUCCESS(
                'Sweep noturno de imports disparado. '
                f'Pendentes elegiveis: {total_due}. Limite: {limit}. Task: {task_label}.'
            )
        )
        write_tenant_sweep_summary(self, sweep)
