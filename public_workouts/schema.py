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

    # `name`/`variations` sao ADITIVOS (movimento publicado antes desta
    # fatia nao tem essas chaves) -- so' validam a FORMA quando presentes,
    # nunca exigem.
    name = movement.get('name')
    _require(name is None or isinstance(name, str), errors, f'{path}.name: string ou ausente')

    variations = movement.get('variations')
    if variations is not None:
        _require(isinstance(variations, list), errors, f'{path}.variations: lista ou ausente')
        if isinstance(variations, list):
            for vindex, variation in enumerate(variations):
                _require(
                    isinstance(variation, dict)
                    and isinstance(variation.get('label'), str) and variation.get('label')
                    and isinstance(variation.get('reference_url'), str) and variation.get('reference_url'),
                    errors,
                    f'{path}.variations[{vindex}]: objeto com label/reference_url string nao vazia',
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


def _validate_cardio_session(session: dict, *, path: str, errors: list[str]) -> None:
    if not isinstance(session, dict):
        errors.append(f'{path}: precisa ser um objeto')
        return
    _require(isinstance(session.get('title'), str) and session['title'], errors, f'{path}.title: obrigatorio, string nao vazia')
    _require(isinstance(session.get('badge'), str), errors, f'{path}.badge: obrigatorio, string (pode ser vazia)')
    _require(isinstance(session.get('note'), str), errors, f'{path}.note: obrigatorio, string (pode ser vazia)')
    details = session.get('details')
    _require(isinstance(details, list), errors, f'{path}.details: lista (pode ser vazia)')
    if isinstance(details, list):
        for index, detail in enumerate(details):
            _require(
                isinstance(detail, dict) and isinstance(detail.get('label'), str) and isinstance(detail.get('value'), str),
                errors,
                f'{path}.details[{index}]: objeto com label/value string',
            )


def _validate_cardio(cardio: dict, *, errors: list[str]) -> None:
    if not isinstance(cardio, dict):
        errors.append('cardio: precisa ser um objeto')
        return
    sessions = cardio.get('sessions')
    _require(isinstance(sessions, list) and len(sessions) > 0, errors, 'cardio.sessions: lista nao vazia')
    if isinstance(sessions, list):
        for index, session in enumerate(sessions):
            _validate_cardio_session(session, path=f'cardio.sessions[{index}]', errors=errors)


def _validate_periodization_row(row: dict, *, path: str, required_keys: tuple[str, ...], errors: list[str]) -> None:
    if not isinstance(row, dict):
        errors.append(f'{path}: precisa ser um objeto')
        return
    for key in required_keys:
        _require(isinstance(row.get(key), str), errors, f'{path}.{key}: obrigatorio, string')


def _validate_periodization(periodization: dict, *, errors: list[str]) -> None:
    if not isinstance(periodization, dict):
        errors.append('periodization: precisa ser um objeto')
        return

    weeks_table = periodization.get('weeks_table')
    _require(isinstance(weeks_table, list) and len(weeks_table) > 0, errors, 'periodization.weeks_table: lista nao vazia')
    if isinstance(weeks_table, list):
        for index, row in enumerate(weeks_table):
            _validate_periodization_row(
                row, path=f'periodization.weeks_table[{index}]',
                required_keys=('week', 'focus', 'reps', 'guidance'), errors=errors,
            )

    volume_table = periodization.get('volume_table')
    _require(isinstance(volume_table, list), errors, 'periodization.volume_table: lista (pode ser vazia)')
    if isinstance(volume_table, list):
        for index, row in enumerate(volume_table):
            _validate_periodization_row(
                row, path=f'periodization.volume_table[{index}]',
                required_keys=('muscle_group', 'sets_per_week', 'frequency', 'where'), errors=errors,
            )

    _require(isinstance(periodization.get('note'), str), errors, 'periodization.note: obrigatorio, string (pode ser vazia)')

    chart = periodization.get('chart')
    _require(isinstance(chart, list), errors, 'periodization.chart: lista (pode ser vazia)')
    if isinstance(chart, list):
        for index, point in enumerate(chart):
            if not isinstance(point, dict):
                errors.append(f'periodization.chart[{index}]: precisa ser um objeto')
                continue
            for key in ('label', 'focus', 'reps', 'color', 'bg', 'fg'):
                _require(isinstance(point.get(key), str) and point[key], errors, f'periodization.chart[{index}].{key}: obrigatorio, string nao vazia')
            _require(
                isinstance(point.get('h'), (int, float)) and 0 <= point['h'] <= 100,
                errors,
                f'periodization.chart[{index}].h: numero entre 0 e 100',
            )


def validate_payload(payload: dict) -> list[str]:
    """Valida um payload de PublicWorkoutProgram contra o contrato da Onda S0.

    Nao levanta excecao — devolve a lista de erros (vazia = valido). Quem
    chama decide o que fazer com eles (publish_program, na Onda A1, vira
    PayloadValidationError via assert_valid_payload).

    `cardio`/`periodization` sao OPCIONAIS (Onda A2, fatia de cardio/
    periodizacao) — ausentes = cliente sem essa aba no HTML legado original
    (ver parser.py). Adicao aditiva ao contrato congelado (D.5): nenhum
    campo existente muda de forma, so' duas chaves novas de nivel superior.
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

    if payload.get('cardio') is not None:
        _validate_cardio(payload['cardio'], errors=errors)

    if payload.get('periodization') is not None:
        _validate_periodization(payload['periodization'], errors=errors)

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
