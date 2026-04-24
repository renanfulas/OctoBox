"""
Executa a regressao explicita dos corredores do onboarding do aluno.

Por que existe:
- manter um comando unico para o gate de CI e para execucao local
- deixar visivel quais cenarios realmente seguram o verde da homologacao
"""

from __future__ import annotations

import subprocess
import sys


TESTS = [
    "student_identity/tests.py::StudentIdentityFlowTests::test_mass_box_invite_redirects_to_onboarding_wizard",
    "student_app/tests.py::StudentAppExperienceTests::test_mass_onboarding_creates_student_and_identity",
    "student_identity/tests.py::StudentIdentityFlowTests::test_imported_lead_invite_redirects_to_reduced_onboarding",
    "student_app/tests.py::StudentAppExperienceTests::test_imported_lead_onboarding_updates_student_and_records_funnel_events",
    "student_identity/tests.py::StudentIdentityFlowTests::test_registered_student_invite_redirects_directly_to_app_with_funnel_events",
    "student_identity/tests.py::StudentIdentityFlowTests::test_open_box_invite_redirects_student_to_membership_pending",
    "student_app/tests.py::StudentAppExperienceTests::test_student_profile_edit_creates_pending_request_without_direct_write",
]


def main() -> int:
    command = [sys.executable, "-m", "pytest", "-q", *TESTS]
    return subprocess.run(command, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
