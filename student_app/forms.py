from datetime import date
from decimal import Decimal

from django import forms
from django.utils import timezone

from finance.models import MembershipPlan
from shared_support.crypto_fields import generate_blind_index
from shared_support.form_inputs import (
    LenientDateField,
    apply_date_input_attrs,
    apply_phone_input_attrs,
    apply_text_input_attrs,
)
from shared_support.phone_numbers import normalize_phone_number
from student_identity.models import StudentIdentity, StudentIdentityStatus
from student_app.models import StudentExerciseMax
from students.models import Student


MIN_STUDENT_BIRTH_DATE = date(1900, 1, 1)
MAX_STUDENT_BIRTH_YEAR = 2026
MIN_STUDENT_NAME_LENGTH = 5
MIN_STUDENT_PHONE_DIGITS = 10
MAX_STUDENT_PHONE_DIGITS = 11


def _student_phone_exists(*, normalized_phone: str, exclude_student_id: int | None = None) -> bool:
    phone_lookup_index = generate_blind_index(normalized_phone)
    queryset = Student.objects.all()
    if exclude_student_id is not None:
        queryset = queryset.exclude(pk=exclude_student_id)
    if phone_lookup_index:
        return queryset.filter(phone_lookup_index=phone_lookup_index).exists()
    return queryset.filter(phone=normalized_phone).exists()


def _student_identity_email_exists(*, email: str, box_root_slug: str, exclude_identity_id: int | None = None) -> bool:
    normalized_email = (email or '').strip().lower()
    if not normalized_email or not box_root_slug:
        return False
    queryset = StudentIdentity.objects.filter(
        email__iexact=normalized_email,
        box_root_slug=box_root_slug,
        status__in=[StudentIdentityStatus.PENDING, StudentIdentityStatus.ACTIVE],
    )
    if exclude_identity_id is not None:
        queryset = queryset.exclude(pk=exclude_identity_id)
    return queryset.exists()


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


class StudentExerciseMaxForm(forms.Form):
    exercise_label = forms.CharField(label='Movimento', max_length=120)
    one_rep_max_kg = forms.DecimalField(
        label='RM (kg)',
        min_value=Decimal('0.5'),
        max_value=Decimal('999'),
        decimal_places=2,
    )

    def clean_exercise_label(self):
        return (self.cleaned_data.get('exercise_label') or '').strip()


class StudentExerciseMaxUpdateForm(forms.Form):
    one_rep_max_kg = forms.DecimalField(
        label='Novo RM (kg)',
        min_value=Decimal('0.5'),
        max_value=Decimal('999'),
        decimal_places=2,
    )


class BaseStudentOnboardingForm(forms.Form):
    full_name = forms.CharField(label='Nome completo', max_length=150)
    phone = forms.CharField(label='WhatsApp', max_length=20)
    birth_date = LenientDateField(
        label='Data de nascimento',
        required=False,
        min_year=MIN_STUDENT_BIRTH_DATE.year,
        max_year=MAX_STUDENT_BIRTH_YEAR,
        widget=forms.TextInput(),
    )
    selected_plan = forms.ModelChoiceField(
        label='Plano',
        required=False,
        queryset=MembershipPlan.objects.none(),
        empty_label='Escolho depois',
    )

    def __init__(self, *args, student=None, identity=None, box_root_slug='', **kwargs):
        super().__init__(*args, **kwargs)
        self.student = student
        self.identity = identity
        self.box_root_slug = box_root_slug
        self.fields['selected_plan'].queryset = MembershipPlan.objects.filter(active=True).order_by('price', 'name')
        apply_text_input_attrs(
            self.fields['full_name'],
            placeholder='Ex.: Maria Souza',
            maxlength=150,
            autocomplete='name',
        )
        self.fields['full_name'].widget.attrs.update({
            'minlength': str(MIN_STUDENT_NAME_LENGTH),
            'autocapitalize': 'words',
        })
        self.fields['full_name'].help_text = 'Use o nome real que identifica voce no box.'
        apply_phone_input_attrs(self.fields['phone'], placeholder='Ex.: 5511999999999')
        self.fields['phone'].help_text = 'Use seu numero principal com DDD. Pode colar com espacos ou simbolos.'
        apply_date_input_attrs(
            self.fields['birth_date'],
            placeholder='dd/mm/aaaa',
            maxlength=10,
            pattern=r'\d{2}/\d{2}/\d{4}',
            min_year=MIN_STUDENT_BIRTH_DATE.year,
            max_year=MAX_STUDENT_BIRTH_YEAR,
        )
        self.fields['birth_date'].help_text = 'Use o formato dd/mm/aaaa. Ano permitido: 1900 a 2026.'
        self.fields['selected_plan'].widget.attrs.update({'autocomplete': 'off'})

    def clean_phone(self):
        raw_phone = (self.cleaned_data.get('phone') or '').strip()
        phone = normalize_phone_number(raw_phone)
        if not phone:
            raise forms.ValidationError('Informe um WhatsApp valido com DDD.')
        if len(phone) < MIN_STUDENT_PHONE_DIGITS or len(phone) > MAX_STUDENT_PHONE_DIGITS:
            raise forms.ValidationError('Informe um WhatsApp valido com DDD. Ex.: 5511999999999.')
        if _student_phone_exists(normalized_phone=phone, exclude_student_id=getattr(self.student, 'id', None)):
            raise forms.ValidationError('Ja existe um aluno cadastrado com este WhatsApp.')
        return phone

    def clean_full_name(self):
        full_name = ' '.join((self.cleaned_data.get('full_name') or '').split())
        if len(full_name) < MIN_STUDENT_NAME_LENGTH:
            raise forms.ValidationError('Informe um nome com pelo menos 5 caracteres.')
        if sum(character.isalpha() for character in full_name) < 2:
            raise forms.ValidationError('Informe um nome valido para continuar.')
        return full_name

    def clean_birth_date(self):
        birth_date = self.cleaned_data.get('birth_date')
        if birth_date is None:
            return birth_date
        if birth_date < MIN_STUDENT_BIRTH_DATE:
            raise forms.ValidationError('A data de nascimento precisa ser posterior a 01/01/1900.')
        if birth_date.year > MAX_STUDENT_BIRTH_YEAR:
            raise forms.ValidationError('O ano da data de nascimento precisa ficar entre 1900 e 2026.')
        return birth_date


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
