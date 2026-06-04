"""
ARQUIVO: acoes de membership da central operacional de ativacao do aluno.

POR QUE ELE EXISTE:
- separa o corredor de membership da view monolitica da central operacional.

O QUE ESTE ARQUIVO FAZ:
1. aprova memberships pendentes.
2. troca e-mail ligado ao corredor de identidade do aluno.
3. suspende, reativa e revoga memberships.
4. realinha a identidade quando um membership ativo deixa de ser o principal.
"""

from __future__ import annotations

from datetime import timedelta

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.shortcuts import redirect
from django.utils import timezone

from access.roles import ROLE_RECEPTION
from auditing.models import AuditEvent
from shared_support.box_runtime import get_box_runtime_slug

from .models import StudentBoxMembership, StudentBoxMembershipStatus



def _update_student_email_in_tenant(*, membership, new_email: str) -> None:
    """Atualiza Student.email no schema tenant correto via schema_context.

    Sprint 2: membership.student.email = new_email + save() era cross-schema.
    Usa schema_context(box.schema_name) para acessar o Student no tenant certo.
    """
    student_id = membership.student_id
    if not student_id:
        return
    schema = membership.box.schema_name if membership.box_id else None
    try:
        from students.models import Student
        if schema:
            from django_tenants.utils import schema_context
            with schema_context(schema):
                Student.objects.filter(pk=student_id).update(email=new_email)
        else:
            Student.objects.filter(pk=student_id).update(email=new_email)
    except Exception:
        import logging
        logging.getLogger('student_identity.staff_membership').exception(
            '_update_student_email_in_tenant: falha ao atualizar email do student_id=%s', student_id
        )

class StudentInvitationMembershipActionsMixin:
    def _handle_approve_membership(self, request):
        denied_response = self._require_action_roles(
            request,
            allowed_roles=self.membership_approval_roles,
            denied_message='Aprovação de membership exige Recepção, Manager, Owner ou DEV.',
        )
        if denied_response is not None:
            return denied_response
        membership = (
            StudentBoxMembership.objects.select_related('identity')  # Sprint 2: sem 'student' (cross-schema)
            .filter(
                pk=request.POST.get('membership_id'),
                box_root_slug=get_box_runtime_slug(),
                status=StudentBoxMembershipStatus.PENDING_APPROVAL,
            )
            .first()
        )
        if membership is None:
            messages.error(request, 'O vínculo pendente não foi encontrado.')
            return redirect('student-invitation-operations')

        membership.mark_active()
        membership.approved_by = request.user
        membership.save(update_fields=['status', 'approved_at', 'approved_by', 'last_access_at', 'updated_at'])
        AuditEvent.objects.create(
            actor=request.user,
            actor_role=self._get_actor_role_slug(request),
            action='student_membership.approved',
            target_model='student_identity.StudentBoxMembership',
            target_id=str(membership.id),
            target_label=membership.identity.student_name,  # Sprint 2: denorm
            description=f'Membership aprovado no box {membership.box_root_slug}.',
            metadata={
                'student_id': membership.student_id,
                'identity_id': membership.identity_id,
                'box_root_slug': membership.box_root_slug,
            },
        )
        messages.success(request, f'Acesso aprovado para {membership.identity.student_name} no box {membership.box_root_slug}.')
        return redirect('student-invitation-operations')

    def _get_membership_for_management(self, request):
        return (
            StudentBoxMembership.objects.select_related('identity')  # Sprint 2: sem 'student' (cross-schema)
            .filter(
                pk=request.POST.get('membership_id'),
                box_root_slug=get_box_runtime_slug(),
            )
            .first()
        )

    def _find_fallback_active_membership(self, *, identity, excluded_membership_id: int):
        return (
            StudentBoxMembership.objects.filter(
                identity=identity,
                status=StudentBoxMembershipStatus.ACTIVE,
            )
            .exclude(pk=excluded_membership_id)
            .order_by('box_root_slug')
            .first()
        )

    def _realign_identity_after_membership_loss(self, *, identity, affected_membership):
        fallback_membership = self._find_fallback_active_membership(
            identity=identity,
            excluded_membership_id=affected_membership.id,
        )
        if fallback_membership is not None:
            identity.primary_box_root_slug = fallback_membership.box_root_slug
            identity.box_root_slug = fallback_membership.box_root_slug
            identity.save(update_fields=['primary_box_root_slug', 'box_root_slug', 'updated_at'])

    def _handle_change_email(self, request):
        denied_response = self._require_action_roles(
            request,
            allowed_roles=self.invite_operator_roles,
            denied_message='Troca de e-mail exige Recepção, Manager, Owner ou DEV.',
        )
        if denied_response is not None:
            return denied_response
        membership = self._get_membership_for_management(request)
        if membership is None:
            messages.error(request, 'O vínculo do aluno não foi encontrado para trocar o e-mail.')
            return redirect('student-invitation-operations')

        new_email = (request.POST.get('new_email') or '').strip().lower()
        change_reason = (request.POST.get('change_reason') or '').strip()
        if not new_email:
            messages.error(request, 'Informe um novo e-mail antes de salvar a troca.')
            return redirect('student-invitation-operations')
        try:
            validate_email(new_email)
        except ValidationError:
            messages.error(request, 'O novo e-mail informado não é válido.')
            return redirect('student-invitation-operations')

        identity = membership.identity
        if identity.email == new_email:
            messages.info(request, 'Esse aluno já está com esse e-mail registrado no app.')
            return redirect('student-invitation-operations')

        role_slug = self._get_actor_role_slug(request)
        if role_slug == ROLE_RECEPTION:
            reception_changes_in_window = AuditEvent.objects.filter(
                action='student_identity.email_changed',
                target_id=str(identity.id),
                actor_role=ROLE_RECEPTION,
                created_at__gte=timezone.now() - timedelta(days=30),
            ).count()
            if reception_changes_in_window >= 1:
                messages.error(
                    request,
                    'A segunda troca de e-mail no mesmo mês exige Manager ou Owner. Chame a liderança para confirmar esta alteração.',
                )
                return redirect('student-invitation-operations')

        old_email = identity.email
        identity.email = new_email
        identity.save(update_fields=['email', 'updated_at'])
        # Sprint 2: Student.email update requer schema_context (tenant->public direcao errada).
        # Aluno tem email tanto em StudentIdentity (login) quanto em Student (tenant).
        # Atualizar Student.email via schema_context do box correto.
        _update_student_email_in_tenant(membership=membership, new_email=new_email)
        AuditEvent.objects.create(
            actor=request.user,
            actor_role=role_slug,
            action='student_identity.email_changed',
            target_model='student_identity.StudentIdentity',
            target_id=str(identity.id),
            target_label=membership.identity.student_name,  # Sprint 2: denorm
            description=f'E-mail do aluno trocado de {old_email} para {new_email}.',
            metadata={
                'student_id': membership.student_id,
                'membership_id': membership.id,
                'box_root_slug': membership.box_root_slug,
                'old_email': old_email,
                'new_email': new_email,
                'reason': change_reason,
            },
        )
        messages.success(request, f'E-mail do aluno {membership.identity.student_name} atualizado para {new_email}.')
        return redirect('student-invitation-operations')

    def _handle_suspend_membership(self, request):
        denied_response = self._require_action_roles(
            request,
            allowed_roles=self.membership_lifecycle_roles,
            denied_message='Suspensão financeira exige Manager, Owner ou DEV.',
        )
        if denied_response is not None:
            return denied_response
        membership = self._get_membership_for_management(request)
        if membership is None:
            messages.error(request, 'O vínculo do aluno não foi encontrado para suspensão financeira.')
            return redirect('student-invitation-operations')
        if membership.status != StudentBoxMembershipStatus.ACTIVE:
            messages.info(request, 'Somente memberships ativos podem entrar em suspensão financeira.')
            return redirect('student-invitation-operations')

        membership.mark_suspended_financial()
        membership.save(update_fields=['status', 'updated_at'])
        self._realign_identity_after_membership_loss(identity=membership.identity, affected_membership=membership)
        AuditEvent.objects.create(
            actor=request.user,
            actor_role=self._get_actor_role_slug(request),
            action='student_membership.suspended_financial',
            target_model='student_identity.StudentBoxMembership',
            target_id=str(membership.id),
            target_label=membership.identity.student_name,  # Sprint 2: denorm
            description=f'Membership suspenso financeiramente no box {membership.box_root_slug}.',
            metadata={
                'student_id': membership.student_id,
                'identity_id': membership.identity_id,
                'box_root_slug': membership.box_root_slug,
            },
        )
        messages.success(request, f'Acesso suspenso por inadimplencia para {membership.identity.student_name}.')
        return redirect('student-invitation-operations')

    def _handle_reactivate_membership(self, request):
        denied_response = self._require_action_roles(
            request,
            allowed_roles=self.membership_lifecycle_roles,
            denied_message='Reativação exige Manager, Owner ou DEV.',
        )
        if denied_response is not None:
            return denied_response
        membership = self._get_membership_for_management(request)
        if membership is None:
            messages.error(request, 'O vínculo do aluno não foi encontrado para reativação.')
            return redirect('student-invitation-operations')
        if membership.status not in {
            StudentBoxMembershipStatus.SUSPENDED_FINANCIAL,
            StudentBoxMembershipStatus.REVOKED,
        }:
            messages.info(request, 'Somente memberships suspensos ou revogados podem ser reativados por aqui.')
            return redirect('student-invitation-operations')

        membership.mark_active()
        membership.approved_by = request.user
        membership.revoked_at = None
        membership.revoked_reason = ''
        membership.save(
            update_fields=[
                'status',
                'approved_at',
                'approved_by',
                'last_access_at',
                'revoked_at',
                'revoked_reason',
                'updated_at',
            ]
        )
        if not membership.identity.primary_box_root_slug:
            membership.identity.primary_box_root_slug = membership.box_root_slug
            membership.identity.box_root_slug = membership.box_root_slug
            membership.identity.save(update_fields=['primary_box_root_slug', 'box_root_slug', 'updated_at'])
        AuditEvent.objects.create(
            actor=request.user,
            actor_role=self._get_actor_role_slug(request),
            action='student_membership.reactivated',
            target_model='student_identity.StudentBoxMembership',
            target_id=str(membership.id),
            target_label=membership.identity.student_name,  # Sprint 2: denorm
            description=f'Membership reativado no box {membership.box_root_slug}.',
            metadata={
                'student_id': membership.student_id,
                'identity_id': membership.identity_id,
                'box_root_slug': membership.box_root_slug,
            },
        )
        messages.success(request, f'Acesso reativado para {membership.identity.student_name}.')
        return redirect('student-invitation-operations')

    def _handle_revoke_membership(self, request):
        denied_response = self._require_action_roles(
            request,
            allowed_roles=self.membership_lifecycle_roles,
            denied_message='Revogação exige Manager, Owner ou DEV.',
        )
        if denied_response is not None:
            return denied_response
        membership = self._get_membership_for_management(request)
        if membership is None:
            messages.error(request, 'O vínculo do aluno não foi encontrado para revogação.')
            return redirect('student-invitation-operations')
        if membership.status == StudentBoxMembershipStatus.REVOKED:
            messages.info(request, 'Esse membership já está revogado.')
            return redirect('student-invitation-operations')

        revoke_reason = (request.POST.get('revoke_reason') or '').strip() or 'Revogação operacional do box.'
        membership.mark_revoked(reason=revoke_reason)
        membership.save(update_fields=['status', 'revoked_at', 'revoked_reason', 'updated_at'])
        self._realign_identity_after_membership_loss(identity=membership.identity, affected_membership=membership)
        AuditEvent.objects.create(
            actor=request.user,
            actor_role=self._get_actor_role_slug(request),
            action='student_membership.revoked',
            target_model='student_identity.StudentBoxMembership',
            target_id=str(membership.id),
            target_label=membership.identity.student_name,  # Sprint 2: denorm
            description=f'Membership revogado no box {membership.box_root_slug}.',
            metadata={
                'student_id': membership.student_id,
                'identity_id': membership.identity_id,
                'box_root_slug': membership.box_root_slug,
                'reason': revoke_reason,
            },
        )
        messages.success(request, f'Acesso revogado para {membership.identity.student_name}.')
        return redirect('student-invitation-operations')
