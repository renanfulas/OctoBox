"""
ARQUIVO: builders da leitura de revisao do WOD.

POR QUE ELE EXISTE:
- tira de `workout_board_builders.py` o corredor de preview, diff e assistencia de decisao.
"""

from django.utils import timezone

from student_app.application.use_cases import (
    build_student_prescription_label,
    build_student_recommendation_preview,
)
from student_app.models import SessionWorkoutMovement, SessionWorkoutRevisionEvent


def build_snapshot_blocks(snapshot):
    normalized_blocks = []
    for block in snapshot.get('blocks', []):
        normalized_movements = []
        for movement in block.get('movements', []):
            normalized_movements.append(
                {
                    'sort_order': movement.get('sort_order') or 0,
                    'movement_slug': movement.get('movement_slug', ''),
                    'movement_label': movement.get('movement_label', ''),
                    'sets': movement.get('sets'),
                    'reps': movement.get('reps'),
                    'load_type': movement.get('load_type', ''),
                    'load_value': movement.get('load_value', ''),
                    'notes': movement.get('notes', ''),
                }
            )
        normalized_blocks.append(
            {
                'sort_order': block.get('sort_order') or 0,
                'title': block.get('title', ''),
                'kind': block.get('kind', ''),
                'kind_label': block.get('kind_label') or block.get('kind', ''),
                'notes': block.get('notes', ''),
                'movements': normalized_movements,
            }
        )
    return normalized_blocks


def build_snapshot_presentation(snapshot):
    blocks = build_snapshot_blocks(snapshot)
    total_movements = sum(len(block['movements']) for block in blocks)
    return {
        'title': snapshot.get('title', ''),
        'coach_notes': snapshot.get('coach_notes', ''),
        'version': snapshot.get('version'),
        'status': snapshot.get('status', ''),
        'block_count': len(blocks),
        'movement_count': total_movements,
        'blocks': blocks,
    }


def normalize_load_type_label(load_type):
    return dict(SessionWorkoutMovement._meta.get_field('load_type').choices).get(load_type, load_type or '-')


def build_student_preview_payload(*, session_title, session_scheduled_label, coach_name, workout_title, coach_notes, blocks):
    preview_blocks = []
    for block in blocks:
        block_title = block.get('title') if isinstance(block, dict) else block.title
        block_kind_label = block.get('kind_label') if isinstance(block, dict) else block.get_kind_display()
        block_notes = block.get('notes', '') if isinstance(block, dict) else block.notes
        block_movements = block.get('movements', []) if isinstance(block, dict) else block.movements.all()
        preview_movements = []
        for movement in block_movements:
            load_context_label, recommended_load, recommendation_copy = build_student_recommendation_preview(movement=movement)
            load_type = movement.get('load_type') if isinstance(movement, dict) else movement.load_type
            recommendation_label = (
                f'{recommended_load} kg'
                if recommended_load is not None and load_type != 'fixed_kg'
                else (f'{recommended_load} kg' if recommended_load is not None else 'Sem carga automatica')
            )
            movement_label = movement.get('movement_label') if isinstance(movement, dict) else movement.movement_label
            movement_notes = movement.get('notes', '') if isinstance(movement, dict) else movement.notes
            preview_movements.append(
                {
                    'movement_label': movement_label,
                    'prescription_label': build_student_prescription_label(movement=movement),
                    'load_context_label': load_context_label,
                    'recommendation_label': recommendation_label,
                    'recommendation_copy': recommendation_copy,
                    'notes': movement_notes,
                }
            )
        preview_blocks.append(
            {
                'title': block_title,
                'kind_label': block_kind_label,
                'notes': block_notes,
                'movements': preview_movements,
            }
        )
    return {
        'session_title': session_title,
        'session_scheduled_label': session_scheduled_label,
        'coach_name': coach_name,
        'workout_title': workout_title,
        'coach_notes': coach_notes,
        'blocks': preview_blocks,
    }


def build_student_preview_diff(*, previous_preview, current_preview):
    if previous_preview is None:
        return {
            'has_previous_preview': False,
            'summary': 'Esse sera o primeiro preview oficial visto pelo aluno nesta aula.',
            'changed_cards': [],
            'added_blocks': [],
            'removed_blocks': [],
            'coach_notes_changed': False,
        }

    previous_blocks = {(block['title'], block['kind_label']): block for block in previous_preview['blocks']}
    current_blocks = {(block['title'], block['kind_label']): block for block in current_preview['blocks']}
    added_blocks = sorted(block[0] for block in current_blocks.keys() - previous_blocks.keys() if block[0])
    removed_blocks = sorted(block[0] for block in previous_blocks.keys() - current_blocks.keys() if block[0])
    changed_cards = []
    for block_key in sorted(previous_blocks.keys() & current_blocks.keys()):
        previous_block = previous_blocks[block_key]
        current_block = current_blocks[block_key]
        previous_movements = {movement['movement_label']: movement for movement in previous_block['movements']}
        current_movements = {movement['movement_label']: movement for movement in current_block['movements']}
        for movement_label in sorted(previous_movements.keys() & current_movements.keys()):
            previous_movement = previous_movements[movement_label]
            current_movement = current_movements[movement_label]
            changed_fields = []
            for field_key, field_label in (
                ('prescription_label', 'prescricao'),
                ('load_context_label', 'contexto de carga'),
                ('recommendation_label', 'carga recomendada'),
                ('recommendation_copy', 'texto de apoio'),
                ('notes', 'nota do movimento'),
            ):
                if previous_movement.get(field_key, '') != current_movement.get(field_key, ''):
                    changed_fields.append(field_label)
            if changed_fields:
                changed_cards.append(
                    {
                        'block_title': current_block['title'],
                        'movement_label': movement_label,
                        'changed_fields': changed_fields,
                        'previous_prescription_label': previous_movement.get('prescription_label', ''),
                        'current_prescription_label': current_movement.get('prescription_label', ''),
                        'previous_recommendation_label': previous_movement.get('recommendation_label', ''),
                        'current_recommendation_label': current_movement.get('recommendation_label', ''),
                    }
                )
    coach_notes_changed = previous_preview.get('coach_notes', '') != current_preview.get('coach_notes', '')
    summary_bits = []
    if coach_notes_changed:
        summary_bits.append('mensagem do coach mudou')
    if added_blocks:
        summary_bits.append(f'{len(added_blocks)} bloco(s) novo(s) no app do aluno')
    if removed_blocks:
        summary_bits.append(f'{len(removed_blocks)} bloco(s) sairam do app do aluno')
    if changed_cards:
        summary_bits.append(f'{len(changed_cards)} cartao(oes) de movimento mudaram para o aluno')
    return {
        'has_previous_preview': True,
        'summary': ', '.join(summary_bits) if summary_bits else 'A experiencia final do aluno continua equivalente a ultima versao publicada.',
        'changed_cards': changed_cards[:6],
        'added_blocks': added_blocks[:4],
        'removed_blocks': removed_blocks[:4],
        'coach_notes_changed': coach_notes_changed,
    }


def build_workout_decision_assist(*, workout, diff_snapshot, student_preview_diff):
    impact_score = 0
    reasons = []
    priority_flags = []

    if diff_snapshot['is_sensitive']:
        impact_score += 4
        reasons.append('Mudancas sensiveis na prescricao')
        priority_flags.append({'label': 'Mudanca sensivel', 'tone': 'danger'})
    if student_preview_diff['changed_cards']:
        impact_score += min(len(student_preview_diff['changed_cards']), 3)
        reasons.append(f"{len(student_preview_diff['changed_cards'])} cartao(oes) mudaram para o aluno")
    if student_preview_diff['added_blocks'] or student_preview_diff['removed_blocks']:
        impact_score += 2
        reasons.append('Estrutura visivel do treino mudou no app do aluno')
    if workout.revisions.filter(event=SessionWorkoutRevisionEvent.PUBLISHED).exists():
        impact_score += 1
        reasons.append('Republicacao de treino que ja teve versao oficial')
        priority_flags.append({'label': 'Republicacao', 'tone': 'warning'})
    else:
        priority_flags.append({'label': 'Primeira publicacao', 'tone': 'info'})

    now = timezone.localtime()
    starts_at = timezone.localtime(workout.session.scheduled_at)
    hours_until_session = (starts_at - now).total_seconds() / 3600
    if hours_until_session <= 6:
        impact_score += 2
        reasons.append('Aula comecando em breve')
        priority_flags.append({'label': 'Aula em breve', 'tone': 'accent'})

    if impact_score >= 6:
        impact_label = 'Alto impacto'
        impact_tone = 'danger'
    elif impact_score >= 3:
        impact_label = 'Medio impacto'
        impact_tone = 'warning'
    else:
        impact_label = 'Baixo impacto'
        impact_tone = 'success'

    summary_bits = []
    if diff_snapshot['added_blocks'] or diff_snapshot['removed_blocks']:
        summary_bits.append(
            f"{len(diff_snapshot['added_blocks']) + len(diff_snapshot['removed_blocks'])} bloco(s) mexidos"
        )
    if diff_snapshot['added_movements'] or diff_snapshot['removed_movements'] or diff_snapshot['changed_blocks']:
        movement_change_count = len(diff_snapshot['added_movements']) + len(diff_snapshot['removed_movements'])
        movement_change_count += sum(len(block['movement_changes']) for block in diff_snapshot['changed_blocks'])
        summary_bits.append(f'{movement_change_count} ajuste(s) de movimento')
    if student_preview_diff['changed_cards']:
        summary_bits.append(f"{len(student_preview_diff['changed_cards'])} cartao(oes) no app do aluno")
    if diff_snapshot['is_sensitive']:
        summary_bits.append('revisao sensivel')

    return {
        'impact_score': impact_score,
        'impact_label': impact_label,
        'impact_tone': impact_tone,
        'priority_flags': priority_flags[:4],
        'summary': ', '.join(summary_bits) if summary_bits else 'Mudanca pequena para leitura rapida.',
        'reasons': reasons[:5],
    }


def build_workout_diff_snapshot(*, published_snapshot, current_snapshot):
    if not published_snapshot:
        return {
            'has_previous_publication': False,
            'title_changed': False,
            'notes_changed': False,
            'added_blocks': [],
            'removed_blocks': [],
            'added_movements': [],
            'removed_movements': [],
            'changed_blocks': [],
            'risk_flags': [],
            'is_sensitive': False,
            'sensitive_reasons': [],
            'summary': 'Ainda nao existe versao publicada anterior para comparar.',
        }

    previous_blocks = build_snapshot_blocks(published_snapshot)
    current_blocks = build_snapshot_blocks(current_snapshot)
    previous_block_keys = {(block.get('title', ''), block.get('kind', '')) for block in previous_blocks}
    current_block_keys = {(block.get('title', ''), block.get('kind', '')) for block in current_blocks}

    def _flatten_movements(blocks):
        flattened = set()
        for block in blocks:
            for movement in block.get('movements', []):
                flattened.add(
                    (
                        movement.get('movement_label', ''),
                        movement.get('load_type', ''),
                        movement.get('sets'),
                        movement.get('reps'),
                    )
                )
        return flattened

    previous_movements = _flatten_movements(previous_blocks)
    current_movements = _flatten_movements(current_blocks)

    added_blocks = sorted(key[0] for key in current_block_keys - previous_block_keys if key[0])
    removed_blocks = sorted(key[0] for key in previous_block_keys - current_block_keys if key[0])
    added_movements = sorted(key[0] for key in current_movements - previous_movements if key[0])
    removed_movements = sorted(key[0] for key in previous_movements - current_movements if key[0])
    title_changed = published_snapshot.get('title', '') != current_snapshot.get('title', '')
    notes_changed = published_snapshot.get('coach_notes', '') != current_snapshot.get('coach_notes', '')
    changed_blocks = []
    risk_flags = []
    sensitive_reasons = []

    previous_block_map = {
        (block.get('title', ''), block.get('kind', '')): block
        for block in previous_blocks
    }
    current_block_map = {
        (block.get('title', ''), block.get('kind', '')): block
        for block in current_blocks
    }
    for block_key in sorted(previous_block_map.keys() & current_block_map.keys()):
        previous_block = previous_block_map[block_key]
        current_block = current_block_map[block_key]
        movement_changes = []
        previous_movement_map = {
            movement.get('movement_slug') or movement.get('movement_label'): movement
            for movement in previous_block.get('movements', [])
        }
        current_movement_map = {
            movement.get('movement_slug') or movement.get('movement_label'): movement
            for movement in current_block.get('movements', [])
        }
        for movement_key in sorted(previous_movement_map.keys() & current_movement_map.keys()):
            previous_movement = previous_movement_map[movement_key]
            current_movement = current_movement_map[movement_key]
            changed_fields = []
            for field_key, field_label in (
                ('sets', 'sets'),
                ('reps', 'reps'),
                ('load_type', 'tipo de carga'),
                ('load_value', 'carga'),
                ('notes', 'notas'),
            ):
                if previous_movement.get(field_key) != current_movement.get(field_key):
                    changed_fields.append(field_label)
            if changed_fields:
                movement_label = current_movement.get('movement_label') or previous_movement.get('movement_label') or movement_key
                movement_changes.append(
                    {
                        'movement_label': movement_label,
                        'changed_fields': changed_fields,
                    }
                )
                if 'tipo de carga' in changed_fields or 'carga' in changed_fields:
                    risk_flags.append(f'Carga alterada em {movement_label}')
                    sensitive_reasons.append(f'Prescricao de carga mudou em {movement_label}')
        if previous_block.get('notes', '') != current_block.get('notes', ''):
            movement_changes.append(
                {
                    'movement_label': 'Notas do bloco',
                    'changed_fields': ['notas'],
                }
            )
        if movement_changes:
            changed_blocks.append(
                {
                    'title': current_block.get('title') or previous_block.get('title'),
                    'kind_label': current_block.get('kind_label') or previous_block.get('kind_label'),
                    'movement_changes': movement_changes,
                }
            )

    summary_bits = []
    if title_changed:
        summary_bits.append('titulo alterado')
    if notes_changed:
        summary_bits.append('notas do coach alteradas')
    if added_blocks:
        summary_bits.append(f'{len(added_blocks)} bloco(s) novo(s)')
    if removed_blocks:
        summary_bits.append(f'{len(removed_blocks)} bloco(s) removido(s)')
    if added_movements:
        summary_bits.append(f'{len(added_movements)} movimento(s) novo(s)')
    if removed_movements:
        summary_bits.append(f'{len(removed_movements)} movimento(s) removido(s)')
    if changed_blocks:
        summary_bits.append(f'{len(changed_blocks)} bloco(s) com ajuste interno')
    if notes_changed:
        risk_flags.append('Notas do coach alteradas')
    if removed_blocks:
        risk_flags.append(f'{len(removed_blocks)} bloco(s) removido(s)')
        sensitive_reasons.append(f'{len(removed_blocks)} bloco(s) foram removido(s)')
    if removed_movements:
        risk_flags.append(f'{len(removed_movements)} movimento(s) removido(s)')
        sensitive_reasons.append(f'{len(removed_movements)} movimento(s) foram removido(s)')
    movement_delta = len(current_movements) - len(previous_movements)
    if abs(movement_delta) >= 3:
        sensitive_reasons.append(f'Volume estrutural mudou em {abs(movement_delta)} movimento(s)')
    if title_changed and not sensitive_reasons:
        risk_flags.append('Titulo do treino foi alterado')

    return {
        'has_previous_publication': True,
        'title_changed': title_changed,
        'notes_changed': notes_changed,
        'added_blocks': added_blocks[:4],
        'removed_blocks': removed_blocks[:4],
        'added_movements': added_movements[:6],
        'removed_movements': removed_movements[:6],
        'changed_blocks': changed_blocks[:4],
        'risk_flags': risk_flags[:5],
        'is_sensitive': bool(sensitive_reasons),
        'sensitive_reasons': sensitive_reasons[:5],
        'summary': ', '.join(summary_bits) if summary_bits else 'Estrutura equivalente a ultima versao publicada.',
    }
