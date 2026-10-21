"""
ARQUIVO: board de aprovacao do WOD com o relogio de parede virando a meia-noite.

POR QUE ELE EXISTE:
- no CI de 2026-10-19 (order-dependence-check 137) a classe da board montou o
  setUpTestData as 23:59 e fez os requests as 00:01 em Sao Paulo; a aula "de hoje"
  virou "de ontem" e sumiu do filtro today_only.

O QUE ESTE ARQUIVO FAZ:
1. reroda os testes da board com o relogio de parede em 23:59 durante o
   setUpTestData e em 00:01 durante os testes.

PONTOS CRITICOS:
- passa porque WorkoutFlowBaseTestCase empilha o proprio relogio
  (WORKOUT_FLOW_FROZEN_NOW) por cima deste; sem ele, a virada reproduz a falha.
- relogio parado so em 23:59 ou so em 00:01 passa ate sem o relogio da base;
  o que quebra e a virada entre o setUpTestData e o request.
- importa o modulo da board, nao a classe: classe no namespace seria coletada de novo.
"""

from datetime import datetime

from django.utils import timezone
from freezegun import freeze_time

from tests import test_workout_approval_board as board_tests


class ApprovalBoardAcrossMidnightTests(board_tests.WorkoutApprovalBoardTests):
    wall_clock_at_setup = datetime(2026, 10, 18, 23, 59)
    wall_clock_at_tests = datetime(2026, 10, 19, 0, 1)

    @classmethod
    def setUpClass(cls):
        # Liga antes do relogio da base para desligar depois dele (pilha do freezegun).
        wall_clock = freeze_time(timezone.make_aware(cls.wall_clock_at_setup))
        frozen_wall_clock = wall_clock.start()
        cls.addClassCleanup(wall_clock.stop)
        super().setUpClass()
        frozen_wall_clock.move_to(timezone.make_aware(cls.wall_clock_at_tests))
