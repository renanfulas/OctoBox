"""
ARQUIVO: estado proprio do app do aluno.

POR QUE ELE EXISTE:
- guarda dados que pertencem a experiencia do aluno, como RM base por exercicio.
"""

from __future__ import annotations

from decimal import Decimal

from django.db import models

from model_support.base import TimeStampedModel
from students.models import Student


class StudentExerciseMax(TimeStampedModel):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='exercise_maxes')
    exercise_slug = models.SlugField(max_length=64)
    exercise_label = models.CharField(max_length=120)
    one_rep_max_kg = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['exercise_label']
        constraints = [
            models.UniqueConstraint(fields=['student', 'exercise_slug'], name='unique_student_exercise_max')
        ]

    def __str__(self):
        return f'{self.student.full_name} - {self.exercise_label}'
