"""Testes de navegador para as duas jornadas que exibem o wizard do aluno."""

from datetime import date, timedelta
from urllib.parse import urlparse
from uuid import uuid4

import pytest
from django.conf import settings
from django.contrib.sessions.backends.cache import SessionStore
from django_tenants.utils import schema_context
from django.urls import reverse
from django.utils import timezone
from playwright.sync_api import Page, expect

from auditing.models import AuditEvent
from finance.models import Enrollment, EnrollmentStatus, MembershipPlan
from student_identity.infrastructure.session import build_student_session_value
from student_identity.models import (
    StudentAppInvitation,
    StudentBoxInviteLink,
    StudentBoxMembership,
    StudentBoxMembershipStatus,
    StudentIdentity,
    StudentIdentityProvider,
    StudentIdentityStatus,
    StudentOnboardingJourney,
)
from students.models import Student, StudentStatus


def _open_student_onboarding(page: Page, *, live_server, payload, identity_id=None, box_id=None):
    session = SessionStore()
    session['student_pending_onboarding'] = payload
    session.save()
    cookies = [{
        'name': settings.SESSION_COOKIE_NAME,
        'value': session.session_key,
        'url': live_server.url,
    }]
    if identity_id is not None:
        cookies.append({
            'name': 'octobox_student_session',
            'value': build_student_session_value(
                identity_id=identity_id,
                box_root_slug=payload['box_root_slug'],
                box_id=box_id,
            ),
            'domain': urlparse(live_server.url).hostname,
            'path': '/aluno/',
        })
    page.context.add_cookies(cookies)
    page.set_viewport_size({'width': 390, 'height': 844})
    page.goto(f'{live_server.url}{reverse("student-app-onboarding")}')


def _cleanup_onboarding_artifacts(
    *, test_tenant, provider_subject, journey, plan_id=None, invitation_id=None, invite_link_id=None,
):
    with schema_context('public'):
        identity = StudentIdentity.objects.filter(provider_subject=provider_subject).first()
        identity_id = identity.pk if identity is not None else None
        student_id = identity.student_id if identity is not None else None

    with schema_context(test_tenant.schema_name):
        onboarding_events = AuditEvent.objects.filter(action__startswith=f'student_onboarding.{journey}.')
        if identity_id is not None:
            onboarding_events.filter(metadata__identity_id=identity_id).delete()
        if invite_link_id is not None:
            onboarding_events.filter(metadata__box_invite_link_id=invite_link_id).delete()
        if invitation_id is not None:
            onboarding_events.filter(metadata__invitation_id=invitation_id).delete()
        if student_id is not None:
            Enrollment.objects.filter(student_id=student_id)._raw_delete('default')
            Student.objects.filter(pk=student_id)._raw_delete('default')
        if plan_id is not None:
            MembershipPlan.objects.filter(pk=plan_id)._raw_delete('default')

    with schema_context('public'):
        if identity_id is not None:
            StudentBoxMembership.objects.filter(identity_id=identity_id)._raw_delete('default')
            StudentIdentity.objects.filter(pk=identity_id)._raw_delete('default')
        if invitation_id is not None:
            StudentAppInvitation.objects.filter(pk=invitation_id)._raw_delete('default')
        if invite_link_id is not None:
            StudentBoxInviteLink.objects.filter(pk=invite_link_id)._raw_delete('default')


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_mass_student_onboarding_completes_in_mobile_browser(page: Page, live_server, test_tenant, request):
    """Confirma rótulos, opção comercial e conclusão visível da jornada em massa."""
    run_token = uuid4().hex
    phone = f'119{int(run_token[:8], 16) % 100_000_000:08d}'
    link = StudentBoxInviteLink.objects.create(
        box=test_tenant,
        box_root_slug=test_tenant.schema_name,
        expires_at=timezone.now() + timedelta(days=3),
        max_uses=200,
    )
    plan = MembershipPlan.objects.create(
        name='Plano Bronze E2E',
        price='159.90',
        billing_cycle='monthly',
        sessions_per_week=3,
        active=True,
    )
    payload = {
        'journey': StudentOnboardingJourney.MASS_BOX_INVITE,
        'box_root_slug': test_tenant.schema_name,
        'box_id': test_tenant.id,
        'provider': StudentIdentityProvider.GOOGLE,
        'provider_subject': f'e2e-mass-onboarding-{run_token}',
        'email': f'e2e-mass-{run_token}@example.test',
        'box_invite_link_id': link.id,
    }
    request.addfinalizer(lambda: _cleanup_onboarding_artifacts(
        test_tenant=test_tenant,
        provider_subject=payload['provider_subject'],
        journey=payload['journey'],
        plan_id=plan.pk,
        invite_link_id=link.pk,
    ))

    _open_student_onboarding(page, live_server=live_server, payload=payload)

    expect(page.get_by_role('heading', name='Complete seu cadastro no app')).to_be_visible()
    expect(page.get_by_text('Plano (opcional)')).to_be_visible()
    expect(page.locator('#id_selected_plan')).to_contain_text('R$ 159,90 · mensal · 3x por semana')
    expect(page.get_by_text('Nenhum pagamento é feito neste passo')).to_be_visible()
    expect(page.get_by_role('button', name='Concluir cadastro')).to_be_visible()
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')

    page.locator('#id_full_name').fill(f'Aluna E2E {run_token[:8]}')
    page.locator('#id_phone').fill(f'55{phone}')
    future_birth_date = (timezone.localdate() + timedelta(days=30)).strftime('%d/%m/%Y')
    page.locator('#id_birth_date').fill(future_birth_date)
    page.locator('#id_selected_plan').select_option(str(plan.pk))
    page.get_by_role('button', name='Concluir cadastro').click()
    expect(page.get_by_text('A data de nascimento não pode ser futura.')).to_be_visible()
    assert reverse('student-app-onboarding') in page.url

    page.locator('#id_birth_date').fill('02/01/2000')
    page.get_by_role('button', name='Concluir cadastro').click()
    page.wait_for_load_state('networkidle', timeout=15_000)
    assert reverse('student-app-home') in page.url, f'URL após concluir: {page.url}; tela: {page.locator("body").inner_text()}'
    created_identity = StudentIdentity.objects.get(provider_subject=payload['provider_subject'])
    student = Student.objects.get(pk=created_identity.student_id)
    assert student.phone == phone
    enrollment = Enrollment.objects.get(student=student, plan=plan)
    assert enrollment.status == EnrollmentStatus.PENDING


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_imported_lead_onboarding_preserves_existing_birth_date_in_browser(page: Page, live_server, test_tenant, request):
    """Permite revisar o lead no browser sem apagar nascimento ao deixar o campo vazio."""
    run_token = uuid4().hex
    student = Student.objects.create(
        full_name=f'Lead E2E {run_token[:8]}',
        phone=f'119{int(run_token[:8], 16) % 100_000_000:08d}',
        email='',
        birth_date=date(1996, 4, 3),
        status=StudentStatus.LEAD,
    )
    identity = StudentIdentity.objects.create(
        student_id=student.id,
        student_name=student.full_name,
        box=test_tenant,
        box_root_slug=test_tenant.schema_name,
        primary_box_root_slug=test_tenant.schema_name,
        provider=StudentIdentityProvider.GOOGLE,
        provider_subject=f'e2e-imported-onboarding-{run_token}',
        email=f'e2e-imported-{run_token}@example.test',
        status=StudentIdentityStatus.ACTIVE,
    )
    StudentBoxMembership.objects.create(
        identity=identity,
        student_id=student.id,
        box=test_tenant,
        box_root_slug=test_tenant.schema_name,
        status=StudentBoxMembershipStatus.ACTIVE,
    )
    invitation = StudentAppInvitation.objects.create(
        student_id=student.id,
        student_name=student.full_name,
        box=test_tenant,
        box_root_slug=test_tenant.schema_name,
        invited_email=identity.email,
        onboarding_journey=StudentOnboardingJourney.IMPORTED_LEAD_INVITE,
        expires_at=timezone.now() + timedelta(days=3),
    )
    payload = {
        'journey': StudentOnboardingJourney.IMPORTED_LEAD_INVITE,
        'box_root_slug': test_tenant.schema_name,
        'box_id': test_tenant.id,
        'student_id': student.id,
        'identity_id': identity.id,
        'invitation_id': invitation.id,
        'email': identity.email,
    }
    request.addfinalizer(lambda: _cleanup_onboarding_artifacts(
        test_tenant=test_tenant,
        provider_subject=identity.provider_subject,
        journey=payload['journey'],
        invitation_id=invitation.pk,
    ))

    _open_student_onboarding(
        page,
        live_server=live_server,
        payload=payload,
        identity_id=identity.id,
        box_id=test_tenant.id,
    )

    expect(page.get_by_role('heading', name='Revise seus dados para entrar no app')).to_be_visible()
    expect(page.get_by_role('button', name='Confirmar dados e entrar')).to_be_visible()
    expect(page.locator('#id_birth_date')).to_have_value('03/04/1996')
    expect(page.get_by_text('Se deixar em branco, ela será mantida')).to_be_visible()

    page.locator('#id_birth_date').fill('')
    page.get_by_role('button', name='Confirmar dados e entrar').click()
    page.wait_for_load_state('networkidle', timeout=15_000)
    assert reverse('student-app-home') in page.url, f'URL após revisar: {page.url}; tela: {page.locator("body").inner_text()}'
    student.refresh_from_db()
    assert student.birth_date == date(1996, 4, 3)
