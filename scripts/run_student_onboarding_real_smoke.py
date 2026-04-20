"""
Executa o smoke end-to-end real do onboarding do aluno.

Por que existe:
- fechar um comando unico para o corredor operacional mais importante do app do aluno
- validar o fluxo completo que o time roda mentalmente em homologacao
- reduzir a chance de confiar so em testes fragmentados por etapa

Fluxos protegidos:
1. staff cria convite individual -> aluno abre link -> OAuth -> cai em Grade
2. staff cria convite individual -> aluno abre link -> OAuth -> cai em WOD quando ha janela ativa
3. staff cria convite aberto -> aluno abre link -> OAuth -> cai em aguardando aprovacao -> staff aprova -> aluno entra
"""

from __future__ import annotations

import subprocess
import sys


TESTS = [
    "student_identity/tests.py::StudentIdentityFlowTests::test_smoke_staff_creates_individual_invite_and_student_reaches_home_in_grade_mode",
    "student_identity/tests.py::StudentIdentityFlowTests::test_smoke_student_oauth_reaches_home_in_wod_mode_when_attendance_window_is_active",
    "student_identity/tests.py::StudentIdentityFlowTests::test_smoke_open_box_invite_waits_for_approval_then_student_enters_home",
]


def main() -> int:
    command = [sys.executable, "-m", "pytest", "-q", *TESTS]
    return subprocess.run(command, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
