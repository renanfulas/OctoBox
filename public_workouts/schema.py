"""
ARQUIVO: schema do payload do PublicWorkoutProgram (Onda S0 do CORDA).

POR QUE ELE EXISTE:
- e o contrato entre as duas frentes, fixado ANTES do codigo (D.5 do
  docs/plans/public-workouts-produtizacao-corda.md): a Frente A publica o
  programa (Ondas A1/A2) nesse formato; a Frente B consome via S1/S2 — contra
  o stub em services_stub.py ate A1 entregar de verdade — sem esperar nada
  da outra. Mudar um campo aqui exige acordo escrito das duas frentes
  ("Regras de convivencia" #3 do CORDA).

PONTOS CRITICOS:
- Sem lib externa de proposito: valida a mao, no estilo do resto do app
  (ver _validate_plan_slug em services.py) — nao adiciona dependencia nova
  so pra isso.
- Nada mutavel entra aqui (D.2, frase 2): e a PRESCRICAO publicada, nunca o
  que o aluno produz depois. Carga registrada vive em PublicWorkoutLoadLog
  (Onda A1), fora deste payload, referenciando (slug, version, movement_slug).
"""

from __future__ import annotations

SCHEMA_VERSION = 1

# Mesmo vocabulario de WorkoutLoadType (student_app/models.py) — o corredor
# copia o padrao (D.00), nao importa o enum do app principal.
LOAD_TYPES = ('free', 'fixed_kg', 'percentage_of_rm')

# Mesmo vocabulario de assessment_sex (PublicWorkoutPlan) — None e o caso
# neutro (D.3: --theme-accent-primary), so mapeado pra tema na Onda B3.
ACCENT_VARIANTS = ('F', 'M', None)


class PayloadValidationError(ValueError):
    """Levantado por assert_valid_payload quando o payload nao segue o schema."""


def _require(condition: bool, errors: list[str], message: str) -> None:
    if not condition:
        errors.append(message)


def _validate_movement(movement: dict, *, path: str, errors: list[str]) -> None:
    if not isinstance(movement, dict):
        errors.append(f'{path}: precisa ser um objeto')
        return

    _require(
        isinstance(movement.get('movement_slug'), str) and movement['movement_slug'],
        errors,
        f'{path}.movement_slug: obrigatorio, string nao vazia',
    )
    _require(isinstance(movement.get('reps_spec'), str), errors, f'{path}.reps_spec: obrigatorio, string (pode ser vazia)')
    _require(isinstance(movement.get('rir_spec'), str), errors, f'{path}.rir_spec: obrigatorio, string (pode ser vazia)')
    _require(isinstance(movement.get('is_tracked'), bool), errors, f'{path}.is_tracked: obrigatorio, bool')

    load_type = movement.get('load_type')
    _require(load_type in LOAD_TYPES, errors, f'{path}.load_type: precisa ser um de {LOAD_TYPES}')

    load_value = movement.get('load_value')
    _require(
        load_value is None or isinstance(load_value, (int, float)),
        errors,
        f'{path}.load_value: numero ou null',
    )

    reference_url = movement.get('reference_url')
    _require(
        reference_url is None or isinstance(reference_url, str),
        errors,
        f'{path}.reference_url: string ou null',
    )


def _validate_block(block: dict, *, path: str, errors: list[str]) -> None:
    if not isinstance(block, dict):
        errors.append(f'{path}: precisa ser um objeto')
        return

    movements = block.get('movements')
    _require(isinstance(movements, list) and len(movements) > 0, errors, f'{path}.movements: lista nao vazia')
    if isinstance(movements, list):
        for index, movement in enumerate(movements):
            _validate_movement(movement, path=f'{path}.movements[{index}]', errors=errors)


def _validate_day(day: dict, *, path: str, errors: list[str]) -> None:
    if not isinstance(day, dict):
        errors.append(f'{path}: precisa ser um objeto')
        return

    _require(isinstance(day.get('day_id'), str) and day['day_id'], errors, f'{path}.day_id: obrigatorio, string nao vazia')
    _require(isinstance(day.get('label'), str) and day['label'], errors, f'{path}.label: obrigatorio, string nao vazia')

    blocks = day.get('blocks')
    _require(isinstance(blocks, list) and len(blocks) > 0, errors, f'{path}.blocks: lista nao vazia')
    if isinstance(blocks, list):
        for index, block in enumerate(blocks):
            _validate_block(block, path=f'{path}.blocks[{index}]', errors=errors)


def validate_payload(payload: dict) -> list[str]:
    """Valida um payload de PublicWorkoutProgram contra o contrato da Onda S0.

    Nao levanta excecao — devolve a lista de erros (vazia = valido). Quem
    chama decide o que fazer com eles (publish_program, na Onda A1, vira
    PayloadValidationError via assert_valid_payload).
    """
    errors: list[str] = []

    if not isinstance(payload, dict):
        return ['payload: precisa ser um objeto']

    _require(payload.get('schema_version') == SCHEMA_VERSION, errors, f'schema_version: precisa ser {SCHEMA_VERSION}')
    _require(
        isinstance(payload.get('program_id'), str) and payload['program_id'],
        errors,
        'program_id: obrigatorio, string nao vazia',
    )
    _require(
        isinstance(payload.get('program_label'), str) and payload['program_label'],
        errors,
        'program_label: obrigatorio, string nao vazia',
    )
    _require(
        isinstance(payload.get('started_on'), str) and payload['started_on'],
        errors,
        'started_on: obrigatorio, string ISO (YYYY-MM-DD)',
    )
    _require(isinstance(payload.get('weeks'), int) and payload['weeks'] > 0, errors, 'weeks: obrigatorio, inteiro positivo')

    accent_variant = payload.get('accent_variant')
    _require(accent_variant in ACCENT_VARIANTS, errors, f'accent_variant: precisa ser um de {ACCENT_VARIANTS!r}')

    days = payload.get('days')
    _require(isinstance(days, list) and len(days) > 0, errors, 'days: lista nao vazia')
    if isinstance(days, list):
        for index, day in enumerate(days):
            _validate_day(day, path=f'days[{index}]', errors=errors)

    return errors


def assert_valid_payload(payload: dict) -> None:
    """Mesma validacao de validate_payload, levantando PayloadValidationError se houver erro."""
    errors = validate_payload(payload)
    if errors:
        raise PayloadValidationError('; '.join(errors))


def build_example_payload() -> dict:
    """Payload minimo e valido — usado pelo teste deste modulo e pelo stub de S0/services_stub.py."""
    return {
        'schema_version': SCHEMA_VERSION,
        'program_id': 'exemplo-2026-q1',
        'program_label': 'Programa de exemplo',
        'started_on': '2026-01-05',
        'weeks': 4,
        'accent_variant': None,
        'days': [
            {
                'day_id': 'seg',
                'label': 'Segunda',
                'blocks': [
                    {
                        'movements': [
                            {
                                'movement_slug': 'agachamento-livre',
                                'reps_spec': '3x8-10',
                                'rir_spec': 'RIR 2',
                                'is_tracked': True,
                                'load_type': 'percentage_of_rm',
                                'load_value': 75.0,
                                'reference_url': None,
                            },
                        ],
                    },
                ],
            },
        ],
    }
