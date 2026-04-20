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


class StudentInvitationMembershipActionsMixin:
    def _handle_approve_membership(self, request):
        denied_response = self._require_action_roles(
            request,
            allowed_roles=self.membership_approval_roles,
            denied_message='Aprovacao de membership exige Recepcao, Manager, Owner ou DEV.',
        )
        if denied_response is not None:
            return denied_response
        membership = (
            StudentBoxMembership.objects.select_related('student', 'identity')
            .filter(
                pk=request.POST.get('membership_id'),
                box_root_slug=get_box_runtime_slug(),
                status=StudentBoxMembershipStatus.PENDING_APPROVAL,
            )
            .first()
        )
        if membership is None:
            messages.error(request, 'O vinculo pendente nao foi encontrado.')
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
            target_label=membership.student.full_name,
            description=f'Membership aprovado no box {membership.box_root_slug}.',
            metadata={
                'student_id': membership.student_id,
                'identity_id': membership.identity_id,
                'box_root_slug': membership.box_root_slug,
            },
        )
        messages.success(request, f'Acesso aprovado para {membership.student.full_name} no box {membership.box_root_slug}.')
        return redirect('student-invitation-operations')

    def _get_membership_for_management(self, request):
        return (
            StudentBoxMembership.objects.select_related('student', 'identity')
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
            denied_message='Troca de e-mail exige Recepcao, Manager, Owner ou DEV.',
        )
        if denied_response is not None:
            return denied_response
        membership = self._get_membership_for_management(request)
        if membership is None:
            messages.error(request, 'O vinculo do aluno nao foi encontrado para trocar o e-mail.')
            return redirect('student-invitation-operations')

        new_email = (request.POST.get('new_email') or '').strip().lower()
        change_reason = (request.POST.get('change_reason') or '').strip()
        if not new_email:
            messages.error(request, 'Informe um novo e-mail antes de salvar a troca.')
            return redirect('student-invitation-operations')
        try:
            validate_email(new_email)
        except ValidationError:
            messages.error(request, 'O novo e-mail informado nao e valido.')
            return redirect('student-invitation-operations')

        identity = membership.identity
        if identity.email == new_email:
            messages.info(request, 'Esse aluno ja esta com esse e-mail registrado no app.')
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
                    'A segunda troca de e-mail no mesmo mes exige Manager ou Owner. Chame a lideranca para confirmar esta alteracao.',
                )
                return redirect('student-invitation-operations')

        old_email = identity.email
        identity.email = new_email
        identity.save(update_fields=['email', 'updated_at'])
        membership.student.email = new_email
        membership.student.save(update_fields=['email'])
        AuditEvent.objects.create(
            actor=request.user,
            actor_role=role_slug,
            action='student_identity.email_changed',
            target_model='student_identity.StudentIdentity',
            target_id=str(identity.id),
            target_label=membership.student.full_name,
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
        messages.success(request, f'E-mail do aluno {membership.student.full_name} atualizado para {new_email}.')
        return redirect('student-invitation-operations')

    def _handle_suspend_membership(self, request):
        denied_response = self._require_action_roles(
            request,
            allowed_roles=self.membership_lifecycle_roles,
            denied_message='Suspensao financeira exige Manager, Owner ou DEV.',
        )
        if denied_response is not None:
            return denied_response
        membership = self._get_membership_for_management(request)
        if membership is None:
            messages.error(request, 'O vinculo do aluno nao foi encontrado para suspensao financeira.')
            return redirect('student-invitation-operations')
        if membership.status != StudentBoxMembershipStatus.ACTIVE:
            messages.info(request, 'Somente memberships ativos podem entrar em suspensao financeira.')
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
            target_label=membership.student.full_name,
            description=f'Membership suspenso financeiramente no box {membership.box_root_slug}.',
            metadata={
                'student_id': membership.student_id,
                'identity_id': membership.identity_id,
                'box_root_slug': membership.box_root_slug,
            },
        )
        messages.success(request, f'Acesso suspenso por inadimplencia para {membership.student.full_name}.')
        return redirect('student-invitation-operations')

    def _handle_reactivate_membership(self, request):
        denied_response = self._require_action_roles(
            request,
            allowed_roles=self.membership_lifecycle_roles,
            denied_message='Reativacao exige Manager, Owner ou DEV.',
        )
        if denied_response is not None:
            return denied_response
        membership = self._get_membership_for_management(request)
        if membership is None:
            messages.error(request, 'O vinculo do aluno nao foi encontrado para reativacao.')
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
            target_label=membership.student.full_name,
            description=f'Membership reativado no box {membership.box_root_slug}.',
            metadata={
                'student_id': membership.student_id,
                'identity_id': membership.identity_id,
                'box_root_slug': membership.box_root_slug,
            },
        )
        messages.success(request, f'Acesso reativado para {membership.student.full_name}.')
        return redirect('student-invitation-operations')

    def _handle_revoke_membership(self, request):
        denied_response = self._require_action_roles(
            request,
            allowed_roles=self.membership_lifecycle_roles,
            denied_message='Revogacao exige Manager, Owner ou DEV.',
        )
        if denied_response is not None:
            return denied_response
        membership = self._get_membership_for_management(request)
        if membership is None:
            messages.error(request, 'O vinculo do aluno nao foi encontrado para revogacao.')
            return redirect('student-invitation-operations')
        if membership.status == StudentBoxMembershipStatus.REVOKED:
            messages.info(request, 'Esse membership ja esta revogado.')
            return redirect('student-invitation-operations')

        revoke_reason = (request.POST.get('revoke_reason') or '').strip() or 'Revogacao operacional do box.'
        membership.mark_revoked(reason=revoke_reason)
        membership.save(update_fields=['status', 'revoked_at', 'revoked_reason', 'updated_at'])
        self._realign_identity_after_membership_loss(identity=membership.identity, affected_membership=membership)
        AuditEvent.objects.create(
            actor=request.user,
            actor_role=self._get_actor_role_slug(request),
            action='student_membership.revoked',
            target_model='student_identity.StudentBoxMembership',
            target_id=str(membership.id),
            target_label=membership.student.full_name,
            description=f'Membership revogado no box {membership.box_root_slug}.',
            metadata={
                'student_id': membership.student_id,
                'identity_id': membership.identity_id,
                'box_root_slug': membership.box_root_slug,
                'reason': revoke_reason,
            },
        )
        messages.success(request, f'Acesso revogado para {membership.student.full_name}.')
        return redirect('student-invitation-operations')
