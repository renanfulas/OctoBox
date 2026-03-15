"""
ARQUIVO: formularios das mutacoes operacionais.

POR QUE ELE EXISTE:
- valida entradas curtas das rotas operacionais antes que cheguem na camada de acao.

O QUE ESTE ARQUIVO FAZ:
1. restringe categorias validas de ocorrencia tecnica.
2. limita tamanho e formato da descricao enviada pelo coach.

PONTOS CRITICOS:
- estes formularios ficam na borda HTTP e devem impedir ruido antes da regra de negocio.
"""

from django import forms

from operations.models import BehaviorCategory
from shared_support.form_inputs import apply_text_input_attrs


class TechnicalBehaviorNoteForm(forms.Form):
    category = forms.ChoiceField(choices=BehaviorCategory.choices)
    description = forms.CharField(max_length=280)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_text_input_attrs(self.fields['description'], placeholder='Explique a ocorrencia tecnica em uma frase curta.', maxlength=280)


__all__ = ['TechnicalBehaviorNoteForm']