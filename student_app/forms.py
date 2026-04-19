from decimal import Decimal

from django import forms
from django.utils import timezone

from finance.models import MembershipPlan
from student_app.models import StudentExerciseMax
from students.models import Student


class WorkoutPrescriptionForm(forms.Form):
    exercise_slug = forms.ChoiceField(choices=())
    percentage = forms.DecimalField(min_value=Decimal('1'), max_value=Decimal('200'), decimal_places=2)

    def __init__(self, *args, student=None, **kwargs):
        super().__init__(*args, **kwargs)
        choices = [
            (record.exercise_slug, record.exercise_label)
            for record in StudentExerciseMax.objects.filter(student=student).order_by('exercise_label')
        ] if student is not None else []
        self.fields['exercise_slug'].choices = choices


class BaseStudentOnboardingForm(forms.Form):
    full_name = forms.CharField(label='Nome completo', max_length=150)
    phone = forms.CharField(label='WhatsApp', max_length=255)
    email = forms.EmailField(label='E-mail')
    birth_date = forms.DateField(
        label='Data de nascimento',
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
        input_formats=['%Y-%m-%d'],
    )
    selected_plan = forms.ModelChoiceField(
        label='Plano',
        required=False,
        queryset=MembershipPlan.objects.none(),
        empty_label='Escolho depois',
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['selected_plan'].queryset = MembershipPlan.objects.filter(active=True).order_by('price', 'name')
        self.fields['full_name'].widget.attrs.update({'placeholder': 'Ex.: Maria Souza'})
        self.fields['phone'].widget.attrs.update({'placeholder': 'Ex.: 5511999999999'})
        self.fields['email'].widget.attrs.update({'placeholder': 'voce@exemplo.com'})
        self.fields['birth_date'].widget.attrs.update({'max': timezone.localdate().isoformat()})

    def clean_email(self):
        return (self.cleaned_data.get('email') or '').strip().lower()

    def clean_phone(self):
        return (self.cleaned_data.get('phone') or '').strip()

    def clean_full_name(self):
        return (self.cleaned_data.get('full_name') or '').strip()


class MassInviteOnboardingForm(BaseStudentOnboardingForm):
    pass


class ImportedLeadOnboardingForm(BaseStudentOnboardingForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['full_name'].help_text = 'Ja puxamos o nome do lead. Ajuste so se precisar.'
        self.fields['phone'].help_text = 'Ja puxamos seu WhatsApp do box. Ajuste se estiver diferente.'


class StudentProfileEditForm(forms.ModelForm):
    email = forms.EmailField(label='E-mail', required=True)

    class Meta:
        model = Student
        fields = ['full_name', 'phone', 'email', 'birth_date']
        widgets = {
            'birth_date': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['birth_date'].input_formats = ['%Y-%m-%d']
        self.fields['full_name'].label = 'Nome completo'
        self.fields['phone'].label = 'WhatsApp'
        self.fields['full_name'].widget.attrs.update({'placeholder': 'Ex.: Maria Souza'})
        self.fields['phone'].widget.attrs.update({'placeholder': 'Ex.: 5511999999999'})
        self.fields['email'].widget.attrs.update({'placeholder': 'voce@exemplo.com'})

    def clean_email(self):
        return (self.cleaned_data.get('email') or '').strip().lower()
