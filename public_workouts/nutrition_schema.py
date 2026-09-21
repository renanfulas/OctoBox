"""
ARQUIVO: schema do payload de PublicWorkoutMealPlan (Entrega 6, Fase 4 —
docs/plans/public-workouts-escala-e-nutricao-corda.md, D.6/ADR-6).

POR QUE ELE EXISTE:
- ADR-6 reverteu a proposta original ("payload livre, forma decidida pela
  nutricionista") depois da Revisão 3 do GTM (§7.6): o dono do produto
  pediu pra nascer estruturado desde o v1. Mesma filosofia de schema.py
  (contrato do treino): valida a mao, sem lib externa, schema_version
  proprio — mas este e' o contrato do plano ALIMENTAR, independente do
  `version` do model (um e' "forma do JSON", o outro e' "revisao do
  conteudo nutricional daquele aluno").

PONTOS CRITICOS:
- Desenhado a partir dos dois casos reais de dieta que ja existem no HTML
  legado (rafael.html, bruno.html — este com tabela de substituicao por
  funcao). Macros por item sao OPCIONAIS de proposito: a nutricionista
  nem sempre quebra o macro por alimento, so o total da refeicao/dia — nao
  forcar granularidade que o HTML legado tambem nao tinha.
- Campos aditivos (ex.: `substitutes`, `note`) nunca quebram payload
  antigo ao adicionar campo novo — mesma regra de schema.py.
"""

from __future__ import annotations

NUTRITION_SCHEMA_VERSION = 1

MACRO_KEYS = ('kcal', 'protein_g', 'carbs_g', 'fat_g')


class NutritionPayloadValidationError(ValueError):
    """Levantado por assert_valid_payload quando o payload nao segue o schema."""


def _require(condition: bool, errors: list[str], message: str) -> None:
    if not condition:
        errors.append(message)


def _validate_macros(macros: dict, *, path: str, errors: list[str], required: bool) -> None:
    if macros is None:
        _require(not required, errors, f'{path}: obrigatorio')
        return
    if not isinstance(macros, dict):
        errors.append(f'{path}: precisa ser um objeto ou null')
        return
    for key in MACRO_KEYS:
        value = macros.get(key)
        _require(
            isinstance(value, (int, float)) and value >= 0,
            errors,
            f'{path}.{key}: obrigatorio, numero >= 0',
        )


def _validate_item(item: dict, *, path: str, errors: list[str]) -> None:
    if not isinstance(item, dict):
        errors.append(f'{path}: precisa ser um objeto')
        return

    _require(isinstance(item.get('food'), str) and item['food'], errors, f'{path}.food: obrigatorio, string nao vazia')
    _require(
        isinstance(item.get('quantity'), str) and item['quantity'],
        errors,
        f'{path}.quantity: obrigatorio, string nao vazia',
    )

    # Macros por item sao opcionais (ver docstring do modulo) — quando
    # presentes, todas as 4 chaves precisam estar corretas.
    macro_keys_present = any(key in item for key in MACRO_KEYS)
    if macro_keys_present:
        _validate_macros(item, path=path, errors=errors, required=False)


def _validate_substitute(substitute: dict, *, path: str, errors: list[str]) -> None:
    _require(
        isinstance(substitute, dict)
        and isinstance(substitute.get('food'), str) and substitute.get('food')
        and isinstance(substitute.get('quantity'), str) and substitute.get('quantity'),
        errors,
        f'{path}: objeto com food/quantity string nao vazia',
    )


def _validate_meal(meal: dict, *, path: str, errors: list[str], seen_meal_ids: set[str]) -> None:
    if not isinstance(meal, dict):
        errors.append(f'{path}: precisa ser um objeto')
        return

    meal_id = meal.get('meal_id')
    _require(isinstance(meal_id, str) and meal_id, errors, f'{path}.meal_id: obrigatorio, string nao vazia')
    if isinstance(meal_id, str) and meal_id:
        _require(meal_id not in seen_meal_ids, errors, f'{path}.meal_id: {meal_id!r} duplicado — precisa ser unico no payload')
        seen_meal_ids.add(meal_id)

    _require(isinstance(meal.get('label'), str) and meal['label'], errors, f'{path}.label: obrigatorio, string nao vazia')

    time_value = meal.get('time')
    _require(time_value is None or isinstance(time_value, str), errors, f'{path}.time: string HH:MM ou ausente')

    items = meal.get('items')
    _require(isinstance(items, list) and len(items) > 0, errors, f'{path}.items: lista nao vazia')
    if isinstance(items, list):
        for index, item in enumerate(items):
            _validate_item(item, path=f'{path}.items[{index}]', errors=errors)

    substitutes = meal.get('substitutes')
    if substitutes is not None:
        _require(isinstance(substitutes, list), errors, f'{path}.substitutes: lista ou ausente')
        if isinstance(substitutes, list):
            for index, substitute in enumerate(substitutes):
                _validate_substitute(substitute, path=f'{path}.substitutes[{index}]', errors=errors)

    note = meal.get('note')
    _require(note is None or isinstance(note, str), errors, f'{path}.note: string ou ausente')


def validate_payload(payload: dict) -> list[str]:
    """Valida um payload de PublicWorkoutMealPlan contra o contrato de D.6.

    Nao levanta excecao — devolve a lista de erros (vazia = valido). Mesmo
    contrato de public_workouts.schema.validate_payload.
    """
    errors: list[str] = []

    if not isinstance(payload, dict):
        return ['payload: precisa ser um objeto']

    _require(
        payload.get('schema_version') == NUTRITION_SCHEMA_VERSION,
        errors,
        f'schema_version: precisa ser {NUTRITION_SCHEMA_VERSION}',
    )

    _validate_macros(payload.get('daily_targets'), path='daily_targets', errors=errors, required=True)

    meals = payload.get('meals')
    _require(isinstance(meals, list) and len(meals) > 0, errors, 'meals: lista nao vazia')
    if isinstance(meals, list):
        seen_meal_ids: set[str] = set()
        for index, meal in enumerate(meals):
            _validate_meal(meal, path=f'meals[{index}]', errors=errors, seen_meal_ids=seen_meal_ids)

    return errors


def assert_valid_payload(payload: dict) -> None:
    """Mesma validacao de validate_payload, levantando NutritionPayloadValidationError se houver erro."""
    errors = validate_payload(payload)
    if errors:
        raise NutritionPayloadValidationError('; '.join(errors))


def build_example_payload() -> dict:
    """Payload minimo e valido — usado pelos testes deste modulo."""
    return {
        'schema_version': NUTRITION_SCHEMA_VERSION,
        'daily_targets': {'kcal': 2400, 'protein_g': 180, 'carbs_g': 260, 'fat_g': 70},
        'meals': [
            {
                'meal_id': 'refeicao-1',
                'label': 'Café da manhã',
                'time': '07:00',
                'items': [
                    {'food': 'Ovo inteiro', 'quantity': '3 unidades', 'kcal': 210, 'protein_g': 18, 'carbs_g': 1.5, 'fat_g': 15},
                ],
                'substitutes': [
                    {'food': 'Tapioca', 'quantity': '2 unidades pequenas'},
                ],
                'note': 'Pode trocar o café por lanche se treinar em jejum.',
            },
        ],
    }
