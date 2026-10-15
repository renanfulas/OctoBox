"""
ARQUIVO: ponte de acesso dos alunos ao PWA na simulacao.

POR QUE ELE EXISTE:
- O onboarding real do aluno so tem um caminho: OAuth Google. Sem provider
  configurado ninguem entra. Para conseguir exercitar as rotas do app do
  aluno por HTTP, esta ponte cria a MESMA identidade que o callback do
  Google criaria e usa /aluno/auth/dev-login/ (existe so em DEBUG).

PONTOS CRITICOS:
- Isto NAO mascara o achado: a dependencia de Google continua registrada
  no relatorio como bloqueio de produto.
"""
from __future__ import annotations

import django
django.setup()  # noqa: E402

from django_tenants.utils import schema_context  # noqa: E402

from control.models import Box  # noqa: E402


def build_student_tokens(schema_name: str, limit: int | None = None):
    """Cria identidade + membership de cada aluno e devolve [(student_id, nome, token)]."""
    from student_identity.models import (
        StudentIdentity, StudentBoxMembership,
        StudentIdentityProvider, StudentIdentityStatus, StudentBoxMembershipStatus,
    )
    from student_identity.infrastructure.session import build_student_session_value

    box = Box.objects.get(schema_name=schema_name)
    root_slug = box.slug
    out = []
    with schema_context(schema_name):
        from students.models import Student
        qs = Student.objects.all().order_by('id')
        if limit:
            qs = qs[:limit]
        students = list(qs)

    for st in students:
        identity, _ = StudentIdentity.objects.get_or_create(
            provider=StudentIdentityProvider.GOOGLE,
            provider_subject=f'sim-{schema_name}-{st.id}',
            defaults={
                'student_id': st.id,
                'student_name': st.full_name,
                'box': box,
                'box_root_slug': root_slug,
                'primary_box': box,
                'primary_box_root_slug': root_slug,
                'email': f'aluno{st.id:03d}@serranorte.test',
                'status': StudentIdentityStatus.ACTIVE,
            },
        )
        StudentBoxMembership.objects.get_or_create(
            identity=identity, box=box,
            defaults={
                'student_id': st.id,
                'box_root_slug': root_slug,
                'status': StudentBoxMembershipStatus.ACTIVE,
            },
        )
        token = build_student_session_value(
            identity_id=identity.id, box_root_slug=root_slug, box_id=box.id,
        )
        out.append((st.id, st.full_name, token))
    return out
