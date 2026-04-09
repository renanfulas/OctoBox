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

from onboarding.attribution import ACQUISITION_CHANNEL_CHOICES
from shared_support.form_inputs import apply_text_input_attrs


INTAKE_ACTION_CHOICES = (
    ('move-to-conversation', 'Mover para Em conversa'),
    ('reject-intake', 'Rejeitar intake'),
)

SEMANTIC_STAGE_CHOICES = (
    ('', 'Todos os estagios'),
    ('new-leads', 'Leads'),
    ('lead-open', 'Em conversa'),
    ('resolved', 'Resolvido'),
)

SORT_CHOICES = (
    ('', 'Ordem padrao'),
    ('registration-oldest', 'Registro mais antigo'),
    ('registration-newest', 'Registro mais recente'),
)


class IntakeCenterFilterForm(forms.Form):
    query = forms.CharField(required=False, label='Buscar por nome, telefone ou e-mail')
    status = forms.ChoiceField(required=False, label='Status', choices=())
    source = forms.ChoiceField(required=False, label='Origem', choices=())
    sort = forms.ChoiceField(required=False, label='Ordenacao', choices=SORT_CHOICES)
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


from onboarding.model_definitions import StudentIntake


class IntakeQuickCreateForm(forms.ModelForm):
    acquisition_channel = forms.ChoiceField(
        required=False,
        label='Canal de captacao',
        choices=ACQUISITION_CHANNEL_CHOICES,
    )
    acquisition_detail = forms.CharField(
        required=False,
        label='Detalhe da origem',
        max_length=120,
    )

    class Meta:
        model = StudentIntake
        fields = ['full_name', 'phone', 'email', 'source']
        labels = {
            'full_name': 'Nome completo',
            'phone': 'WhatsApp',
            'email': 'E-mail',
            'source': 'Origem',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_text_input_attrs(self.fields['full_name'], placeholder='Nome completo')
        apply_text_input_attrs(self.fields['phone'], placeholder='WhatsApp principal (com DDD)')
        apply_text_input_attrs(self.fields['email'], placeholder='E-mail (opcional)')
        apply_text_input_attrs(self.fields['acquisition_detail'], placeholder='Ex.: indicacao do Joao, Google Maps, passou na frente')


class IntakeQueueActionForm(forms.Form):
    intake_id = forms.IntegerField()
    action = forms.ChoiceField(choices=INTAKE_ACTION_CHOICES)
    return_query = forms.CharField(required=False)


__all__ = [
    'INTAKE_ACTION_CHOICES',
    'IntakeCenterFilterForm',
    'IntakeQuickCreateForm',
    'IntakeQueueActionForm',
    'SEMANTIC_STAGE_CHOICES',
    'SORT_CHOICES',
]
