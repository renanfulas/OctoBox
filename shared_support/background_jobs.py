"""
ARQUIVO: executor de tarefas assincronas (Facade).

POR QUE ELE EXISTE:
- Fornece execucao em background sem depender inicialmente do Celery (usa threading puro + Redis).
- Permite que processos pesados (como importacao de CSVs) rodem sem travar o request do usuario.

O QUE ESTE ARQUIVO FAZ:
1. Gera um job_id e registra o estado inicial no Redis.
2. Lanca uma Thread (daemon=True) para executar a funcao.
3. Atualiza o status, progresso e erros parciais da execucao.
4. Expoe API legivel para enfileirar e consultar status no front-end.

PONTOS CRITICOS:
- Threads nao sobrevivem ao restart do gunicorn/servidor. Para volume maior,
  basta trocar o backend desta facade para Celery (`job.delay()`). O contrato externo
  continuara o mesmo.
"""

import logging
import threading
import uuid
from typing import Any, Callable, Dict, List, Optional

from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)

# Constants
JOB_PREFIX = "octobox:job_status:"
DEFAULT_EXPIRE_SECONDS = 3600 * 24  # Guarda o status por 24 horas

class JobStatus:
    PENDING = 'pending'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'


def create_job(job_name: str, total_items: int = 100, metadata: Optional[Dict] = None) -> str:
    """Cria um registro de job e retorna seu ID unico."""
    job_id = str(uuid.uuid4())
    job_data = {
        'id': job_id,
        'name': job_name,
        'status': JobStatus.PENDING,
        'progress': 0,
        'total': total_items,
        'created_at': timezone.now().isoformat(),
        'updated_at': timezone.now().isoformat(),
        'error_message': None,
        'metadata': metadata or {},
        'failed_items': []
    }
    _save_job(job_id, job_data)
    return job_id


def get_job_status(job_id: str) -> Optional[Dict]:
    """Retorna o estado atual do job."""
    return cache.get(f"{JOB_PREFIX}{job_id}")


def update_job_progress(job_id: str, items_processed: int, failed_item: Optional[Dict] = None):
    """Atualiza o progresso no Redis. Optimizacao: evite chamar por loop (ex: a cada 10)."""
    job_data = get_job_status(job_id)
    if not job_data:
        return

    job_data['progress'] += items_processed
    job_data['updated_at'] = timezone.now().isoformat()
    if job_data['status'] == JobStatus.PENDING:
        job_data['status'] = JobStatus.RUNNING

    if failed_item:
        if 'failed_items' not in job_data:
            job_data['failed_items'] = []
        job_data['failed_items'].append(failed_item)

    _save_job(job_id, job_data)


def mark_job_completed(job_id: str):
    job_data = get_job_status(job_id)
    if not job_data:
        return
    job_data['status'] = JobStatus.COMPLETED
    job_data['progress'] = job_data['total']
    job_data['updated_at'] = timezone.now().isoformat()
    _save_job(job_id, job_data)


def mark_job_failed(job_id: str, error_message: str):
    job_data = get_job_status(job_id)
    if not job_data:
        return
    job_data['status'] = JobStatus.FAILED
    job_data['error_message'] = error_message
    job_data['updated_at'] = timezone.now().isoformat()
    logger.error(f"Job {job_id} falhou: {error_message}")
    _save_job(job_id, job_data)


def _save_job(job_id: str, data: Dict):
    cache.set(f"{JOB_PREFIX}{job_id}", data, timeout=DEFAULT_EXPIRE_SECONDS)


# -----------------------------------------------------------------------------
# Coracao do Async: The Thread Runner
# -----------------------------------------------------------------------------

def submit_background_job(job_fn: Callable, job_id: str, *args, **kwargs):
    """
    Submete uma funcao pesada para background.
    
    Uso:
    job_id = create_job('import_students', total_items=100)
    submit_background_job(importar_csv_service, job_id, file_path)
    
    A funcao `job_fn` deve aceitar `job_id` para atualizar seu progresso via
    `update_job_progress(job_id, 1)` a cada 'n' linhas processadas.
    """
    def thread_worker():
        from django.db import connection
        try:
            # Envia a thread. Cuidado com requests fora da transacao web!
            job_fn(job_id, *args, **kwargs)
            mark_job_completed(job_id)
        except Exception as e:
            logger.exception(f"Erro nao tratado no job {job_id}")
            mark_job_failed(job_id, str(e))
        finally:
            # Em threads separadas, essencial fechar a conexao de banco manualmente
            # para evitar estourar o limite de conexoes do pool.
            connection.close()

    thread = threading.Thread(target=thread_worker, daemon=True)
    thread.start()
    return job_id
