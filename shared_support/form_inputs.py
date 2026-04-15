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

from datetime import date

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


class DateInputValidationError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def parse_lenient_date_value(raw_value, *, year_digits=4, min_year=None, max_year=None):
    text = str(raw_value or '').strip()
    if not text:
        return None

    accepted_year_digits = 2 if year_digits == 2 else 4
    max_digits = 4 + accepted_year_digits
    digits = ''.join(character for character in text if character.isdigit())
    if len(digits) != max_digits:
        raise DateInputValidationError('incomplete')

    try:
        day = int(digits[:2])
        month = int(digits[2:4])
        raw_year = int(digits[4:max_digits])
    except ValueError as exc:
        raise DateInputValidationError('invalid') from exc

    year = 2000 + raw_year if accepted_year_digits == 2 else raw_year
    if min_year is not None and year < int(min_year):
        raise DateInputValidationError('min_year')
    if max_year is not None and year > int(max_year):
        raise DateInputValidationError('max_year')

    try:
        return date(year, month, day)
    except ValueError as exc:
        raise DateInputValidationError('invalid') from exc


def normalize_date_value(raw_value, *, year_digits=4, min_year=None, max_year=None):
    parsed_date = parse_lenient_date_value(
        raw_value,
        year_digits=year_digits,
        min_year=min_year,
        max_year=max_year,
    )
    if parsed_date is None:
        return ''
    if year_digits == 2:
        return parsed_date.strftime('%d/%m/%y')
    return parsed_date.strftime('%d/%m/%Y')


class LenientDateField(forms.DateField):
    default_error_messages = {
        'invalid': 'Informe uma data valida no formato dd/mm/aaaa.',
        'incomplete': 'Use a data no formato dd/mm/aaaa. Ex.: 21/11/1995.',
        'min_year': 'O ano precisa estar dentro do intervalo permitido.',
        'max_year': 'O ano precisa estar dentro do intervalo permitido.',
    }

    def __init__(self, *args, year_digits=4, min_year=None, max_year=None, **kwargs):
        self.year_digits = 2 if year_digits == 2 else 4
        self.min_year = min_year
        self.max_year = max_year
        kwargs.setdefault('input_formats', ['%d/%m/%Y'] if self.year_digits == 4 else ['%d/%m/%y'])
        super().__init__(*args, **kwargs)

    def to_python(self, value):
        if value in self.empty_values:
            return None
        if isinstance(value, date):
            return value
        if isinstance(value, str) and any(not character.isdigit() for character in value.strip()):
            return super().to_python(value)
        try:
            return parse_lenient_date_value(
                value,
                year_digits=self.year_digits,
                min_year=self.min_year,
                max_year=self.max_year,
            )
        except DateInputValidationError as exc:
            raise forms.ValidationError(self.error_messages[exc.code], code=exc.code) from exc


def apply_date_input_attrs(field, *, placeholder=None, maxlength=None, pattern=None, min_year=None, max_year=None):
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
        **{
            'data-mask': 'date',
            'data-year-digits': year_digits,
            'data-min-year': min_year,
            'data-max-year': max_year,
            'data-date-invalid-message': 'Informe uma data valida no formato dd/mm/aaaa.',
            'data-date-incomplete-message': 'Use a data no formato dd/mm/aaaa. Ex.: 21/11/1995.',
            'data-date-range-message': 'O ano precisa estar dentro do intervalo permitido.',
        },
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
    'LenientDateField',
    'LenientTimeField',
    'apply_cpf_input_attrs',
    'apply_currency_input_attrs',
    'apply_date_input_attrs',
    'apply_integer_input_attrs',
    'apply_phone_input_attrs',
    'apply_text_input_attrs',
    'apply_time_input_attrs',
    'apply_widget_attrs',
    'normalize_date_value',
    'normalize_time_value',
    'parse_lenient_date_value',
]
