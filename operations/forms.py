"""
ARQUIVO: formularios das mutacoes operacionais.

POR QUE ELE EXISTE:
- valida entradas curtas das rotas operacionais antes que cheguem na camada de acao.

O QUE ESTE ARQUIVO FAZ:
1. restringe categorias validas de ocorrencia tecnica.
2. limita tamanho e formato da descricao enviada pelo coach.

PONTOS CRITICOS:
- estes formularios ficam na borda HTTP e devem impedir ruido antes da regra de negocio.
"""

from django import forms

from operations.models import BehaviorCategory
from shared_support.form_inputs import apply_text_input_attrs
from student_app.models import StudentExerciseMax, WorkoutBlockKind, WorkoutLoadType, WorkoutOperationalMemoryKind
from student_app.models import (
    WorkoutRmGapActionStatus,
    WorkoutWeeklyCheckpointClosure,
    WorkoutWeeklyCheckpointOwner,
    WorkoutWeeklyCheckpointStatus,
    WorkoutWeeklyGovernanceCommitmentStatus,
)


WORKOUT_REJECTION_REASON_CHOICES = (
    ('load_incoherent', 'Carga incoerente'),
    ('missing_block', 'Faltou bloco'),
    ('poor_order', 'Ordem ruim'),
    ('adjust_notes', 'Ajustar notas'),
    ('excessive_volume', 'Volume excessivo'),
    ('other', 'Outro ajuste'),
)

WORKOUT_APPROVAL_REASON_CHOICES = (
    ('', 'Sem registrar motivo extra'),
    ('without_concerns', 'Aprovado sem ressalvas'),
    ('verbal_alignment', 'Aprovado com alinhamento verbal'),
    ('operational_urgency', 'Aprovado por urgencia operacional'),
)

WORKOUT_HISTORY_REASON_FILTER_CHOICES = (
    ('', 'Todos os contextos'),
    ('without_concerns', 'Sem ressalvas'),
    ('verbal_alignment', 'Alinhamento verbal'),
    ('operational_urgency', 'Urgencia operacional'),
    ('no_reason', 'Sem motivo extra'),
)

WORKOUT_FOLLOW_UP_STATUS_CHOICES = (
    ('completed', 'Resolvido'),
    ('dismissed', 'Descartado'),
)

WORKOUT_OPERATIONAL_MEMORY_KIND_CHOICES = (
    (WorkoutOperationalMemoryKind.RECEPTION_OWNED, 'Recepcao assumiu'),
    (WorkoutOperationalMemoryKind.COACH_ALIGNED, 'Coach alinhado'),
    (WorkoutOperationalMemoryKind.WHATSAPP_SENT, 'WhatsApp disparado'),
    (WorkoutOperationalMemoryKind.MONITORING_NOTE, 'Nota de monitoramento'),
    (WorkoutOperationalMemoryKind.CUSTOM, 'Marco livre'),
)

WORKOUT_RM_GAP_STATUS_CHOICES = (
    (WorkoutRmGapActionStatus.REQUESTED, 'RM solicitado'),
    (WorkoutRmGapActionStatus.COLLECTED, 'RM coletado'),
    (WorkoutRmGapActionStatus.FREE_LOAD, 'Deixar carga livre'),
)


class TechnicalBehaviorNoteForm(forms.Form):
    category = forms.ChoiceField(choices=BehaviorCategory.choices)
    description = forms.CharField(max_length=280)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_text_input_attrs(self.fields['description'], placeholder='Explique a ocorrencia tecnica em uma frase curta.', maxlength=280)


class CoachSessionWorkoutForm(forms.Form):
    title = forms.CharField(max_length=140, required=False)
    coach_notes = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_text_input_attrs(self.fields['title'], placeholder='Ex.: Forca + Metcon')
        self.fields['coach_notes'].widget.attrs.update(
            {
                'placeholder': 'Mensagem curta do coach para contextualizar o treino do dia.',
            }
        )


class WorkoutRejectionForm(forms.Form):
    rejection_category = forms.ChoiceField(choices=WORKOUT_REJECTION_REASON_CHOICES)
    rejection_reason = forms.CharField(max_length=255, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_text_input_attrs(
            self.fields['rejection_reason'],
            placeholder='Detalhe rapido para o coach entender o ajuste pedido.',
            maxlength=255,
        )

    def clean(self):
        cleaned_data = super().clean()
        category = cleaned_data.get('rejection_category')
        reason = (cleaned_data.get('rejection_reason') or '').strip()
        if category == 'other' and not reason:
            self.add_error('rejection_reason', 'Explique o ajuste quando escolher "Outro ajuste".')
        return cleaned_data

    def build_reason_text(self):
        category = self.cleaned_data['rejection_category']
        category_label = dict(WORKOUT_REJECTION_REASON_CHOICES).get(category, category)
        detail = (self.cleaned_data.get('rejection_reason') or '').strip()
        return f'{category_label}: {detail}' if detail else category_label


class WorkoutApprovalFilterForm(forms.Form):
    sort = forms.ChoiceField(
        required=False,
        choices=(
            ('submitted_oldest', 'Mais antigos primeiro'),
            ('submitted_newest', 'Mais recentes primeiro'),
            ('session_soonest', 'Aulas mais proximas'),
        ),
    )
    coach = forms.CharField(required=False, max_length=120)
    session_id = forms.IntegerField(required=False, min_value=1)
    sensitive_only = forms.BooleanField(required=False)
    today_only = forms.BooleanField(required=False)
    published_reason = forms.ChoiceField(required=False, choices=WORKOUT_HISTORY_REASON_FILTER_CHOICES)


class WorkoutApprovalDecisionForm(forms.Form):
    approval_reason_category = forms.ChoiceField(required=False, choices=WORKOUT_APPROVAL_REASON_CHOICES)
    approval_reason_note = forms.CharField(max_length=255, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_text_input_attrs(
            self.fields['approval_reason_note'],
            placeholder='Detalhe opcional da aprovacao para trilha de decisao.',
            maxlength=255,
        )

    def build_reason_payload(self):
        category = (self.cleaned_data.get('approval_reason_category') or '').strip()
        note = (self.cleaned_data.get('approval_reason_note') or '').strip()
        category_label = dict(WORKOUT_APPROVAL_REASON_CHOICES).get(category, '')
        return {
            'category': category,
            'label': category_label,
            'note': note,
            'summary': f'{category_label}: {note}' if category_label and note else (category_label or note),
        }


class WorkoutFollowUpResolutionForm(forms.Form):
    action_key = forms.CharField(max_length=64)
    action_label = forms.CharField(max_length=120)
    result_status = forms.ChoiceField(choices=WORKOUT_FOLLOW_UP_STATUS_CHOICES)
    outcome_note = forms.CharField(max_length=255, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_text_input_attrs(
            self.fields['outcome_note'],
            placeholder='Ex.: turma avisada no grupo e coach alinhado no piso.',
            maxlength=255,
        )

    def build_result_payload(self):
        status = self.cleaned_data['result_status']
        return {
            'status': status,
            'status_label': dict(WORKOUT_FOLLOW_UP_STATUS_CHOICES).get(status, status),
            'action_key': self.cleaned_data['action_key'],
            'action_label': self.cleaned_data['action_label'],
            'outcome_note': (self.cleaned_data.get('outcome_note') or '').strip(),
        }


class WorkoutOperationalMemoryForm(forms.Form):
    kind = forms.ChoiceField(choices=WORKOUT_OPERATIONAL_MEMORY_KIND_CHOICES)
    note = forms.CharField(max_length=255, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_text_input_attrs(
            self.fields['note'],
            placeholder='Ex.: recepcao chamou o coach e confirmou turma entrando.',
            maxlength=255,
        )

    def build_memory_payload(self):
        kind = self.cleaned_data['kind']
        note = (self.cleaned_data.get('note') or '').strip()
        return {
            'kind': kind,
            'kind_label': dict(WORKOUT_OPERATIONAL_MEMORY_KIND_CHOICES).get(kind, kind),
            'note': note,
        }


class WorkoutWeeklyCheckpointForm(forms.Form):
    execution_status = forms.ChoiceField(choices=WorkoutWeeklyCheckpointStatus.choices)
    responsible_role = forms.ChoiceField(choices=WorkoutWeeklyCheckpointOwner.choices)
    closure_status = forms.ChoiceField(choices=(('', 'Fechamento ainda nao registrado'), *WorkoutWeeklyCheckpointClosure.choices), required=False)
    governance_commitment_status = forms.ChoiceField(choices=WorkoutWeeklyGovernanceCommitmentStatus.choices)
    governance_commitment_note = forms.CharField(max_length=255, required=False)
    summary_note = forms.CharField(max_length=255, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_text_input_attrs(
            self.fields['governance_commitment_note'],
            placeholder='Ex.: owner assumiu a decisao e vai validar execucao na proxima semana.',
            maxlength=255,
        )
        apply_text_input_attrs(
            self.fields['summary_note'],
            placeholder='Ex.: manager puxando ritual da semana e coach alinhado no fechamento.',
            maxlength=255,
        )

    def build_payload(self):
        return {
            'execution_status': self.cleaned_data['execution_status'],
            'responsible_role': self.cleaned_data['responsible_role'],
            'closure_status': (self.cleaned_data.get('closure_status') or '').strip(),
            'governance_commitment_status': self.cleaned_data['governance_commitment_status'],
            'governance_commitment_note': (self.cleaned_data.get('governance_commitment_note') or '').strip(),
            'summary_note': (self.cleaned_data.get('summary_note') or '').strip(),
        }


class WorkoutRmGapActionForm(forms.Form):
    student_id = forms.IntegerField(min_value=1)
    exercise_slug = forms.SlugField(max_length=64)
    exercise_label = forms.CharField(max_length=120)
    status = forms.ChoiceField(choices=WORKOUT_RM_GAP_STATUS_CHOICES)
    note = forms.CharField(max_length=255, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_text_input_attrs(
            self.fields['note'],
            placeholder='Ex.: recepcao pediu RM hoje antes da aula das 18h.',
            maxlength=255,
        )

    def build_payload(self):
        status = self.cleaned_data['status']
        return {
            'student_id': self.cleaned_data['student_id'],
            'exercise_slug': self.cleaned_data['exercise_slug'],
            'exercise_label': self.cleaned_data['exercise_label'],
            'status': status,
            'status_label': dict(WORKOUT_RM_GAP_STATUS_CHOICES).get(status, status),
            'note': (self.cleaned_data.get('note') or '').strip(),
        }


class WorkoutStudentRmQuickForm(forms.ModelForm):
    class Meta:
        model = StudentExerciseMax
        fields = ['exercise_label', 'one_rep_max_kg', 'notes']

    def __init__(self, *args, exercise_label='', **kwargs):
        super().__init__(*args, **kwargs)
        apply_text_input_attrs(self.fields['exercise_label'], placeholder='Ex.: Deadlift', maxlength=120)
        self.fields['one_rep_max_kg'].widget.attrs.update({'placeholder': 'Ex.: 100.00', 'step': '0.01', 'min': '0'})
        apply_text_input_attrs(
            self.fields['notes'],
            placeholder='Ex.: medido no teste de forca da turma.',
            maxlength=255,
        )
        if exercise_label and not self.initial.get('exercise_label'):
            self.initial['exercise_label'] = exercise_label
            self.fields['exercise_label'].initial = exercise_label


class CoachWorkoutBlockForm(forms.Form):
    block_id = forms.IntegerField(min_value=1, required=False)
    title = forms.CharField(max_length=120)
    kind = forms.ChoiceField(choices=WorkoutBlockKind.choices, initial=WorkoutBlockKind.CUSTOM)
    notes = forms.CharField(widget=forms.Textarea(attrs={'rows': 2}), required=False)
    sort_order = forms.IntegerField(min_value=1, initial=1)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_text_input_attrs(self.fields['title'], placeholder='Ex.: Forca principal')
        self.fields['notes'].widget.attrs.update(
            {
                'placeholder': 'Orientacao curta para este bloco.',
            }
        )


class CoachWorkoutMovementForm(forms.Form):
    movement_id = forms.IntegerField(min_value=1, required=False)
    block_id = forms.IntegerField(min_value=1)
    movement_slug = forms.SlugField(max_length=64)
    movement_label = forms.CharField(max_length=120)
    sets = forms.IntegerField(min_value=1, required=False)
    reps = forms.IntegerField(min_value=1, required=False)
    load_type = forms.ChoiceField(choices=WorkoutLoadType.choices, initial=WorkoutLoadType.FREE)
    load_value = forms.DecimalField(min_value=0, decimal_places=2, max_digits=6, required=False)
    notes = forms.CharField(max_length=255, required=False)
    sort_order = forms.IntegerField(min_value=1, initial=1)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_text_input_attrs(self.fields['movement_slug'], placeholder='deadlift')
        apply_text_input_attrs(self.fields['movement_label'], placeholder='Deadlift')
        self.fields['movement_slug'].widget.attrs.update(
            {
                'list': 'wod-movement-catalog-slugs',
                'data-wod-movement-slug': 'true',
                'autocomplete': 'off',
            }
        )
        self.fields['movement_label'].widget.attrs.update(
            {
                'list': 'wod-movement-catalog-labels',
                'data-wod-movement-label': 'true',
                'autocomplete': 'off',
            }
        )
        apply_text_input_attrs(self.fields['notes'], placeholder='Respire no topo e mantenha a lombar forte.', maxlength=255)


class WorkoutDuplicateForm(forms.Form):
    target_session_id = forms.IntegerField(min_value=1)


class WorkoutQuickTemplateForm(forms.Form):
    source_workout_id = forms.IntegerField(min_value=1)


class WorkoutStoredTemplateForm(forms.Form):
    template_id = forms.IntegerField(min_value=1)


class WorkoutCreateStoredTemplateForm(forms.Form):
    template_name = forms.CharField(max_length=120)


class WorkoutTemplateMetadataForm(forms.Form):
    name = forms.CharField(max_length=120)
    description = forms.CharField(max_length=255, required=False)
    is_featured = forms.BooleanField(required=False)
    is_trusted = forms.BooleanField(required=False)


class WorkoutTemplateDuplicateForm(forms.Form):
    name = forms.CharField(max_length=120, required=False)


class WorkoutTemplateManagementFilterForm(forms.Form):
    q = forms.CharField(max_length=120, required=False)
    active = forms.BooleanField(required=False)
    featured = forms.BooleanField(required=False)


class WorkoutApprovalPolicyForm(forms.Form):
    approval_policy = forms.ChoiceField(choices=(('strict', 'Aprovacao obrigatoria'), ('trusted_template', 'Template confiavel publica direto'), ('coach_autonomy', 'Coach confiavel publica direto')))


class WorkoutTemplateBlockForm(forms.Form):
    block_id = forms.IntegerField(min_value=1, required=False)
    title = forms.CharField(max_length=120)
    kind = forms.ChoiceField(choices=WorkoutBlockKind.choices, initial=WorkoutBlockKind.CUSTOM)
    notes = forms.CharField(widget=forms.Textarea(attrs={'rows': 2}), required=False)
    sort_order = forms.IntegerField(min_value=1, initial=1)


class WorkoutTemplateMovementForm(forms.Form):
    movement_id = forms.IntegerField(min_value=1, required=False)
    block_id = forms.IntegerField(min_value=1, required=False)
    movement_slug = forms.SlugField(max_length=64)
    movement_label = forms.CharField(max_length=120)
    sets = forms.IntegerField(min_value=1, required=False)
    reps = forms.IntegerField(min_value=1, required=False)
    load_type = forms.ChoiceField(choices=WorkoutLoadType.choices, initial=WorkoutLoadType.FREE)
    load_value = forms.DecimalField(min_value=0, decimal_places=2, max_digits=6, required=False)
    notes = forms.CharField(max_length=255, required=False)
    sort_order = forms.IntegerField(min_value=1, initial=1)


__all__ = [
    'CoachSessionWorkoutForm',
    'CoachWorkoutBlockForm',
    'WorkoutDuplicateForm',
    'WorkoutQuickTemplateForm',
    'WorkoutStoredTemplateForm',
    'WorkoutTemplateMetadataForm',
    'WorkoutTemplateDuplicateForm',
    'WorkoutTemplateManagementFilterForm',
    'WorkoutApprovalPolicyForm',
    'WorkoutTemplateBlockForm',
    'WorkoutTemplateMovementForm',
    'WorkoutCreateStoredTemplateForm',
    'CoachWorkoutMovementForm',
    'TechnicalBehaviorNoteForm',
    'WorkoutRejectionForm',
    'WorkoutApprovalFilterForm',
    'WorkoutApprovalDecisionForm',
    'WorkoutFollowUpResolutionForm',
    'WorkoutOperationalMemoryForm',
    'WorkoutWeeklyCheckpointForm',
    'WorkoutRmGapActionForm',
    'WorkoutStudentRmQuickForm',
]
