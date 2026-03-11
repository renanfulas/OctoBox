"""
ARQUIVO: formularios das paginas visuais de catalogo.

POR QUE ELE EXISTE:
- centraliza os formularios leves que sustentam alunos, financeiro e grade de aulas fora do admin bruto.

O QUE ESTE ARQUIVO FAZ:
1. define filtros da pagina de alunos, do centro financeiro e da grade de aulas.
2. define o formulario leve de aluno com intake, plano, cobranca inicial e regra comercial.
3. define formularios de gestao pontual para pagamento, matricula e plano financeiro.
4. define os formularios de planejamento recorrente e edicao rapida da grade de aulas.

PONTOS CRITICOS:
- estes formularios espelham a camada operacional mais usada do produto.
- validacoes e querysets errados aqui distorcem cadastro, conversao de leads, cobranca e leitura da agenda.
"""

from django import forms
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone

from boxcore.access.roles import ROLE_COACH, ROLE_MANAGER, ROLE_OWNER
from boxcore.models import (
    ClassSession,
    EnrollmentStatus,
    IntakeStatus,
    MembershipPlan,
    PaymentMethod,
    PaymentStatus,
    SessionStatus,
    Student,
    StudentIntake,
    StudentStatus,
)
from boxcore.catalog.services.class_grid_policy import build_class_grid_session_policy


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


class StudentDirectoryFilterForm(forms.Form):
    query = forms.CharField(required=False, label='Busca')
    student_status = forms.ChoiceField(
        required=False,
        label='Status do aluno',
        choices=(('', 'Todos'), *StudentStatus.choices),
    )
    commercial_status = forms.ChoiceField(
        required=False,
        label='Status comercial',
        choices=(('', 'Todos'), *EnrollmentStatus.choices),
    )
    payment_status = forms.ChoiceField(
        required=False,
        label='Status financeiro',
        choices=(('', 'Todos'), *PaymentStatus.choices),
    )


class StudentQuickForm(forms.ModelForm):
    intake_record = forms.ModelChoiceField(
        queryset=StudentIntake.objects.none(),
        required=False,
        label='Lead / entrada provisoria',
        empty_label='Sem lead vinculado',
    )
    selected_plan = forms.ModelChoiceField(
        queryset=MembershipPlan.objects.none(),
        required=False,
        label='Plano conectado',
        empty_label='Sem plano por enquanto',
    )
    enrollment_status = forms.ChoiceField(
        choices=EnrollmentStatus.choices,
        required=False,
        label='Status comercial',
    )
    payment_method = forms.ChoiceField(
        choices=PaymentMethod.choices,
        required=False,
        label='Metodo de pagamento',
    )
    confirm_payment_now = forms.TypedChoiceField(
        choices=((True, 'Confirmar pagamento agora'), (False, 'Gerar cobranca pendente')),
        required=False,
        label='Confirmacao do pagamento inicial',
        coerce=lambda value: value in (True, 'True', 'true', '1', 'on'),
        widget=forms.Select,
    )
    payment_due_date = forms.DateField(
        required=False,
        label='Vencimento da primeira cobranca',
        widget=forms.DateInput(attrs={'type': 'date'}),
    )
    payment_reference = forms.CharField(
        required=False,
        label='Referencia comercial',
    )
    initial_payment_amount = forms.DecimalField(
        required=False,
        min_value=0,
        decimal_places=2,
        max_digits=10,
        label='Valor inicial da cobranca',
    )
    billing_strategy = forms.ChoiceField(
        required=False,
        label='Formato de cobranca',
        choices=(
            ('single', 'Cobranca unica'),
            ('installments', 'Parcelado'),
            ('recurring', 'Recorrencia programada'),
        ),
    )
    installment_total = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=12,
        label='Total de parcelas',
    )
    recurrence_cycles = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=12,
        label='Quantidade de ciclos',
    )

    class Meta:
        model = Student
        fields = [
            'full_name',
            'phone',
            'status',
            'email',
            'gender',
            'birth_date',
            'health_issue_status',
            'cpf',
            'notes',
        ]
        widgets = {
            'birth_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['full_name'].label = 'Nome completo'
        self.fields['phone'].label = 'WhatsApp'
        self.fields['phone'].help_text = 'Use o numero principal de contato do aluno.'
        self.fields['status'].label = 'Status inicial'
        self.fields['email'].label = 'E-mail'
        self.fields['gender'].label = 'Genero'
        self.fields['birth_date'].label = 'Nascimento'
        self.fields['health_issue_status'].label = 'Algum problema de saude?'
        self.fields['cpf'].label = 'CPF do aluno'
        self.fields['notes'].label = 'Descreva o problema, se houver'
        self.fields['intake_record'].queryset = StudentIntake.objects.filter(
            linked_student__isnull=True,
            status__in=[IntakeStatus.NEW, IntakeStatus.REVIEWING, IntakeStatus.MATCHED],
        ).order_by('status', '-created_at')
        self.fields['intake_record'].help_text = 'Use isso para transformar uma entrada provisoria em aluno definitivo.'
        self.fields['selected_plan'].queryset = MembershipPlan.objects.filter(active=True).order_by('price', 'name')
        self.fields['selected_plan'].help_text = 'Esse plano ja fica pronto para conversar com matricula e financeiro.'
        self.fields['enrollment_status'].label = 'Status do plano no aluno'
        self.fields['payment_method'].initial = PaymentMethod.PIX
        self.fields['confirm_payment_now'].initial = False
        self.fields['payment_due_date'].initial = timezone.localdate()
        self.fields['billing_strategy'].initial = 'single'
        self.fields['installment_total'].initial = 1
        self.fields['recurrence_cycles'].initial = 3

        self.fields['full_name'].widget.attrs.update({'placeholder': 'Ex.: Mariana Souza'})
        self.fields['phone'].widget.attrs.update({'placeholder': 'Ex.: 5511999999999'})
        self.fields['email'].widget.attrs.update({'placeholder': 'Opcional neste momento'})
        self.fields['cpf'].widget.attrs.update({'placeholder': 'Ex.: 123.456.789-00'})
        self.fields['notes'].widget.attrs.update({'placeholder': 'Descreva o problema de saude ou deixe em branco.'})
        self.fields['payment_reference'].widget.attrs.update({'placeholder': 'Ex.: PIX-MAR-2026'})
        self.fields['initial_payment_amount'].widget.attrs.update({'placeholder': 'Ex.: 289.90', 'step': '0.01'})

        self.fields['email'].required = False
        self.fields['gender'].required = False
        self.fields['birth_date'].required = False
        self.fields['health_issue_status'].required = False
        self.fields['cpf'].required = False
        self.fields['notes'].required = False
        self.fields['enrollment_status'].initial = EnrollmentStatus.PENDING
        self.fields['payment_method'].required = False
        self.fields['payment_due_date'].required = False
        self.fields['payment_reference'].required = False
        self.fields['initial_payment_amount'].required = False
        self.fields['billing_strategy'].required = False
        self.fields['installment_total'].required = False
        self.fields['recurrence_cycles'].required = False

        # Na edicao, o formulario precisa nascer refletindo a situacao comercial atual do aluno.
        latest_enrollment = None
        if self.instance.pk:
            latest_enrollment = self.instance.enrollments.select_related('plan').order_by('-start_date', '-created_at').first()

        if latest_enrollment is not None:
            self.fields['selected_plan'].initial = latest_enrollment.plan
            self.fields['enrollment_status'].initial = latest_enrollment.status
            latest_payment = latest_enrollment.payments.order_by('-due_date', '-created_at').first()
            if latest_payment is not None:
                self.fields['payment_method'].initial = latest_payment.method
                self.fields['confirm_payment_now'].initial = latest_payment.status == 'paid'
                self.fields['payment_due_date'].initial = latest_payment.due_date
                self.fields['payment_reference'].initial = latest_payment.reference
                self.fields['initial_payment_amount'].initial = latest_payment.amount
                self.fields['installment_total'].initial = latest_payment.installment_total

        linked_intake = self.instance.intake_records.order_by('-created_at').first() if self.instance.pk else None
        if linked_intake is not None:
            self.fields['intake_record'].initial = linked_intake

    def clean(self):
        cleaned_data = super().clean()
        selected_plan = cleaned_data.get('selected_plan')
        billing_strategy = cleaned_data.get('billing_strategy') or 'single'
        confirm_payment_now = bool(cleaned_data.get('confirm_payment_now'))
        initial_payment_amount = cleaned_data.get('initial_payment_amount')
        enrollment_status = cleaned_data.get('enrollment_status')
        student_status = cleaned_data.get('status')

        if billing_strategy in ('installments', 'recurring') and selected_plan is None:
            self.add_error('selected_plan', 'Escolha um plano antes de usar parcelamento ou recorrencia.')

        if confirm_payment_now and selected_plan is None:
            self.add_error('confirm_payment_now', 'Nao da para confirmar pagamento inicial sem plano conectado.')

        if selected_plan is not None and initial_payment_amount is not None and initial_payment_amount <= 0:
            self.add_error('initial_payment_amount', 'O valor inicial da cobranca precisa ser maior que zero.')

        if selected_plan is not None and enrollment_status == EnrollmentStatus.ACTIVE and student_status == StudentStatus.LEAD:
            self.add_error('status', 'Lead nao pode sair com matricula ativa. Ajuste o status do aluno para ativo, pausado ou inativo.')

        return cleaned_data


class PaymentManagementForm(forms.Form):
    payment_id = forms.IntegerField(widget=forms.HiddenInput)
    amount = forms.DecimalField(decimal_places=2, max_digits=10, min_value=0, label='Valor da cobranca')
    due_date = forms.DateField(label='Vencimento', widget=forms.DateInput(attrs={'type': 'date'}))
    method = forms.ChoiceField(choices=PaymentMethod.choices, label='Metodo')
    reference = forms.CharField(required=False, label='Referencia')
    notes = forms.CharField(required=False, label='Observacoes', widget=forms.Textarea(attrs={'rows': 3}))


class EnrollmentManagementForm(forms.Form):
    enrollment_id = forms.IntegerField(widget=forms.HiddenInput)
    action_date = forms.DateField(label='Data da acao', widget=forms.DateInput(attrs={'type': 'date'}))
    reason = forms.CharField(required=False, label='Motivo', widget=forms.Textarea(attrs={'rows': 3}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['action_date'].initial = timezone.localdate()


class FinanceFilterForm(forms.Form):
    months = forms.ChoiceField(
        required=False,
        label='Janela',
        choices=(('1', '1 mes'), ('3', '3 meses'), ('6', '6 meses'), ('12', '12 meses')),
    )
    plan = forms.ModelChoiceField(
        queryset=MembershipPlan.objects.all().order_by('name'),
        required=False,
        label='Plano',
        empty_label='Todos os planos',
    )
    payment_status = forms.ChoiceField(
        required=False,
        label='Status financeiro',
        choices=(('', 'Todos'), *PaymentStatus.choices),
    )
    payment_method = forms.ChoiceField(
        required=False,
        label='Metodo',
        choices=(('', 'Todos'), *PaymentMethod.choices),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['months'].initial = '6'


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


class MembershipPlanQuickForm(forms.ModelForm):
    active = forms.TypedChoiceField(
        label='Status do plano',
        choices=((True, 'Ativo'), (False, 'Inativo')),
        coerce=lambda value: value in (True, 'True', 'true', '1', 'on'),
        widget=forms.Select,
    )

    class Meta:
        model = MembershipPlan
        fields = [
            'name',
            'price',
            'billing_cycle',
            'sessions_per_week',
            'description',
            'active',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].label = 'Nome do plano'
        self.fields['price'].label = 'Valor do plano'
        self.fields['billing_cycle'].label = 'Ciclo de cobranca'
        self.fields['sessions_per_week'].label = 'Aulas por semana'
        self.fields['description'].label = 'O que este plano entrega'

        self.fields['name'].widget.attrs.update({'placeholder': 'Ex.: Cross Prime'})
        self.fields['price'].widget.attrs.update({'placeholder': 'Ex.: 289.90', 'step': '0.01'})
        self.fields['sessions_per_week'].widget.attrs.update({'placeholder': 'Ex.: 3'})
        self.fields['description'].widget.attrs.update({'placeholder': 'Descreva proposta, limite e observacoes comerciais do plano.'})

        self.fields['description'].required = False


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

        self.fields['title'].widget.attrs.update({'placeholder': 'Ex.: WOD 07h'} )
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
