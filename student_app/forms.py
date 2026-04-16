from decimal import Decimal

from django import forms

from student_app.models import StudentExerciseMax


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
