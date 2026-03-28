"""
ARQUIVO: utilitario generico para execucao de operacoes em lote.

POR QUE ELE EXISTE:
- Centraliza a logica de partial-commit e tratamento de falhas em acoes em lote.

O QUE ESTE ARQUIVO FAZ:
1. Recebe uma lista de itens e uma funcao de acao.
2. Executa a acao para cada item dentro de uma transacao atomica segura (savepoint parcial).
3. Se um item falha, faz o rollback apenas dele e continua com o restante.
4. Retorna um relatorio unificado com sucessos e falhas detalhadas.

PONTOS CRITICOS:
- Usado em listagens como a grade de alunos para realizar atualizacoes multiplas.
"""

import logging
from typing import Any, Callable, Dict, Iterable, List

from django.db import transaction

logger = logging.getLogger(__name__)


def execute_bulk_action(items: Iterable[Any], action_fn: Callable[[Any], None]) -> Dict[str, List[Any]]:
    """
    Executa uma funcaon para cada item de forma assincrona isolada (partial commit).
    
    Se `action_fn(item)` levantar uma excecao, apenas o item que gerou o erro sofre
    rollback preservando as operacoes bem-sucedidas.
    
    Retorno:
    {
        'success': [item1, item2],
        'failed': [
            {'item': item3, 'error': 'Motivo do erro'},
        ]
    }
    """
    results = {
        'success': [],
        'failed': []
    }

    for item in items:
        # Cria um savepoint (transação parcial) para isolar o item atual.
        # Assim protegemos as alterações dos outros itens na transação principal.
        try:
            with transaction.atomic():
                action_fn(item)
            results['success'].append(item)
        except Exception as e:
            logger.exception(f"Erro em bulk operations no item {item}: {str(e)}")
            results['failed'].append({
                'item': item,
                'error': str(e) or repr(e)
            })

    return results
