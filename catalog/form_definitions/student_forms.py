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
from onboarding.attribution import extract_acquisition_channel
from shared_support.crypto_fields import generate_blind_index
from shared_support.acquisition import ACQUISITION_CHANNEL_CHOICES, normalize_acquisition_channel
from shared_support.form_inputs import (
    apply_cpf_input_attrs,
    apply_currency_input_attrs,
    apply_date_input_attrs,
    apply_integer_input_attrs,
    apply_phone_input_attrs,
    apply_text_input_attrs,
)
from shared_support.phone_numbers import normalize_phone_number
from students.domain import resolve_acquisition_resolution
from students.infrastructure.django_attribution import get_active_student_source_declaration
from students.models import SourceConfidence, SourceResolutionMethod, Student, StudentStatus


def _student_phone_exists(*, normalized_phone, instance_pk=None):
    phone_lookup_index = generate_blind_index(normalized_phone)
    queryset = Student.objects.all()
    if instance_pk is not None:
        queryset = queryset.exclude(pk=instance_pk)

    if phone_lookup_index:
        return queryset.filter(phone_lookup_index=phone_lookup_index).exists()

    return queryset.filter(phone=normalized_phone).exists()


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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_text_input_attrs(self.fields['query'], placeholder='Nome, WhatsApp ou CPF', maxlength=150)


class StudentQuickForm(forms.ModelForm):
    acquisition_source = forms.ChoiceField(
        required=True,
        label='Origem de aquisicao',
        choices=tuple(choice for choice in ACQUISITION_CHANNEL_CHOICES if choice[0] not in ('legacy',)),
    )
    acquisition_source_detail = forms.CharField(
        required=False,
        label='Detalhe da origem',
        max_length=120,
    )
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
        widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
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
            'acquisition_source',
            'acquisition_source_detail',
            'notes',
        ]
        widgets = {
            'birth_date': forms.DateInput(attrs={'type': 'text'}, format='%d/%m/%Y'),
            'notes': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['full_name'].label = 'Nome completo'
        self.fields['phone'].label = 'WhatsApp'
        self.fields['phone'].help_text = 'Use o numero principal de contato do aluno.'
        self.fields['status'].label = 'Status inicial'
        self.fields['status'].choices = [
            choice for choice in StudentStatus.choices 
            if choice[0] in (StudentStatus.LEAD, StudentStatus.ACTIVE)
        ]
        self.fields['email'].label = 'E-mail'
        self.fields['gender'].label = 'Genero'
        self.fields['birth_date'].label = 'Nascimento (dd/mm/aaaa)'
        self.fields['health_issue_status'].label = 'Algum problema de saude?'
        self.fields['cpf'].label = 'CPF do aluno'
        self.fields['acquisition_source'].help_text = 'Esse dado sustenta leitura comercial, reconciliacao e ML futuro.'
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
        apply_text_input_attrs(self.fields['full_name'], placeholder='Ex.: Mariana Souza', maxlength=150, autocomplete='name')
        apply_phone_input_attrs(self.fields['phone'], placeholder='Ex.: 5511999999999')
        apply_text_input_attrs(self.fields['email'], placeholder='Opcional neste momento', maxlength=254, autocomplete='email')
        apply_date_input_attrs(self.fields['birth_date'], placeholder='dd/mm/aaaa', maxlength=10, pattern=r'\d{2}/\d{2}/\d{4}')
        apply_cpf_input_attrs(self.fields['cpf'], placeholder='Ex.: 123.456.789-00')
        apply_text_input_attrs(self.fields['acquisition_source_detail'], placeholder='Ex.: indicacao do Joao, Google Maps, passou na frente', maxlength=120)
        apply_text_input_attrs(self.fields['notes'], placeholder='Descreva o problema de saude ou deixe em branco.')
        apply_text_input_attrs(self.fields['payment_reference'], placeholder='Ex.: PIX-MAR-2026', maxlength=100)
        apply_currency_input_attrs(self.fields['initial_payment_amount'], placeholder='Ex.: 289.90')
        apply_integer_input_attrs(self.fields['installment_total'], placeholder='Ex.: 3', min_value=1, max_value=12, maxlength=2)
        apply_integer_input_attrs(self.fields['recurrence_cycles'], placeholder='Ex.: 3', min_value=1, max_value=12, maxlength=2)

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

        if self.instance.pk:
            self.fields['acquisition_source'].initial = self.instance.acquisition_source or self.instance.resolved_acquisition_source
            self.fields['acquisition_source_detail'].initial = self.instance.acquisition_source_detail or self.instance.resolved_source_detail
            self.active_source_declaration = get_active_student_source_declaration(self.instance)
        else:
            self.active_source_declaration = None

        intake_record = self.initial.get('intake_record')
        if isinstance(intake_record, StudentIntake):
            intake_channel = extract_acquisition_channel(
                raw_payload=getattr(intake_record, 'raw_payload', {}),
                fallback_source=getattr(intake_record, 'source', ''),
            )
            intake_detail = (
                ((getattr(intake_record, 'raw_payload', {}) or {}).get('attribution') or {}).get('acquisition', {}) or {}
            ).get('declared_detail', '')
            if intake_channel and not self.fields['acquisition_source'].initial:
                self.fields['acquisition_source'].initial = intake_channel
            if intake_detail and not self.fields['acquisition_source_detail'].initial:
                self.fields['acquisition_source_detail'].initial = intake_detail

    def clean_phone(self):
        phone = normalize_phone_number(self.cleaned_data.get('phone'))
        if not phone:
            return ''
        student_id = self.instance.pk if self.instance else None
        if _student_phone_exists(normalized_phone=phone, instance_pk=student_id):
            raise forms.ValidationError('Já existe um aluno cadastrado com este WhatsApp.')
        return phone

    def clean_cpf(self):
        raw_cpf = ''.join(character for character in (self.cleaned_data.get('cpf') or '') if character.isdigit())
        if not raw_cpf:
            return ''
        
        # 1. Validar CPF Dígito Verificador
        if len(raw_cpf) != 11 or raw_cpf == raw_cpf[0]*11:
            raise forms.ValidationError('Informe um CPF valido com 11 digitos.')
        
        # Algoritmo de validação de CPF
        for i in range(9, 11):
            val = sum(int(raw_cpf[num]) * ((i+1) - num) for num in range(0, i))
            digit = ((val * 10) % 11) % 10
            if digit != int(raw_cpf[i]):
                raise forms.ValidationError('CPF inválido (Dígito verificador incorreto).')

        # 2. Validar Duplicidade
        student_id = self.instance.pk if self.instance else None
        if Student.objects.filter(cpf=f'{raw_cpf[:3]}.{raw_cpf[3:6]}.{raw_cpf[6:9]}-{raw_cpf[9:]}').exclude(pk=student_id).exists() or Student.objects.filter(cpf=raw_cpf).exclude(pk=student_id).exists():
            raise forms.ValidationError('Já existe um aluno cadastrado com este CPF.')

        return f'{raw_cpf[:3]}.{raw_cpf[3:6]}.{raw_cpf[6:9]}-{raw_cpf[9:]}'

    def clean_acquisition_source(self):
        acquisition_source = normalize_acquisition_channel(self.cleaned_data.get('acquisition_source'))
        if not acquisition_source:
            raise forms.ValidationError('Escolha a origem de aquisicao antes de continuar.')
        return acquisition_source

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

        acquisition_source = cleaned_data.get('acquisition_source')
        acquisition_source_detail = (cleaned_data.get('acquisition_source_detail') or '').strip()
        selected_intake = cleaned_data.get('intake_record')
        active_declaration = self.active_source_declaration

        preferred_method = ''
        if acquisition_source:
            if self.instance.pk and self.instance.acquisition_source and self.instance.acquisition_source != acquisition_source:
                preferred_method = SourceResolutionMethod.MANUAL_REVIEW
            elif selected_intake:
                preferred_method = SourceResolutionMethod.INTAKE_AUTO
            else:
                preferred_method = SourceResolutionMethod.MANUAL_FORM

        if acquisition_source:
            resolution = resolve_acquisition_resolution(
                operational_source=acquisition_source,
                operational_detail=acquisition_source_detail,
                operational_method=preferred_method,
                declared_source=getattr(active_declaration, 'declared_acquisition_source', ''),
                declared_detail=getattr(active_declaration, 'declared_source_detail', ''),
            )
            cleaned_data['resolved_acquisition_source'] = resolution.resolved_acquisition_source
            cleaned_data['resolved_source_detail'] = resolution.resolved_source_detail
            cleaned_data['source_confidence'] = resolution.source_confidence
            cleaned_data['source_conflict_flag'] = resolution.source_conflict_flag
            cleaned_data['source_resolution_method'] = resolution.source_resolution_method
            cleaned_data['source_resolution_reason'] = resolution.source_resolution_reason
            cleaned_data['source_captured_at'] = timezone.now()
        else:
            cleaned_data['source_confidence'] = SourceConfidence.UNKNOWN

        return cleaned_data


class StudentExpressForm(forms.ModelForm):
    selected_plan = forms.ModelChoiceField(
        queryset=MembershipPlan.objects.none(),
        required=False,
        label='Vincular Plano Rapido',
        empty_label='Apenas cadastrar',
    )
    initial_payment_amount = forms.DecimalField(
        required=False,
        min_value=0,
        decimal_places=2,
        max_digits=10,
        label='Valor inicial (Opcional)',
    )

    class Meta:
        model = Student
        fields = ['full_name', 'phone']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['full_name'].label = 'Nome do aluno'
        self.fields['phone'].label = 'WhatsApp'
        self.fields['selected_plan'].queryset = MembershipPlan.objects.filter(active=True).order_by('price', 'name')
        
        apply_text_input_attrs(self.fields['full_name'], placeholder='Ex.: Carlos Lima', maxlength=150, autocomplete='name')
        apply_phone_input_attrs(self.fields['phone'], placeholder='Ex.: (11) 99999-9999')
        apply_currency_input_attrs(self.fields['initial_payment_amount'], placeholder='Ex.: 120.00')

    def clean_phone(self):
        phone = normalize_phone_number(self.cleaned_data.get('phone'))
        if not phone:
            return ''
        if _student_phone_exists(normalized_phone=phone):
            raise forms.ValidationError('Ja existe aluno cadastrado com este numero.')
        return phone


class StudentSourceDeclarationCaptureForm(forms.Form):
    token = forms.CharField(widget=forms.HiddenInput)
    declared_acquisition_source = forms.ChoiceField(
        required=True,
        label='Como voce conheceu o box?',
        choices=tuple(choice for choice in ACQUISITION_CHANNEL_CHOICES if choice[0] not in ('', 'legacy')),
    )
    declared_source_detail = forms.CharField(
        required=False,
        label='Detalhe opcional',
        max_length=120,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_text_input_attrs(
            self.fields['declared_source_detail'],
            placeholder='Ex.: indicacao da Ana, Google Maps, passei na frente',
            maxlength=120,
        )


class PaymentManagementForm(forms.Form):
    payment_id = forms.IntegerField(widget=forms.HiddenInput, required=False)
    amount = forms.DecimalField(decimal_places=2, max_digits=10, min_value=0, label='Valor da cobranca')
    due_date = forms.DateField(label='Vencimento', input_formats=['%d/%m/%Y', '%Y-%m-%d'], widget=forms.DateInput(attrs={'type': 'text'}, format='%d/%m/%Y'))
    method = forms.ChoiceField(choices=PaymentMethod.choices, label='Metodo')
    reference = forms.CharField(required=False, label='Referencia')
    notes = forms.CharField(required=False, label='Observacoes', widget=forms.Textarea(attrs={'rows': 3}))

    def __init__(self, *args, **kwargs):
        self.instance = kwargs.pop('instance', None)
        if args and args[0] is not None:
            args = list(args)
            args[0] = self._normalize_bound_data(args[0])
        elif kwargs.get('data') is not None:
            kwargs = dict(kwargs)
            kwargs['data'] = self._normalize_bound_data(kwargs['data'])
        super().__init__(*args, **kwargs)
        apply_currency_input_attrs(self.fields['amount'], placeholder='Ex.: 289.90')
        apply_date_input_attrs(self.fields['due_date'], placeholder='dd/mm/aaaa', maxlength=10, pattern=r'\d{2}/\d{2}/\d{4}')
        apply_text_input_attrs(self.fields['reference'], placeholder='Ex.: PIX-MAR-2026', maxlength=100)
        apply_text_input_attrs(self.fields['notes'], placeholder='Observacao curta para a cobranca.')

    @staticmethod
    def _normalize_bound_data(data):
        raw_amount = data.get('amount') if hasattr(data, 'get') else None
        if not isinstance(raw_amount, str) or ',' not in raw_amount:
            return data

        normalized_data = data.copy()
        normalized_amount = raw_amount.replace('.', '').replace(',', '.') if '.' in raw_amount else raw_amount.replace(',', '.')
        normalized_data['amount'] = normalized_amount
        return normalized_data


class StudentPaymentActionForm(forms.Form):
    ACTION_CHOICES = (
        ('create-payment', 'Nova Cobranca Avulsa'),
        ('update-payment', 'Salvar Ajustes (Vencimento/Valor)'),
        ('mark-paid', 'Confirmar Recebimento (Pago)'),
        ('refund-payment', 'Estornar Pagamento'),
        ('cancel-payment', 'Cancelar Cobranca (Inativar)'),
        ('regenerate-payment', 'Regenerar cobranca'),
    )

    payment_id = forms.IntegerField(widget=forms.HiddenInput, min_value=1, required=False)
    action = forms.ChoiceField(choices=ACTION_CHOICES)


class ReceptionPaymentManagementForm(forms.Form):
    ACTION_CHOICES = (
        ('update-payment', 'Salvar Ajuste Rápido'),
        ('mark-paid', 'Confirmar Recebimento Agora'),
    )

    payment_id = forms.IntegerField(widget=forms.HiddenInput)
    action = forms.ChoiceField(choices=ACTION_CHOICES)
    due_date = forms.DateField(label='Vencimento', input_formats=['%d/%m/%Y', '%Y-%m-%d'], widget=forms.DateInput(attrs={'type': 'text'}, format='%d/%m/%Y'))
    method = forms.ChoiceField(choices=PaymentMethod.choices, label='Metodo')
    reference = forms.CharField(required=False, label='Referencia')
    notes = forms.CharField(required=False, label='Observacoes')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_date_input_attrs(self.fields['due_date'], placeholder='dd/mm/aaaa', maxlength=10, pattern=r'\d{2}/\d{2}/\d{4}')
        apply_text_input_attrs(self.fields['reference'], placeholder='Ex.: PIX-MAR-2026', maxlength=100)
        apply_text_input_attrs(self.fields['notes'], placeholder='Observacao curta para a cobranca.', maxlength=255)


class FinanceCommunicationActionForm(forms.Form):
    ACTION_KIND_CHOICES = (
        ('upcoming', 'Lembrete de vencimento'),
        ('overdue', 'Cobranca em atraso'),
        ('reactivation', 'Reativacao'),
    )

    action_kind = forms.ChoiceField(choices=ACTION_KIND_CHOICES)
    student_id = forms.IntegerField(min_value=1)
    payment_id = forms.IntegerField(required=False, min_value=1)
    enrollment_id = forms.IntegerField(required=False, min_value=1)


class EnrollmentManagementForm(forms.Form):
    ACTION_CHOICES = (
        ('cancel-enrollment', 'Cancelar matricula'),
        ('reactivate-enrollment', 'Reativar matricula'),
    )

    enrollment_id = forms.IntegerField(widget=forms.HiddenInput)
    action = forms.ChoiceField(choices=ACTION_CHOICES)
    action_date = forms.DateField(label='Data da acao', widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'))
    reason = forms.CharField(required=False, label='Motivo', widget=forms.Textarea(attrs={'rows': 3}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['action_date'].initial = timezone.localdate()
        apply_date_input_attrs(self.fields['action_date'], placeholder='dd/mm/aaaa')
        apply_text_input_attrs(self.fields['reason'], placeholder='Explique o motivo da acao, se precisar.')
