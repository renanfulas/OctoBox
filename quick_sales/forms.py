"""
ARQUIVO: formularios publicos do dominio quick_sales.

POR QUE ELE EXISTE:
- valida a entrada canonica das vendas rapidas sem depender do fluxo de mensalidades.

O QUE ESTE ARQUIVO FAZ:
1. define o formulario de criacao de venda rapida.
2. define o formulario de acoes operacionais sobre a venda.

PONTOS CRITICOS:
- o valor precisa seguir a mesma normalizacao segura de moeda do restante do produto.
- template_id e opcional porque a V1 ainda aceita venda totalmente manual.
"""

from django import forms
from decimal import Decimal

from finance.models import PaymentMethod
from quick_sales.models import QuickSale
from shared_support.form_inputs import apply_currency_input_attrs, apply_text_input_attrs


class QuickSaleManagementForm(forms.Form):
    template_id = forms.IntegerField(widget=forms.HiddenInput, required=False, min_value=1)
    description = forms.CharField(max_length=120, label='Descricao do produto')
    amount = forms.DecimalField(decimal_places=2, max_digits=10, min_value=0, label='Valor total')
    method = forms.ChoiceField(choices=PaymentMethod.choices, label='Metodo')
    reference = forms.CharField(required=False, max_length=100, label='Referencia')
    notes = forms.CharField(required=False, label='Observacoes', widget=forms.Textarea(attrs={'rows': 3}))

    def __init__(self, *args, **kwargs):
        if args and args[0] is not None:
            args = list(args)
            args[0] = self._normalize_bound_data(args[0])
        elif kwargs.get('data') is not None:
            kwargs = dict(kwargs)
            kwargs['data'] = self._normalize_bound_data(kwargs['data'])
        super().__init__(*args, **kwargs)
        apply_text_input_attrs(self.fields['description'], placeholder='Ex.: Agua, energetico, barra', maxlength=120)
        apply_currency_input_attrs(self.fields['amount'], placeholder='Ex.: 5.00')
        self.fields['amount'].widget.attrs.update(
            {
                'maxlength': '6',
                'pattern': r'\d{1,3}([\.,]\d{0,2})?',
                'data-currency-max-integer-digits': '3',
            }
        )
        apply_text_input_attrs(self.fields['reference'], placeholder='Ex.: BALCAO-PIX-001', maxlength=100)
        apply_text_input_attrs(self.fields['notes'], placeholder='Observacao curta da venda rapida.')

    def clean_description(self):
        return ' '.join((self.cleaned_data.get('description') or '').split())

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is None:
            return amount
        if amount > Decimal('999.99'):
            raise forms.ValidationError('O valor maximo para pagamento rapido e R$ 999,99.')
        return amount

    @staticmethod
    def _normalize_bound_data(data):
        raw_amount = data.get('amount') if hasattr(data, 'get') else None
        if not isinstance(raw_amount, str) or ',' not in raw_amount:
            return data

        normalized_data = data.copy()
        normalized_amount = raw_amount.replace('.', '').replace(',', '.') if '.' in raw_amount else raw_amount.replace(',', '.')
        normalized_data['amount'] = normalized_amount
        return normalized_data


class QuickSaleActionForm(forms.Form):
    ACTION_CHOICES = (
        ('create-quick-sale', 'Registrar pagamento rapido'),
        ('cancel-quick-sale', 'Cancelar venda rapida'),
        ('refund-quick-sale', 'Estornar venda rapida'),
    )

    quick_sale_id = forms.IntegerField(widget=forms.HiddenInput, required=False, min_value=1)
    action = forms.ChoiceField(choices=ACTION_CHOICES)

    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        quick_sale_id = cleaned_data.get('quick_sale_id')
        if action in {'cancel-quick-sale', 'refund-quick-sale'} and not quick_sale_id:
            raise forms.ValidationError('A venda rapida precisa ser informada para esta acao.')
        return cleaned_data


class QuickSaleStatusUpdateForm(forms.ModelForm):
    class Meta:
        model = QuickSale
        fields = ['status', 'notes']


__all__ = [
    'QuickSaleActionForm',
    'QuickSaleManagementForm',
    'QuickSaleStatusUpdateForm',
]
