"""
ARQUIVO: formulários de aplicação de template por dia.

POR QUE EXISTE SEPARADO DE forms.py:
- forms.py já tem 592 linhas; adicionar aqui evitaria crescimento desnecessário.
- escopo fechado: valida data alvo, template e modo de aplicação.
"""

from datetime import date

from django import forms

from operations.domain.wod_day_apply_rules import ApplyMode


class WodDayApplyForm(forms.Form):
    target_date = forms.DateField()
    template_id = forms.IntegerField(min_value=1)
    mode = forms.ChoiceField(
        choices=[
            ('replace_empty', 'Aplicar apenas em aulas sem WOD'),
            ('overwrite', 'Substituir todas as aulas do dia'),
        ],
        initial='replace_empty',
    )

    def clean_target_date(self) -> date:
        d = self.cleaned_data.get('target_date')
        if d is None:
            raise forms.ValidationError('Data inválida.')
        return d

    def clean_mode(self) -> ApplyMode:
        return self.cleaned_data.get('mode', 'replace_empty')


class WodDayApplyUndoForm(forms.Form):
    undo_token = forms.CharField(max_length=64)


__all__ = ['WodDayApplyForm', 'WodDayApplyUndoForm']
