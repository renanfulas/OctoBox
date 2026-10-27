"""Forms for weekly WOD intake, review, and projection."""

from __future__ import annotations

from datetime import date

from django import forms
from django.utils import timezone

from operations.model_definitions import ClassType
from shared_support.form_inputs import apply_text_input_attrs


def _coerce_smart_paste_date(
    raw_value: str,
    *,
    field_label: str,
    allow_past: bool = False,
    allow_historical_years: bool = False,
    max_date: date | None = None,
) -> date:
    normalized = (raw_value or '').strip()
    if not normalized:
        raise forms.ValidationError(f'Informe {field_label} no formato dd/mm.')

    today = timezone.localdate()
    allowed_years = {today.year - 1, today.year, today.year + 1}
    if max_date is not None:
        allowed_years.add(max_date.year)

    if normalized.count('/') == 1:
        try:
            day_value, month_value = [int(chunk) for chunk in normalized.split('/')]
            current_year_candidate = date(today.year, month_value, day_value)
            next_year_candidate = date(today.year + 1, month_value, day_value)
        except ValueError as exc:
            raise forms.ValidationError(f'Informe uma data válida para {field_label} no formato dd/mm/aaaa.') from exc
        current_distance = abs((current_year_candidate - today).days)
        next_distance = abs((next_year_candidate - today).days)
        if allow_past:
            candidate = current_year_candidate
        else:
            candidate = current_year_candidate if current_distance <= next_distance else next_year_candidate
    elif normalized.count('/') == 2:
        try:
            day_value, month_value, year_value = [int(chunk) for chunk in normalized.split('/')]
        except ValueError as exc:
            raise forms.ValidationError(f'Use {field_label} no formato dd/mm.') from exc
        if year_value < 100:
            year_value += 2000
        if not allow_historical_years and year_value not in allowed_years:
            raise forms.ValidationError('A data precisa ficar no ano anterior, atual ou no proximo ano.')
        try:
            candidate = date(year_value, month_value, day_value)
        except ValueError as exc:
            raise forms.ValidationError(f'Informe uma data válida para {field_label} no formato dd/mm/aaaa.') from exc
    else:
        raise forms.ValidationError(f'Use {field_label} no formato dd/mm.')

    if not allow_past and candidate < today:
        raise forms.ValidationError('Nao e permitido usar datas no passado.')
    if not allow_historical_years and candidate.year not in allowed_years:
        raise forms.ValidationError('A data precisa ficar no ano anterior, atual ou no proximo ano.')
    if candidate.weekday() != 0:
        from datetime import timedelta
        candidate = candidate - timedelta(days=candidate.weekday())
    if max_date is not None and candidate > max_date:
        raise forms.ValidationError(
            f'A semana escolhida ({candidate:%d/%m/%Y}) ultrapassa a ultima aula da grade ({max_date:%d/%m/%Y}).'
        )
    return candidate



SMART_PASTE_MAX_LINES = 500


class WeeklyWodSmartPasteForm(forms.Form):
    plan_id = forms.IntegerField(required=False, min_value=1)
    plan_revision = forms.DateTimeField(required=False)
    plan_version = forms.IntegerField(required=False, min_value=1)
    workout_program = forms.ModelChoiceField(
        queryset=None,
        empty_label='Selecione a modalidade',
        label='Modalidade desta programação',
        help_text='A distribuição será limitada às aulas desta modalidade na semana escolhida.',
        required=False,
    )
    week_start = forms.CharField(max_length=10)
    label = forms.CharField(max_length=140, required=False)
    source_text = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 12}),
        error_messages={'required': 'Cole o treino da semana antes de organizar.'},
    )

    def __init__(self, *args, max_week_start: date | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        from operations.models import WorkoutProgram
        from operations.workout_program_catalog import ensure_default_workout_programs
        programs = ensure_default_workout_programs()
        self.fields['workout_program'].queryset = programs
        # Preserve compatibility for existing clients/forms that submit the
        # weekly paste without the new modality field. The visible UI still
        # sends an explicit choice; omission safely defaults to CrossFit.
        # A UI envia escolha explícita; payloads antigos que omitem o campo
        # seguem temporariamente com CrossFit para compatibilidade.
        self.fields['workout_program'].widget.attrs['required'] = 'required'
        self.fields['workout_program'].widget.attrs.update({'class': 'smart-paste-program-select'})
        self._max_week_start = max_week_start
        apply_text_input_attrs(
            self.fields['label'],
            placeholder='Ex.: Semana 2 - Base de forca + metcon',
            maxlength=140,
        )
        apply_text_input_attrs(
            self.fields['week_start'],
            placeholder='dd/mm',
            maxlength=10,
        )
        self.fields['week_start'].widget.attrs.update(
            {
                'data-smart-date-input': 'true',
                'data-smart-date-include-year': 'true',
                'data-picker-target': 'smart-paste-week-start-picker',
                'inputmode': 'numeric',
            }
        )
        self.fields['source_text'].widget.attrs.update(
            {
                'placeholder': (
                    'Cole ou escreva o treino da semana. Exemplo:\n\n'
                    'Segunda\n'
                    'Força: 5x5 Back Squat 75%\n'
                    'AMRAP 12: 10 pull-up / 15 air squat / 20 sit-up\n\n'
                    'Terça\n'
                    'EMOM 10: min 1 = 3 power clean 70% / min 2 = 8 TTB\n'
                    'For Time 5 rounds: 10 deadlift 80kg / 15 wall ball\n\n'
                    'Quarta\n'
                    'Skill: HSPU estrito\n'
                    'AMRAP 20: 400m run / 21 KB swing 24kg / 12 pull-up'
                ),
                'class': 'smart-paste-textarea',
                'spellcheck': 'false',
                'aria-describedby': 'smart-paste-source-hint',
                'data-wod-draft-source': 'true',
            }
        )

    def clean_workout_program(self):
        program = self.cleaned_data.get('workout_program')
        if program is not None:
            return program
        if self.is_bound and 'workout_program' in self.data:
            raise forms.ValidationError('Escolha a modalidade antes de organizar a semana.')
        return self.fields['workout_program'].queryset.filter(slug='crossfit').first()

    def clean_source_text(self):
        text = (self.cleaned_data.get('source_text') or '').strip()
        if text:
            line_count = text.count('\n') + 1
            if line_count > SMART_PASTE_MAX_LINES:
                raise forms.ValidationError(
                    f'O texto colado tem {line_count} linhas — o limite e {SMART_PASTE_MAX_LINES}. '
                    'Cole so o treino da semana, sem texto extra.'
                )
        return text

    def clean_week_start(self):
        return _coerce_smart_paste_date(
            self.cleaned_data.get('week_start'),
            field_label='a semana',
            allow_past=True,
            max_date=self._max_week_start,
        )


class WeeklyWodProjectionForm(forms.Form):
    plan_id = forms.IntegerField(min_value=1)
    idempotency_key = forms.UUIDField(required=False, widget=forms.HiddenInput())
    target_week_start = forms.CharField(max_length=10)
    class_types = forms.MultipleChoiceField(
        choices=(
            (ClassType.CROSS, 'CrossFit'),
            (ClassType.HYROX, 'HYROX'),
            (ClassType.MOBILITY, 'Mobilidade'),
            (ClassType.OLY, 'Halterofilia'),
            (ClassType.STRENGTH, 'Forca'),
            (ClassType.OPEN_GYM, 'Open Gym'),
            (ClassType.OTHER, 'Outros'),
        ),
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_text_input_attrs(
            self.fields['target_week_start'],
            placeholder='dd/mm',
            maxlength=10,
        )
        self.fields['target_week_start'].widget.attrs.update(
            {
                'data-smart-date-input': 'true',
                'data-picker-target': 'smart-paste-target-week-picker',
                'data-smart-date-include-year': 'true',
                'inputmode': 'numeric',
            }
        )

    def clean_class_types(self):
        class_types = self.cleaned_data.get('class_types') or []
        return list(class_types or [ClassType.CROSS])

    def clean_target_week_start(self):
        return _coerce_smart_paste_date(
            self.cleaned_data.get('target_week_start'),
            field_label='a semana alvo',
            allow_past=True,
            allow_historical_years=True,
        )


class WeeklyWodReviewMovementForm(forms.Form):
    plan_id = forms.IntegerField(min_value=1)
    plan_revision = forms.DateTimeField(required=False)
    plan_version = forms.IntegerField(required=False, min_value=1)
    day_index = forms.IntegerField(min_value=0)
    block_index = forms.IntegerField(min_value=0)
    movement_index = forms.IntegerField(min_value=0)
    movement_label_raw = forms.CharField(max_length=120)
    movement_slug = forms.CharField(max_length=64, required=False)
    reps_spec = forms.CharField(max_length=64, required=False)
    load_spec = forms.CharField(max_length=64, required=False)
    notes = forms.CharField(max_length=255, required=False)

    def __init__(self, *args, slug_choices=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.slug_choices = list(slug_choices or [])
        apply_text_input_attrs(
            self.fields['movement_label_raw'],
            placeholder='Ex.: 15 bar muscle up',
            maxlength=120,
        )
        apply_text_input_attrs(
            self.fields['movement_slug'],
            placeholder='Ex.: bar_muscle_up',
            maxlength=64,
        )
        apply_text_input_attrs(
            self.fields['reps_spec'],
            placeholder='Ex.: 15 ou 10 a 12',
            maxlength=64,
        )
        apply_text_input_attrs(
            self.fields['load_spec'],
            placeholder='Ex.: 40/25 ou 70%',
            maxlength=64,
        )
        apply_text_input_attrs(
            self.fields['notes'],
            placeholder='Observacao curta do movimento.',
            maxlength=255,
        )

    def clean_movement_slug(self):
        slug = (self.cleaned_data.get('movement_slug') or '').strip().lower()
        if not slug:
            return ''
        valid_slugs = {choice[0] for choice in self.slug_choices}
        if slug not in valid_slugs and slug != 'custom':
            from operations.services.wod_paste_parser import resolve_movement_slug
            matched_slug = resolve_movement_slug(slug, exact_only=True)
            if matched_slug in valid_slugs:
                return matched_slug
            raise forms.ValidationError(
                'Escolha um movimento sugerido ou use “Manter nome original como personalizado”.'
            )
        return slug

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get('movement_slug') and cleaned.get('movement_label_raw'):
            from operations.services.wod_paste_parser import resolve_movement_slug
            if not resolve_movement_slug(cleaned['movement_label_raw']):
                self.add_error(
                    'movement_slug',
                    'Selecione um movimento ou use “Manter nome original como personalizado”.',
                )
        return cleaned


__all__ = [
    'SMART_PASTE_MAX_LINES',
    'WeeklyWodProjectionForm',
    'WeeklyWodReviewMovementForm',
    'WeeklyWodSmartPasteForm',
]
