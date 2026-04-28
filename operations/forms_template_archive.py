"""
ARQUIVO: formulários de arquivamento de templates de WOD.

POR QUE EXISTE SEPARADO DE forms.py:
- escopo isolado; validação simples de confirmação de texto.
"""

from django import forms

ARCHIVE_ALL_CONFIRMATION_PHRASE = 'ARQUIVAR'


class TemplateArchiveAllForm(forms.Form):
    confirmation = forms.CharField(max_length=20)

    def clean_confirmation(self) -> str:
        value = (self.cleaned_data.get('confirmation') or '').strip().upper()
        if value != ARCHIVE_ALL_CONFIRMATION_PHRASE:
            raise forms.ValidationError(
                f'Digite "{ARCHIVE_ALL_CONFIRMATION_PHRASE}" para confirmar.'
            )
        return value


class TemplateRestoreForm(forms.Form):
    template_id = forms.IntegerField(min_value=1)


__all__ = [
    'ARCHIVE_ALL_CONFIRMATION_PHRASE',
    'TemplateArchiveAllForm',
    'TemplateRestoreForm',
]
