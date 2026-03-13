"""
ARQUIVO: formularios da leitura e gestao financeira.

POR QUE ELE EXISTE:
- separa os formularios de financeiro do fluxo de alunos e da grade de aulas no app real catalog.

O QUE ESTE ARQUIVO FAZ:
1. define os filtros da central financeira.
2. define o formulario leve de plano financeiro.

PONTOS CRITICOS:
- esses formularios afetam filtros, portfolio de planos e operacao comercial.
"""

from django import forms

from finance.models import MembershipPlan, PaymentMethod, PaymentStatus
from shared_support.form_inputs import apply_currency_input_attrs, apply_integer_input_attrs, apply_text_input_attrs


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
        apply_text_input_attrs(self.fields['plan'], maxlength=100)


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

        apply_text_input_attrs(self.fields['name'], placeholder='Ex.: Cross Prime', maxlength=100)
        apply_currency_input_attrs(self.fields['price'], placeholder='Ex.: 289.90')
        apply_integer_input_attrs(self.fields['sessions_per_week'], placeholder='Ex.: 3', min_value=1, maxlength=2)
        apply_text_input_attrs(self.fields['description'], placeholder='Descreva proposta, limite e observacoes comerciais do plano.')

        self.fields['description'].required = False