"""
ARQUIVO: formularios da grade visual de aulas.

POR QUE ELE EXISTE:
- Mantem juntos os formularios de filtro, planejamento recorrente e edicao rapida da agenda.

O QUE ESTE ARQUIVO FAZ:
1. Define os filtros de leitura da grade.
2. Define o formulario de criacao recorrente de aulas.
3. Define o formulario de edicao rapida de uma aula.

PONTOS CRITICOS:
- Validacoes erradas aqui distorcem agenda, ocupacao e mudancas operacionais da grade.
"""

from django import forms
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone

from boxcore.access.roles import ROLE_COACH, ROLE_MANAGER, ROLE_OWNER
from boxcore.catalog.services.class_grid_policy import build_class_grid_session_policy
from boxcore.models import ClassSession, SessionStatus


WEEKDAY_CHOICES = (
    ('0', 'Segunda'),
    ('1', 'Terca'),
    ('2', 'Quarta'),
    ('3', 'Quinta'),
    ('4', 'Sexta'),
    ('5', 'Sabado'),
    ('6', 'Domingo'),
)


def _get_class_coach_queryset():
    user_model = get_user_model()
    return user_model.objects.filter(
        Q(is_superuser=True) | Q(groups__name__in=(ROLE_COACH, ROLE_MANAGER, ROLE_OWNER)),
        is_active=True,
    ).distinct().order_by('first_name', 'username')


class ClassGridFilterForm(forms.Form):
    reference_month = forms.CharField(
        required=False,
        label='Mes de referencia',
        widget=forms.TextInput(attrs={'type': 'month'}),
    )
    coach = forms.ModelChoiceField(
        queryset=_get_class_coach_queryset(),
        required=False,
        label='Coach',
        empty_label='Todos os coaches',
    )
    status = forms.ChoiceField(
        required=False,
        label='Status da aula',
        choices=(('', 'Todos'), *SessionStatus.choices),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['reference_month'].initial = timezone.localdate().strftime('%Y-%m')

    def clean_reference_month(self):
        reference_month = self.cleaned_data.get('reference_month')
        if not reference_month:
            return timezone.localdate().replace(day=1)
        try:
            parsed_date = timezone.datetime.strptime(reference_month, '%Y-%m').date()
        except ValueError as exc:
            raise forms.ValidationError('Informe um mes valido no formato AAAA-MM.') from exc
        return parsed_date.replace(day=1)


class ClassScheduleRecurringForm(forms.ModelForm):
    start_date = forms.DateField(
        label='Primeiro dia (dd/mm/aa)',
        input_formats=['%d/%m/%y', '%d/%m/%Y', '%Y-%m-%d'],
        error_messages={
            'required': 'Informe o primeiro dia da recorrencia.',
            'invalid': 'Use a data no formato dd/mm/aa. Ex.: 11/03/26.',
        },
        widget=forms.DateInput(
            format='%d/%m/%y',
            attrs={
                'placeholder': '11/03/26',
                'inputmode': 'numeric',
                'autocomplete': 'off',
                'maxlength': '8',
                'pattern': '\\d{2}/\\d{2}/\\d{2}',
                'data-mask': 'date',
            },
        ),
    )
    end_date = forms.DateField(
        label='Data final (dd/mm/aa)',
        input_formats=['%d/%m/%y', '%d/%m/%Y', '%Y-%m-%d'],
        error_messages={
            'required': 'Informe a data final da recorrencia.',
            'invalid': 'Use a data no formato dd/mm/aa. Ex.: 08/04/26.',
        },
        widget=forms.DateInput(
            format='%d/%m/%y',
            attrs={
                'placeholder': '08/04/26',
                'inputmode': 'numeric',
                'autocomplete': 'off',
                'maxlength': '8',
                'pattern': '\\d{2}/\\d{2}/\\d{2}',
                'data-mask': 'date',
            },
        ),
    )
    start_time = forms.TimeField(
        label='Horario inicial da aula (24h)',
        input_formats=['%H:%M'],
        error_messages={
            'required': 'Informe o horario inicial da aula.',
            'invalid': 'Use o horario em 24h no formato HH:MM. Ex.: 07:00.',
        },
        widget=forms.TimeInput(
            format='%H:%M',
            attrs={
                'placeholder': '07:00',
                'inputmode': 'numeric',
                'autocomplete': 'off',
                'maxlength': '5',
                'pattern': '([01]\\d|2[0-3]):[0-5]\\d',
                'data-mask': 'time',
            },
        ),
    )
    weekdays = forms.MultipleChoiceField(
        label='Dias da semana',
        choices=WEEKDAY_CHOICES,
        widget=forms.CheckboxSelectMultiple,
    )
    coach = forms.ModelChoiceField(
        queryset=get_user_model().objects.none(),
        required=False,
        label='Coach responsavel pela aula',
        empty_label='Definir depois',
    )
    skip_existing = forms.BooleanField(
        required=False,
        initial=True,
        label='Pular aulas que ja existirem nesse mesmo horario',
    )
    sequence_count = forms.TypedChoiceField(
        label='Aulas em sequencia',
        choices=((0, '0'), (1, '+1'), (2, '+2'), (3, '+3'), (4, '+4'), (5, '+5')),
        coerce=int,
        initial=0,
        widget=forms.Select,
        help_text='0 cria so o horario base. Ex.: 07:00 com +3 gera 07:00, 08:00, 09:00 e 10:00 quando a duracao for 60 min.',
    )

    class Meta:
        model = ClassSession
        fields = [
            'title',
            'coach',
            'start_date',
            'end_date',
            'weekdays',
            'start_time',
            'sequence_count',
            'duration_minutes',
            'capacity',
            'status',
            'notes',
            'skip_existing',
        ]
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['title'].label = 'Nome da aula'
        self.fields['duration_minutes'].label = 'Duracao em minutos'
        self.fields['capacity'].label = 'Capacidade da turma'
        self.fields['status'].label = 'Status inicial'
        self.fields['notes'].label = 'Observacoes operacionais'
        self.fields['coach'].queryset = _get_class_coach_queryset()

        self.fields['title'].widget.attrs.update({'placeholder': 'Ex.: WOD 07h'})
        self.fields['duration_minutes'].widget.attrs.update({'placeholder': 'Ex.: 60', 'min': '1', 'step': '1', 'inputmode': 'numeric'})
        self.fields['capacity'].widget.attrs.update({'placeholder': 'Ex.: 20', 'min': '1', 'step': '1', 'inputmode': 'numeric'})
        self.fields['notes'].widget.attrs.update({'placeholder': 'Ex.: aula de alta demanda; abrir check-in 15 min antes.'})

        self.fields['start_date'].initial = timezone.localdate()
        self.fields['end_date'].initial = timezone.localdate() + timezone.timedelta(days=27)
        self.fields['duration_minutes'].initial = 60
        self.fields['capacity'].initial = 20
        self.fields['status'].initial = SessionStatus.SCHEDULED
        self.fields['weekdays'].initial = [str(timezone.localdate().weekday())]
        self.fields['sequence_count'].initial = 0
        self.fields['notes'].required = False

    def clean_weekdays(self):
        weekdays = self.cleaned_data.get('weekdays') or []
        return [int(value) for value in weekdays]

    def clean_duration_minutes(self):
        duration_minutes = self.cleaned_data.get('duration_minutes')
        if duration_minutes is not None and duration_minutes <= 0:
            raise forms.ValidationError('A duracao precisa ser maior que zero.')
        return duration_minutes

    def clean_capacity(self):
        capacity = self.cleaned_data.get('capacity')
        if capacity is not None and capacity <= 0:
            raise forms.ValidationError('A capacidade precisa ser maior que zero.')
        return capacity

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        weekdays = cleaned_data.get('weekdays') or []

        if start_date and end_date and end_date < start_date:
            self.add_error('end_date', 'A data final precisa ser igual ou posterior a data inicial.')

        if start_date and end_date and (end_date - start_date).days > 120:
            self.add_error('end_date', 'Para evitar excesso de agenda acidental, use um intervalo de ate 120 dias por vez.')

        if not weekdays:
            self.add_error('weekdays', 'Escolha pelo menos um dia da semana para gerar a agenda.')

        return cleaned_data


class ClassSessionQuickEditForm(forms.ModelForm):
    start_time = forms.TimeField(
        label='Horario de inicio',
        widget=forms.TimeInput(attrs={'type': 'time'}),
    )

    class Meta:
        model = ClassSession
        fields = [
            'title',
            'coach',
            'start_time',
            'duration_minutes',
            'capacity',
            'status',
            'notes',
        ]
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        session_policy = build_class_grid_session_policy(self.instance) if self.instance.pk else None
        self.fields['coach'].queryset = _get_class_coach_queryset()
        self.fields['title'].label = 'Nome da aula'
        self.fields['coach'].label = 'Coach responsavel pela aula'
        self.fields['duration_minutes'].label = 'Duracao em minutos'
        self.fields['capacity'].label = 'Capacidade da turma'
        self.fields['status'].label = 'Status da aula'
        self.fields['notes'].label = 'Observacoes operacionais'
        if session_policy is not None:
            self.fields['status'].choices = session_policy.quick_edit_status_choices
        if self.instance.pk:
            local_start = timezone.localtime(self.instance.scheduled_at)
            self.fields['start_time'].initial = local_start.time().replace(second=0, microsecond=0)
            if self.instance.status not in dict(self.fields['status'].choices):
                self.fields['status'].initial = SessionStatus.SCHEDULED

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        selected_status = cleaned_data.get('status')

        if self.instance.pk:
            session_policy = build_class_grid_session_policy(self.instance)
            try:
                session_policy.validate_quick_edit_status(selected_status)
            except ValueError as exc:
                self.add_error('status', str(exc))

        if self.instance.pk and start_time:
            scheduled_date = timezone.localtime(self.instance.scheduled_at).date()
            cleaned_data['scheduled_at'] = timezone.make_aware(
                timezone.datetime.combine(scheduled_date, start_time),
                timezone.get_current_timezone(),
            )
        return cleaned_data