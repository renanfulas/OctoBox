"""
ARQUIVO: formularios do fluxo de alunos e ficha comercial.

POR QUE ELE EXISTE:
- isola os formularios ligados a alunos, intake, matricula e cobranca inicial no app real catalog.

O QUE ESTE ARQUIVO FAZ:
1. define filtros do diretorio de alunos.
2. define o formulario leve de criacao e edicao de aluno.
3. define formularios pontuais de pagamento e matricula.

PONTOS CRITICOS:
- essas validacoes sustentam o principal fluxo operacional do produto.
"""

from django import forms
from django.utils import timezone

from communications.models import IntakeStatus, StudentIntake
from finance.models import EnrollmentStatus, MembershipPlan, PaymentMethod, PaymentStatus
from students.models import Student, StudentStatus


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