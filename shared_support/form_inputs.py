"""
ARQUIVO: utilitarios compartilhados para digitacao guiada e normalizacao de inputs.

POR QUE ELE EXISTE:
- centraliza limites, mascaras leves e normalizacao segura para formularios do produto.

O QUE ESTE ARQUIVO FAZ:
1. aplica atributos consistentes em campos recorrentes.
2. normaliza horarios digitados de forma humana para formato HH:MM.
3. reduz repeticao de configuracao entre formularios.

PONTOS CRITICOS:
- mudancas aqui afetam a experiencia de digitacao em varias telas.
"""

from django import forms


def apply_widget_attrs(field, **attrs):
    normalized_attrs = {
        key: str(value)
        for key, value in attrs.items()
        if value is not None
    }
    field.widget.attrs.update(normalized_attrs)


def apply_text_input_attrs(field, *, placeholder=None, maxlength=None, autocomplete='off', spellcheck='false'):
    apply_widget_attrs(
        field,
        placeholder=placeholder,
        maxlength=maxlength,
        autocomplete=autocomplete,
        spellcheck=spellcheck,
    )


def apply_phone_input_attrs(field, *, placeholder=None):
    apply_widget_attrs(
        field,
        placeholder=placeholder,
        inputmode='numeric',
        autocomplete='tel',
        maxlength=20,
        pattern='[0-9]{10,20}',
        **{'data-mask': 'phone'},
    )


def apply_cpf_input_attrs(field, *, placeholder=None):
    apply_widget_attrs(
        field,
        placeholder=placeholder,
        inputmode='numeric',
        autocomplete='off',
        maxlength=14,
        pattern=r'\d{3}\.\d{3}\.\d{3}-\d{2}',
        **{'data-mask': 'cpf'},
    )


def apply_currency_input_attrs(field, *, placeholder=None):
    field.widget.input_type = 'text'
    apply_widget_attrs(
        field,
        placeholder=placeholder,
        inputmode='decimal',
        autocomplete='off',
        min='0',
        step='0.01',
        maxlength=7,
        pattern=r'\d{1,4}([\.,]\d{0,2})?',
        **{'data-mask': 'currency', 'data-currency-max-integer-digits': '4', 'data-decimal-places': '2'},
    )


def apply_integer_input_attrs(field, *, placeholder=None, min_value=None, max_value=None, maxlength=None):
    field.widget.input_type = 'text'
    apply_widget_attrs(
        field,
        placeholder=placeholder,
        inputmode='numeric',
        min=min_value,
        max=max_value,
        step='1',
        maxlength=maxlength,
        pattern=rf'\d{{1,{maxlength}}}' if maxlength else None,
        **{'data-mask': 'integer', 'data-max-digits': maxlength},
    )


def apply_date_input_attrs(field, *, placeholder=None, maxlength=None, pattern=None):
    year_digits = '4'
    if maxlength == 8:
        year_digits = '2'
    elif maxlength == 10:
        year_digits = '4'

    apply_widget_attrs(
        field,
        placeholder=placeholder,
        inputmode='numeric',
        autocomplete='off',
        maxlength=maxlength,
        pattern=pattern,
        **{'data-mask': 'date', 'data-year-digits': year_digits},
    )


def apply_time_input_attrs(field, *, placeholder='07:00'):
    apply_widget_attrs(
        field,
        type='text',
        placeholder=placeholder,
        inputmode='numeric',
        autocomplete='off',
        maxlength=5,
        pattern=r'([01]\d|2[0-3]):[0-5]\d',
        **{'data-mask': 'time'},
    )


def normalize_time_value(raw_value):
    text = str(raw_value or '').strip()
    if not text:
        return text

    hour_text = ''
    minute_text = ''

    if ':' in text:
        left, right = text.split(':', 1)
        hour_text = ''.join(character for character in left if character.isdigit())
        minute_text = ''.join(character for character in right if character.isdigit())
        if not hour_text:
            return text
        if not minute_text:
            minute_text = '00'
        elif len(minute_text) == 1:
            minute_text = f'{minute_text}0'
        else:
            minute_text = minute_text[:2]
    else:
        digits = ''.join(character for character in text if character.isdigit())
        if not digits:
            return text
        if len(digits) <= 2:
            hour_text = digits
            minute_text = '00'
        elif len(digits) == 3:
            hour_text = digits[0]
            minute_text = digits[1:3]
        else:
            hour_text = digits[:2]
            minute_text = digits[2:4]

    try:
        hour = int(hour_text)
        minute = int(minute_text)
    except ValueError:
        return text

    if hour > 23 or minute > 59:
        return text

    return f'{hour:02d}:{minute:02d}'


class LenientTimeField(forms.TimeField):
    def to_python(self, value):
        if isinstance(value, str):
            value = normalize_time_value(value)
        return super().to_python(value)


__all__ = [
    'LenientTimeField',
    'apply_cpf_input_attrs',
    'apply_currency_input_attrs',
    'apply_date_input_attrs',
    'apply_integer_input_attrs',
    'apply_phone_input_attrs',
    'apply_text_input_attrs',
    'apply_time_input_attrs',
    'apply_widget_attrs',
    'normalize_time_value',
]