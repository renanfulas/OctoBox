from datetime import datetime

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from freezegun import freeze_time

from access.roles import ROLE_COACH, ROLE_MANAGER, ROLE_OWNER
from operations.models import ClassSession
from students.models import Student


# Quarta-feira 10:00 no fuso local (TIME_ZONE), semana sem feriado.
# O corredor WOD le o relogio no request: filtro "so hoje" (timezone.localdate()),
# "aula em breve" (horas ate o inicio) e semana corrente do planner. Com o relogio
# real, a classe montada antes da meia-noite e testada depois (CI de 2026-10-19
# 00:00 em Sao Paulo) via a aula "de hoje" como "de ontem".
# Precisa ficar depois de 22/09/2026: a smart paste aceita no maximo a proxima
# segunda, e ha testes com semana fixa em 28/09/2026.
WORKOUT_FLOW_FROZEN_NOW = datetime(2026, 9, 30, 10, 0)


class WorkoutFlowBaseTestCase(TestCase):
    """Shared baseline for WOD corridor tests without hiding test intent."""

    @classmethod
    def setUpClass(cls):
        # Relogio da classe inteira (setUpTestData + testes) parte do mesmo instante.
        # tick=True mantem submitted_at/created_at distintos para as ordenacoes.
        # Nao usar @freeze_time na classe: ele amarra setUpClass a esta base e
        # quebra o setUpTestData das subclasses.
        clock = freeze_time(timezone.make_aware(WORKOUT_FLOW_FROZEN_NOW), tick=True)
        clock.start()
        cls.addClassCleanup(clock.stop)
        super().setUpClass()

    @classmethod
    def setUpTestData(cls):
        call_command('bootstrap_roles')
        user_model = get_user_model()

        cls.coach = user_model.objects.create_user(
            username='coach-wod',
            email='coach-wod@example.com',
            password='senha-forte-123',
        )
        cls.coach.groups.add(Group.objects.get(name=ROLE_COACH))

        cls.manager = user_model.objects.create_user(
            username='manager-wod',
            email='manager-wod@example.com',
            password='senha-forte-123',
        )
        cls.manager.groups.add(Group.objects.get(name=ROLE_MANAGER))

        cls.owner = user_model.objects.create_user(
            username='owner-wod',
            email='owner-wod@example.com',
            password='senha-forte-123',
        )
        cls.owner.groups.add(Group.objects.get(name=ROLE_OWNER))

        local_now = timezone.localtime()
        session_time = local_now.replace(hour=12, minute=0, second=0, microsecond=0)

        cls.session = ClassSession.objects.create(
            title='Cross 07h',
            coach=cls.coach,
            scheduled_at=session_time,
            duration_minutes=60,
            capacity=16,
        )

        cls.student_alpha = Student.objects.create(
            full_name='Aluno Alpha',
            phone='5511990000001',
            email='alpha@example.com',
        )
        cls.student_beta = Student.objects.create(
            full_name='Aluno Beta',
            phone='5511990000002',
            email='beta@example.com',
        )

    def setUp(self):
        cache.clear()
        self.client.force_login(self.coach)

    def login_as_coach(self):
        self.client.force_login(self.coach)

    def login_as_manager(self):
        self.client.force_login(self.manager)

    def login_as_owner(self):
        self.client.force_login(self.owner)
