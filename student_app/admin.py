from django.contrib import admin

from .models import StudentExerciseMax


@admin.register(StudentExerciseMax)
class StudentExerciseMaxAdmin(admin.ModelAdmin):
    list_display = ('student', 'exercise_label', 'one_rep_max_kg')
    search_fields = ('student__full_name', 'exercise_label', 'exercise_slug')
