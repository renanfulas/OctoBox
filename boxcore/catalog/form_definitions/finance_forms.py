"""
ARQUIVO: formularios da leitura e gestao financeira.

POR QUE ELE EXISTE:
- Separa os formularios de financeiro do fluxo de alunos e da grade de aulas.

O QUE ESTE ARQUIVO FAZ:
1. Define os filtros da central financeira.
2. Define o formulario leve de plano financeiro.

PONTOS CRITICOS:
- Esses formularios afetam filtros, portfolio de planos e operacao comercial.
"""

from django import forms

from finance.models import MembershipPlan, PaymentMethod, PaymentStatus


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