"""
ARQUIVO: formularios das paginas visuais de catalogo.

POR QUE ELE EXISTE:
- Centraliza os formularios leves que sustentam alunos, financeiro e acoes comerciais fora do admin bruto.

O QUE ESTE ARQUIVO FAZ:
1. Define filtros da pagina de alunos e do centro financeiro.
2. Define o formulario leve de aluno com intake, plano e cobranca inicial.
3. Define formularios de gestao pontual para pagamento e matricula.
4. Define o formulario leve de plano financeiro.

PONTOS CRITICOS:
- Estes formularios espelham a camada operacional mais usada do produto.
- Defaults e querysets errados aqui distorcem cadastro, conversao de leads e leitura financeira.
"""

from django import forms
from django.utils import timezone

from boxcore.models import (
    EnrollmentStatus,
    IntakeStatus,
    MembershipPlan,
    PaymentMethod,
    PaymentStatus,
    Student,
    StudentIntake,
    StudentStatus,
)


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
        self.fields['notes'].label = 'Descreva o problema / Se nao, deixe em branco'
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
