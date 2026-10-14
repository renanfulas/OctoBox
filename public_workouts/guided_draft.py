"""Prepara propostas de séries em rascunhos, sem tocar em programas publicados."""

from copy import deepcopy

from .guided_prescription import propose_guided_prescription, validate_guided_prescription


def prepare_guided_payload(payload: dict) -> tuple[dict, int, int]:
    """Devolve cópia do payload, quantidade preparada e casos para revisão manual."""
    prepared_payload = deepcopy(payload)
    prepared = unresolved = 0
    for day in prepared_payload.get('days', []):
        for block in day.get('blocks', []):
            for movement in block.get('movements', []):
                if movement.get('guided_prescription') is not None:
                    continue
                proposal = propose_guided_prescription(movement)
                if proposal is None or validate_guided_prescription(proposal):
                    unresolved += 1
                    continue
                movement['guided_prescription'] = proposal
                prepared += 1
    return prepared_payload, prepared, unresolved
