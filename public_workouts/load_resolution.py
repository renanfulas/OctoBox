"""Uma decisão de carga para a ficha e o guia, com origem explícita."""

from dataclasses import dataclass

from .load_suggestion import suggest_movement_load
from .periodization import suggest_progressive_load_kg


@dataclass(frozen=True)
class LoadResolution:
    kind: str
    value_kg: object | None
    percentage: float | None = None
    show_registration_hint: bool = False
    fallback_note: str | None = None
    anchor_kg: object | None = None
    reason_code: str = ''
    rounding_step_kg: float = 2.5
    editable: bool = True

    def as_template_dict(self) -> dict:
        """Mantém o contrato de template antigo durante a extração da regra."""
        result = {
            'kind': self.kind, 'value_kg': self.value_kg,
            'percentage': self.percentage,
            'show_registration_hint': self.show_registration_hint,
        }
        if self.fallback_note is not None:
            result['fallback_note'] = self.fallback_note
        return result


def _round_to_nearest_load(value, step=2.5):
    return round(value / step) * step


def resolve_movement_load(*, movement: dict, payload: dict, phase,
                          one_rep_max_by_movement: dict, progress_snapshots=None) -> LoadResolution:
    """Prescrição > progressão > estimativa > última Top > escolha manual."""
    slug = movement.get('movement_slug')
    estimate = (one_rep_max_by_movement or {}).get(slug)
    one_rep_max_kg = estimate.get('value_kg') if estimate else None
    has_rm = one_rep_max_kg is not None
    snapshot = (progress_snapshots or {}).get(slug)
    latest_top = snapshot.latest_top_set if snapshot else None
    load_type = movement.get('load_type')
    load_value = movement.get('load_value')

    if load_type == 'fixed_kg':
        return LoadResolution('fixed_kg', load_value, anchor_kg=load_value, reason_code='coach_fixed')

    if load_type == 'percentage_of_rm' and load_value is not None:
        if has_rm:
            return LoadResolution(
                'percentage', _round_to_nearest_load(load_value / 100 * one_rep_max_kg),
                percentage=load_value, anchor_kg=one_rep_max_kg, reason_code='rm_available',
            )
        if latest_top is not None and latest_top.weight_kg is not None:
            return LoadResolution(
                'last_observed', latest_top.weight_kg, percentage=load_value,
                show_registration_hint=True, anchor_kg=latest_top.weight_kg,
                reason_code='rm_missing_last_top_reference',
                fallback_note='Sem RM confiável ainda. Use sua última carga registrada como referência e ajuste se necessário.',
            )
        return LoadResolution(
            'percentage', None, percentage=load_value, show_registration_hint=True,
            reason_code='rm_missing',
            fallback_note='Ainda não há RM confiável. Defina a carga alvo da Top no guia ou registre a carga realizada.',
        )

    if phase is not None:
        last_log = (
            {'weight_kg': latest_top.weight_kg, 'reps': latest_top.reps,
             'rir': latest_top.rir, 'performed_on': latest_top.performed_on.isoformat(),
             'program_id': latest_top.program_id}
            if latest_top is not None else None
        )
        value = suggest_progressive_load_kg(
            payload=payload, current_phase=phase, last_log=last_log,
            one_rep_max_kg=one_rep_max_kg,
        )
        if value is not None:
            return LoadResolution(
                'phase_progressive', value,
                percentage=round(sum(phase.intensity_pct_range) / 2),
                anchor_kg=latest_top.weight_kg if latest_top else None,
                reason_code='active_phase',
            )

    suggestion = suggest_movement_load(movement=movement, one_rep_max_kg=one_rep_max_kg)
    if suggestion is not None:
        return LoadResolution(
            'rir_estimate', suggestion['value_kg'], anchor_kg=one_rep_max_kg,
            reason_code='reps_rir_estimate',
        )

    if latest_top is not None and latest_top.weight_kg is not None:
        return LoadResolution(
            'last_observed', latest_top.weight_kg, show_registration_hint=True,
            anchor_kg=latest_top.weight_kg, reason_code='no_computable_prescription',
            fallback_note='A prescrição não gerou kg automático. Sua última carga registrada é uma referência editável.',
        )
    return LoadResolution(
        'free', None, show_registration_hint=not has_rm, reason_code='no_usable_anchor',
        fallback_note=(
            'Há RM registrado, mas faltam reps ou RIR claros para sugerir kg. Escolha a carga realizada.'
            if has_rm else
            'Sem dados suficientes para sugerir kg. Registre uma carga confortável para criar sua primeira referência.'
        ),
    )
