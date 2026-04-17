from __future__ import annotations

from django import forms

from student_identity.models import StudentInvitationType
from students.models import Student, StudentStatus


class StudentInvitationCreateForm(forms.Form):
    student = forms.ModelChoiceField(
        label='Aluno',
        queryset=Student.objects.none(),
        help_text='Somente alunos ativos entram no app do aluno nesta fase.',
    )
    invited_email = forms.EmailField(
        label='E-mail do convite',
        required=False,
        help_text='Se vazio, o sistema tenta usar o e-mail ja cadastrado no aluno.',
    )
    invite_type = forms.ChoiceField(
        label='Tipo de convite',
        choices=StudentInvitationType.choices,
        initial=StudentInvitationType.INDIVIDUAL,
        help_text='Convite individual libera o aluno ao fechar a identidade. Convite do box pede aprovacao depois.',
    )
    expires_in_days = forms.TypedChoiceField(
        label='Validade',
        coerce=int,
        choices=(
            (3, '3 dias'),
            (7, '7 dias'),
            (14, '14 dias'),
        ),
        initial=7,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['student'].queryset = Student.objects.filter(status=StudentStatus.ACTIVE).order_by('full_name')

    def clean_invited_email(self):
        return (self.cleaned_data.get('invited_email') or '').strip().lower()
