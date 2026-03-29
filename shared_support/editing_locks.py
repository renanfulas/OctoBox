"""
ARQUIVO: gerenciador de locks de edicao com hierarquia de papeis.

POR QUE ELE EXISTE:
- Impede que dois usuarios editem o mesmo aluno ao mesmo tempo.
- Usa hierarquia de papeis: quem tem maior prioridade toma o lock de quem tem menor.

O QUE ESTE ARQUIVO FAZ:
1. Registra quem esta editando um aluno no Redis com TTL por papel.
2. Permite que papeis de maior prioridade tomem o lock de papeis menores.
3. Fornece heartbeat para renovar o lock enquanto o usuario esta ativo.
4. Expoe consulta de status para polling de frontend.

PONTOS CRITICOS:
- Dev nao participa do lock operacional (Opcao B aprovada).
- Timeouts: Owner = 20min, demais = 4h.
- Locks de 4h so bloqueiam o mesmo papel ou menor. Manager/Owner sempre podem tomar o lock.
- Se Redis estiver offline, o sistema degrada de forma segura (sem lock = aceita a edicao).
"""

import logging
from dataclasses import dataclass
from typing import Optional

from django.core.cache import cache
from django.utils import timezone

from access.roles import ROLE_COACH, ROLE_MANAGER, ROLE_OWNER, ROLE_RECEPTION

logger = logging.getLogger(__name__)

# -------------------------------------------------------------------
# Configuracao de hierarquia e timeouts
# -------------------------------------------------------------------

# Menor numero = maior prioridade (como posicao em fila VIP)
ROLE_LOCK_PRIORITY: dict[str, int] = {
    ROLE_OWNER: 1,
    ROLE_MANAGER: 2,
    ROLE_RECEPTION: 3,
    ROLE_COACH: 4,
}

# Timeout de inatividade por papel (em segundos)
# O heartbeat renova o TTL enquanto o usuario estiver ativo.
ROLE_LOCK_TIMEOUTS: dict[str, int] = {
    ROLE_OWNER: 20 * 60,        # 20 minutos
    ROLE_MANAGER: 4 * 60 * 60,  # 4 horas
    ROLE_RECEPTION: 4 * 60 * 60,
    ROLE_COACH: 4 * 60 * 60,
}

# Papeis que participam do lock operacional. Dev monitoriza, nao edita.
_LOCK_PARTICIPANTS = frozenset(ROLE_LOCK_PRIORITY.keys())

_CACHE_KEY_PREFIX = 'octobox:student_edit_lock'


def _cache_key(student_id: int) -> str:
    return f'{_CACHE_KEY_PREFIX}:{student_id}'


# -------------------------------------------------------------------
# Estrutura de resultado
# -------------------------------------------------------------------

@dataclass
class LockResult:
    """Resultado de uma tentativa de aquisicao de lock."""
    acquired: bool
    holder: Optional[dict] = None  # dados do detentor atual, se lock nao foi adquirido


# -------------------------------------------------------------------
# API publica
# -------------------------------------------------------------------

def acquire_student_lock(student_id: int, user, role_slug: str) -> LockResult:
    """
    Tenta adquirir o lock de edicao de um aluno.

    Regras:
    - Se nenhum lock existe: adquire.
    - Se o lock pertence a este usuario: renova (heartbeat implicito).
    - Se o lock pertence a um papel de MENOR prioridade: toma o lock.
    - Se o lock pertence a um papel de IGUAL ou MAIOR prioridade: rejeita.

    Se o papel do usuario nao participa do lock (ex: Dev): retorna acquired=True
    sem criar lock, para nao bloquear o fluxo.
    """
    if role_slug not in _LOCK_PARTICIPANTS:
        # Dev e papeis nao operacionais passam sem lock
        return LockResult(acquired=True)

    key = _cache_key(student_id)
    my_priority = ROLE_LOCK_PRIORITY.get(role_slug, 99)
    timeout = ROLE_LOCK_TIMEOUTS.get(role_slug, 4 * 60 * 60)

    try:
        existing = cache.get(key)
    except Exception:
        logger.warning('editing_locks: Redis indisponivel. Degradando sem lock.')
        return LockResult(acquired=True)

    # Sem lock ativo: adquire
    if not existing:
        _write_lock(key, user, role_slug, my_priority, timeout)
        return LockResult(acquired=True)

    # Ja e o mesmo usuario: renova o lock (reentrancia)
    if existing.get('user_id') == user.id:
        _write_lock(key, user, role_slug, my_priority, timeout)
        return LockResult(acquired=True)

    holder_priority = existing.get('role_priority', 99)

    # Tenho maior prioridade (numero menor): tomo o lock
    if my_priority < holder_priority:
        _write_lock(key, user, role_slug, my_priority, timeout)
        return LockResult(acquired=True)

    # Prioridade igual ou menor: nao posso tomar o lock
    return LockResult(acquired=False, holder=existing)


def release_student_lock(student_id: int, user_id: int) -> bool:
    """
    Libera o lock apenas se o usuario corrente for o detentor.
    Retorna True se o lock foi liberado.
    """
    key = _cache_key(student_id)
    try:
        existing = cache.get(key)
        if existing and existing.get('user_id') == user_id:
            cache.delete(key)
            return True
    except Exception:
        logger.warning('editing_locks: Falha ao liberar lock no Redis.')
    return False


def refresh_student_lock(student_id: int, user_id: int) -> bool:
    """
    Heartbeat: renova o TTL do lock enquanto o usuario esta ativo na pagina.
    Chamado pelo JS de polling a cada 5s.
    Retorna True se o lock ainda pertence ao usuario e foi renovado.
    """
    key = _cache_key(student_id)
    try:
        existing = cache.get(key)
        if existing and existing.get('user_id') == user_id:
            role_slug = existing.get('role_slug', ROLE_RECEPTION)
            timeout = ROLE_LOCK_TIMEOUTS.get(role_slug, 4 * 60 * 60)
            cache.set(key, existing, timeout=timeout)
            return True
    except Exception:
        logger.warning('editing_locks: Falha ao renovar lock no Redis.')
    return False


def get_student_lock_status(student_id: int) -> Optional[dict]:
    """
    Retorna os dados do lock atual ou None se nao houver lock.
    Usado pelo endpoint de polling do frontend.
    """
    key = _cache_key(student_id)
    try:
        return cache.get(key)
    except Exception:
        return None


# -------------------------------------------------------------------
# Internos
# -------------------------------------------------------------------

def _write_lock(key: str, user, role_slug: str, priority: int, timeout: int) -> None:
    """Grava o lock no Redis com os metadados do detentor."""
    lock_data = {
        'user_id': user.id,
        'user_display': _get_user_display(user),
        'role_slug': role_slug,
        'role_label': _get_role_label(role_slug),
        'role_priority': priority,
        'acquired_at': timezone.now().isoformat(),
    }
    try:
        cache.set(key, lock_data, timeout=timeout)
    except Exception:
        logger.warning('editing_locks: Falha ao gravar lock no Redis.')


def _get_user_display(user) -> str:
    """Retorna o nome de exibicao do usuario."""
    name = user.get_full_name()
    if name:
        return name
    return user.username


def _get_role_label(role_slug: str) -> str:
    """Retorna o label legivel do papel."""
    labels = {
        ROLE_OWNER: 'Owner',
        ROLE_MANAGER: 'Manager',
        ROLE_RECEPTION: 'Recepção',
        ROLE_COACH: 'Coach',
    }
    return labels.get(role_slug, role_slug)
