"""
ARQUIVO: stub temporario de S1/S2/S3 (Onda S0 do CORDA).

POR QUE ELE EXISTE:
- desacopla as duas frentes desde o dia 1 (D.5 do
  docs/plans/public-workouts-produtizacao-corda.md): enquanto a Frente A
  nao entrega get_active_program/build_student_package/record_load de
  verdade (Onda A1), a Frente B programa views e templates contra este
  stub, que devolve payload valido pelo schema (ver schema.py) sem tocar
  banco.

PONTOS CRITICOS:
- DELETAR NA ONDA A2: quando public_workouts/services.py ganhar as funcoes
  de verdade, com esses MESMOS nomes e assinaturas (D.5 — congeladas;
  mudar exige acordo escrito das duas frentes). Ate la, quem importar de
  services_stub troca o import para services quando A2 fechar.
- Nao persiste nada, nao le banco, nao valida slug contra a biblioteca real
  — isso e trabalho de quem consome o stub.
"""

from __future__ import annotations

from .schema import build_example_payload


def get_active_program(*, slug: str) -> dict | None:
    """Stub de S1 — sempre devolve um payload de exemplo, nunca None."""
    payload = build_example_payload()
    payload['program_id'] = f'{slug}-stub'
    return payload


def build_student_package(*, student_identity_id: int, slug: str) -> dict:
    """Stub de S2 — carga, 1RM e substituicoes vazios; acesso aberto (sem trava)."""
    return {
        'last_load_by_movement': {},
        'one_rep_max_by_movement': {},
        'substitutions': {},
        'access_until': None,
    }


def record_load(
    *,
    student_identity_id: int,
    movement_slug: str,
    weight_kg,
    reps=None,
    rir=None,
    performed_on,
    program_id=None,
    week_in_program=None,
    idempotency_key: str,
) -> dict:
    """Stub de S3 — nao persiste nada, so ecoa o que recebeu."""
    return {
        'student_identity_id': student_identity_id,
        'movement_slug': movement_slug,
        'weight_kg': weight_kg,
        'reps': reps,
        'rir': rir,
        'performed_on': performed_on,
        'program_id': program_id,
        'week_in_program': week_in_program,
        'idempotency_key': idempotency_key,
    }
