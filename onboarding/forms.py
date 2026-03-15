"""
ARQUIVO: formularios da Central de Intake.

POR QUE ELE EXISTE:
- Centraliza filtros e acoes operacionais da fila de entrada no proprio dominio de onboarding.

O QUE ESTE ARQUIVO FAZ:
1. Define o filtro da fila de intake.
2. Define o formulario de acoes de triagem, atribuicao e decisao.

PONTOS CRITICOS:
- Esses formularios ditam a linguagem da triagem; campos errados aqui contaminam o fluxo inteiro de entrada.
"""

from django import forms

from shared_support.form_inputs import apply_text_input_attrs


INTAKE_ACTION_CHOICES = (
    ('assign-to-me', 'Assumir caso'),
    ('clear-assignee', 'Remover responsavel'),
    ('start-review', 'Colocar em revisao'),
    ('mark-matched', 'Marcar como pronto para conversao'),
    ('approve-intake', 'Aprovar intake'),
    ('reject-intake', 'Rejeitar intake'),
)

SEMANTIC_STAGE_CHOICES = (
    ('', 'Todos os estagios'),
    ('lead-open', 'Lead aberto'),
    ('conversion-ready', 'Pronto para conversao'),
    ('resolved', 'Resolvido'),
)


class IntakeCenterFilterForm(forms.Form):
    query = forms.CharField(required=False, label='Buscar por nome, telefone ou e-mail')
    status = forms.ChoiceField(required=False, label='Status', choices=())
    source = forms.ChoiceField(required=False, label='Origem', choices=())
    semantic_stage = forms.ChoiceField(required=False, label='Leitura comercial', choices=SEMANTIC_STAGE_CHOICES)
    assignment = forms.ChoiceField(
        required=False,
        label='Atribuicao',
        choices=(
            ('', 'Todas'),
            ('assigned', 'Com responsavel'),
            ('unassigned', 'Sem responsavel'),
        ),
    )

    def __init__(self, *args, status_choices=(), source_choices=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['status'].choices = (('', 'Todos os status'), *status_choices)
        self.fields['source'].choices = (('', 'Todas as origens'), *source_choices)
        apply_text_input_attrs(self.fields['query'], placeholder='Ex.: Fernanda, 1199..., lead@box.com', maxlength=150)


class IntakeQueueActionForm(forms.Form):
    intake_id = forms.IntegerField()
    action = forms.ChoiceField(choices=INTAKE_ACTION_CHOICES)
    return_query = forms.CharField(required=False)


__all__ = [
    'INTAKE_ACTION_CHOICES',
    'IntakeCenterFilterForm',
    'IntakeQueueActionForm',
    'SEMANTIC_STAGE_CHOICES',
]