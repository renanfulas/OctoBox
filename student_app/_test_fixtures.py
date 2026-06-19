"""
ARQUIVO: fixtures compartilhadas dos testes do app do aluno.

POR QUE ELE EXISTE:
- As camadas de smoke e de integracao (test_smoke_routes.py,
  test_integration_backend.py) precisam do MESMO aluno onboarded + cookie
  de sessao assinado que o tests.py legado monta no setUp. Centralizar aqui
  evita drift entre os arquivos.

POR QUE O NOME COMECA COM '_':
- pytest coleta apenas `tests.py`, `test_*.py` e `*_tests.py` (ver pytest.ini)
  e o test runner do Django coleta `test*.py`. `_test_fixtures.py` nao casa
  com nenhum dos dois, entao e tratado como modulo utilitario importavel e
  nunca e coletado como teste.

PONTO CRITICO:
- O backend e schema-per-tenant (django-tenants). Estes objetos sao criados
  dentro do schema `box_test` pelo autouse `_tenant_schema_context` do
  conftest, por isso nao ha tenant_context explicito aqui.
"""

from __future__ import annotations

from student_identity.infrastructure.session import build_student_session_value
from student_identity.models import (
    StudentBoxMembership,
    StudentBoxMembershipStatus,
    StudentIdentity,
    StudentIdentityProvider,
    StudentIdentityStatus,
)
from students.models import Student
from shared_support.box_runtime import get_box_runtime_slug


STUDENT_SESSION_COOKIE = 'octobox_student_session'


def create_onboarded_student(
    *,
    full_name='Aluno Backend',
    phone='5511988887777',
    email='backend@example.com',
    provider_subject='provider-subject-backend',
    status=StudentBoxMembershipStatus.ACTIVE,
):
    """Cria Student + StudentIdentity ativa + StudentBoxMembership no box de teste.

    Replica o caminho feliz do setUp de StudentAppExperienceTests: um aluno
    que ja passou pelo onboarding e tem matricula ativa, pronto para navegar
    no app autenticado.
    """
    slug = get_box_runtime_slug()
    student = Student.objects.create(full_name=full_name, phone=phone, email=email)
    identity = StudentIdentity.objects.create(
        student_id=student.id,
        student_name=student.full_name,
        box_root_slug=slug,
        primary_box_root_slug=slug,
        provider=StudentIdentityProvider.GOOGLE,
        provider_subject=provider_subject,
        email=email,
        status=StudentIdentityStatus.ACTIVE,
    )
    StudentBoxMembership.objects.create(
        identity=identity,
        student_id=student.id,
        box_root_slug=slug,
        status=status,
    )
    return student, identity


def auth_cookie_value(identity):
    """Valor assinado do cookie de sessao do aluno para `identity`."""
    return build_student_session_value(
        identity_id=identity.id,
        box_root_slug=get_box_runtime_slug(),
    )
