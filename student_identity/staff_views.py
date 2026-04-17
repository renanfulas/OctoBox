from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.views.generic import TemplateView

from access.permissions import RoleRequiredMixin
from access.roles import ROLE_DEV, ROLE_MANAGER, ROLE_OWNER, ROLE_RECEPTION, get_user_role
from auditing.models import AuditEvent
from shared_support.box_runtime import get_box_runtime_slug
from shared_support.page_payloads import attach_page_payload
from .application.commands import CreateStudentInvitationCommand
from .application.use_cases import CreateStudentInvitation
from .delivery_audit import record_student_invitation_whatsapp_handoff
from .delivery_gateways import StudentEmailDeliveryError
from .forms import StudentInvitationCreateForm
from .infrastructure.repositories import DjangoStudentIdentityRepository
from .models import (
    StudentAppInvitation,
    StudentBoxMembership,
    StudentBoxMembershipStatus,
    StudentInvitationDeliveryStatus,
    StudentInvitationType,
)
from .notifications import build_invitation_whatsapp_url, send_invitation_email
from .presentation import build_student_invitation_operations_page
from .security import check_student_flow_rate_limit, maybe_emit_student_anomaly_alert


class StudentInvitationOperationsView(LoginRequiredMixin, RoleRequiredMixin, TemplateView):
    allowed_roles = (ROLE_OWNER, ROLE_DEV, ROLE_MANAGER, ROLE_RECEPTION)
    template_name = 'student_identity/operations_invites.html'

    def _track_invite_creation_anomalies(self, request, *, invitation: StudentAppInvitation):
        actor_window_seconds = max(
            60,
            int(getattr(settings, 'STUDENT_INVITE_CREATION_ACTOR_ALERT_WINDOW_SECONDS', 900)),
        )
        actor_threshold = max(
            1,
            int(getattr(settings, 'STUDENT_INVITE_CREATION_ACTOR_ALERT_THRESHOLD', 12)),
        )
        actor_allowed, _ = check_student_flow_rate_limit(
            scope='student-invite-creation-actor-alert',
            token=f'actor:{request.user.id}',
            limit=actor_threshold,
            window_seconds=actor_window_seconds,
        )
        if not actor_allowed:
            maybe_emit_student_anomaly_alert(
                scope='student-invite-creation-actor',
                actor=request.user,
                actor_role=self._get_actor_role_slug(request),
                target_label=str(request.user.id),
                description='Volume suspeito de criacao de invites concentrado no mesmo ator.',
                metadata={
                    'box_root_slug': invitation.box_root_slug,
                    'invite_type': invitation.invite_type,
                    'student_id': invitation.student_id,
                },
                dedupe_window_seconds=actor_window_seconds,
            )

        box_window_seconds = max(
            60,
            int(getattr(settings, 'STUDENT_INVITE_CREATION_BOX_ALERT_WINDOW_SECONDS', 900)),
        )
        box_threshold = max(
            1,
            int(getattr(settings, 'STUDENT_INVITE_CREATION_BOX_ALERT_THRESHOLD', 20)),
        )
        box_allowed, _ = check_student_flow_rate_limit(
            scope='student-invite-creation-box-alert',
            token=f'box:{invitation.box_root_slug}',
            limit=box_threshold,
            window_seconds=box_window_seconds,
        )
        if not box_allowed:
            maybe_emit_student_anomaly_alert(
                scope='student-invite-creation-box',
                actor=request.user,
                actor_role=self._get_actor_role_slug(request),
                target_label=invitation.box_root_slug,
                description='Volume suspeito de criacao de invites concentrado no mesmo box.',
                metadata={
                    'actor_id': request.user.id,
                    'invite_type': invitation.invite_type,
                    'student_id': invitation.student_id,
                },
                dedupe_window_seconds=box_window_seconds,
            )

    def _get_actor_role_slug(self, request) -> str:
        return getattr(get_user_role(request.user), 'slug', '')

    def _require_action_roles(self, request, *, allowed_roles: tuple[str, ...], denied_message: str):
        if self._get_actor_role_slug(request) not in allowed_roles:
            messages.error(request, denied_message)
            return redirect('student-invitation-operations')
        return None

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action', 'create-invite').strip()
        if action == 'send-email':
            return self._handle_send_email(request)
        if action == 'open-whatsapp':
            return self._handle_open_whatsapp(request)
        if action == 'approve-membership':
            return self._handle_approve_membership(request)
        if action == 'change-email':
            return self._handle_change_email(request)
        if action == 'suspend-membership':
            return self._handle_suspend_membership(request)
        if action == 'reactivate-membership':
            return self._handle_reactivate_membership(request)
        if action == 'revoke-membership':
            return self._handle_revoke_membership(request)

        form = StudentInvitationCreateForm(request.POST)
        if form.is_valid():
            command = CreateStudentInvitationCommand(
                student_id=form.cleaned_data['student'].id,
                invited_email=form.cleaned_data['invited_email'],
                box_root_slug=get_box_runtime_slug(),
                invite_type=form.cleaned_data['invite_type'],
                expires_in_days=form.cleaned_data['expires_in_days'],
                actor_id=request.user.id,
            )
            result = CreateStudentInvitation(DjangoStudentIdentityRepository()).execute(command)
            if result.success and result.invitation is not None:
                invite_url = request.build_absolute_uri(
                    reverse('student-identity-invite', kwargs={'token': result.invitation.token})
                )
                AuditEvent.objects.create(
                    actor=request.user,
                    actor_role=self._get_actor_role_slug(request),
                    action='student_invitation.created',
                    target_model='student_identity.StudentAppInvitation',
                    target_id=str(result.invitation.id),
                    target_label=result.invitation.student_name,
                    description=f'Convite {result.invitation.invite_type} criado para o box {get_box_runtime_slug()}.',
                    metadata={
                        'student_id': result.invitation.student_id,
                        'box_root_slug': result.invitation.box_root_slug,
                        'invite_type': result.invitation.invite_type,
                        'invited_email': result.invitation.invited_email,
                    },
                )
                self._track_invite_creation_anomalies(request, invitation=result.invitation)
                messages.success(
                    request,
                    f"Convite pronto para {result.invitation.student_name}. Link gerado: {invite_url}",
                )
                return redirect('student-invitation-operations')

            if result.failure_reason == 'open-box-rate-limit-exceeded':
                AuditEvent.objects.create(
                    actor=request.user,
                    actor_role=self._get_actor_role_slug(request),
                    action='student_invitation.rate_limit_blocked',
                    target_model='student_identity.StudentAppInvitation',
                    target_label=form.cleaned_data['student'].full_name,
                    description='Tentativa bloqueada por rate limit de invite aberto do box.',
                    metadata={
                        'student_id': form.cleaned_data['student'].id,
                        'box_root_slug': get_box_runtime_slug(),
                        'invite_type': form.cleaned_data['invite_type'],
                    },
                )
            messages.error(request, self._map_failure_reason(result.failure_reason))
        return self.render_to_response(self.get_context_data(form=form))

    def _handle_approve_membership(self, request):
        denied_response = self._require_action_roles(
            request,
            allowed_roles=(ROLE_RECEPTION, ROLE_MANAGER, ROLE_OWNER, ROLE_DEV),
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
            allowed_roles=(ROLE_RECEPTION, ROLE_MANAGER, ROLE_OWNER, ROLE_DEV),
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
            allowed_roles=(ROLE_MANAGER, ROLE_OWNER, ROLE_DEV),
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
            allowed_roles=(ROLE_MANAGER, ROLE_OWNER, ROLE_DEV),
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
            allowed_roles=(ROLE_MANAGER, ROLE_OWNER, ROLE_DEV),
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

    def _handle_send_email(self, request):
        invitation = (
            StudentAppInvitation.objects.select_related('student')
            .filter(pk=request.POST.get('invitation_id'), box_root_slug=get_box_runtime_slug())
            .first()
        )
        if invitation is None:
            messages.error(request, 'O convite escolhido nao foi encontrado.')
            return redirect('student-invitation-operations')
        if invitation.accepted_at:
            messages.info(request, 'Esse convite ja foi aceito pelo aluno.')
            return redirect('student-invitation-operations')
        if invitation.is_expired:
            messages.error(request, 'Esse convite expirou. Gere um novo antes de enviar.')
            return redirect('student-invitation-operations')
        if not invitation.invited_email:
            messages.error(request, 'Esse convite nao possui e-mail de destino.')
            return redirect('student-invitation-operations')

        invite_url = request.build_absolute_uri(
            reverse('student-identity-invite', kwargs={'token': invitation.token})
        )
        try:
            result = send_invitation_email(invitation=invitation, invite_url=invite_url, actor=request.user)
        except StudentEmailDeliveryError:
            messages.error(request, 'Nao foi possivel enviar o e-mail agora. Revise a configuracao do provedor transacional.')
            return redirect('student-invitation-operations')

        messages.success(
            request,
            f'E-mail de convite enviado para {invitation.invited_email} via {result.provider}.',
        )
        return redirect('student-invitation-operations')

    def _handle_open_whatsapp(self, request):
        invitation = (
            StudentAppInvitation.objects.select_related('student')
            .filter(pk=request.POST.get('invitation_id'), box_root_slug=get_box_runtime_slug())
            .first()
        )
        if invitation is None:
            messages.error(request, 'O convite escolhido nao foi encontrado.')
            return redirect('student-invitation-operations')
        if invitation.accepted_at:
            messages.info(request, 'Esse convite ja foi aceito pelo aluno.')
            return redirect('student-invitation-operations')
        if invitation.is_expired:
            messages.error(request, 'Esse convite expirou. Gere um novo antes de enviar mensagem.')
            return redirect('student-invitation-operations')

        invite_url = request.build_absolute_uri(
            reverse('student-identity-invite', kwargs={'token': invitation.token})
        )
        whatsapp_url = build_invitation_whatsapp_url(invitation=invitation, invite_url=invite_url)
        if not whatsapp_url:
            messages.error(request, 'Esse aluno nao possui telefone valido para abrir o WhatsApp.')
            return redirect('student-invitation-operations')

        record_student_invitation_whatsapp_handoff(
            invitation=invitation,
            actor=request.user,
            recipient=invitation.student.phone,
            metadata={'invite_url': invite_url},
        )
        return redirect(whatsapp_url)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = kwargs.get('form') or StudentInvitationCreateForm()
        recent_invites = []
        stalled_invites = []
        managed_memberships = []
        box_root_slug = get_box_runtime_slug()
        open_box_window_hours = max(1, int(getattr(settings, 'STUDENT_OPEN_BOX_INVITE_WINDOW_HOURS', 24)))
        open_box_limit_per_window = max(1, int(getattr(settings, 'STUDENT_OPEN_BOX_INVITE_LIMIT_PER_WINDOW', 25)))
        open_box_window_start = timezone.now() - timedelta(hours=open_box_window_hours)
        pending_memberships = [
            {
                'id': membership.id,
                'student_name': membership.student.full_name,
                'box_root_slug': membership.box_root_slug,
                'created_at': membership.created_at,
                'invite_type_label': (
                    membership.created_from_invite.get_invite_type_display()
                    if membership.created_from_invite_id else 'Sem convite'
                ),
                'invited_email': (
                    membership.created_from_invite.invited_email
                    if membership.created_from_invite_id else membership.identity.email
                ),
            }
            for membership in (
                StudentBoxMembership.objects.select_related('student', 'identity', 'created_from_invite')
                .filter(
                    box_root_slug=box_root_slug,
                    status=StudentBoxMembershipStatus.PENDING_APPROVAL,
                )
                .order_by('created_at')
            )
        ]
        for membership in (
            StudentBoxMembership.objects.select_related('student', 'identity', 'created_from_invite')
            .filter(box_root_slug=box_root_slug)
            .exclude(status=StudentBoxMembershipStatus.INACTIVE)
            .order_by('student__full_name', 'box_root_slug')
        ):
            managed_memberships.append(
                {
                    'id': membership.id,
                    'student_name': membership.student.full_name,
                    'student_email': membership.student.email,
                    'identity_email': membership.identity.email,
                    'identity_id': membership.identity_id,
                    'box_root_slug': membership.box_root_slug,
                    'status': membership.status,
                    'status_label': membership.get_status_display(),
                    'status_tone': self._build_membership_status_tone(membership.status),
                    'invite_type_label': (
                        membership.created_from_invite.get_invite_type_display()
                        if membership.created_from_invite_id else 'Sem convite'
                    ),
                    'is_primary': membership.box_root_slug == membership.identity.primary_box_root_slug,
                    'can_suspend_financial': membership.status == StudentBoxMembershipStatus.ACTIVE,
                    'can_reactivate': membership.status in {
                        StudentBoxMembershipStatus.SUSPENDED_FINANCIAL,
                        StudentBoxMembershipStatus.REVOKED,
                    },
                    'can_revoke': membership.status in {
                        StudentBoxMembershipStatus.ACTIVE,
                        StudentBoxMembershipStatus.SUSPENDED_FINANCIAL,
                        StudentBoxMembershipStatus.PENDING_APPROVAL,
                    },
                    'can_change_email': membership.status != StudentBoxMembershipStatus.REVOKED,
                }
            )
        for invitation in (
            StudentAppInvitation.objects.select_related('student', 'created_by')
            .prefetch_related('deliveries')
            .filter(box_root_slug=box_root_slug)
            .order_by('-created_at')[:12]
        ):
            last_email_delivery = next(
                (delivery for delivery in invitation.deliveries.all() if delivery.channel == 'email'),
                None,
            )
            last_whatsapp_delivery = next(
                (delivery for delivery in invitation.deliveries.all() if delivery.channel == 'whatsapp'),
                None,
            )
            recent_invites.append(
                {
                    'id': invitation.id,
                    'student_name': invitation.student.full_name,
                    'invite_type_label': invitation.get_invite_type_display(),
                    'invited_email': invitation.invited_email,
                    'status_label': self._build_status_label(invitation),
                    'status_tone': self._build_status_tone(invitation),
                    'expires_at': invitation.expires_at,
                    'accepted_at': invitation.accepted_at,
                    'created_by_name': (
                        invitation.created_by.get_full_name().strip() or invitation.created_by.username
                    ) if invitation.created_by else '',
                    'invite_url': self.request.build_absolute_uri(reverse('student-identity-invite', kwargs={'token': invitation.token})),
                    'can_send_email': False,
                    'can_open_whatsapp': False,
                    'last_email_delivery_label': self._build_last_email_delivery_label(last_email_delivery),
                    'last_email_delivery_status_label': self._build_last_email_delivery_status_label(last_email_delivery),
                    'last_email_delivery_status_tone': self._build_last_email_delivery_status_tone(last_email_delivery),
                    'last_whatsapp_delivery_label': self._build_last_whatsapp_delivery_label(last_whatsapp_delivery),
                    'last_whatsapp_delivery_status_label': self._build_last_whatsapp_delivery_status_label(last_whatsapp_delivery),
                    'last_whatsapp_delivery_status_tone': self._build_last_whatsapp_delivery_status_tone(last_whatsapp_delivery),
                    'email_action_recommendation_label': self._build_email_action_recommendation_label(
                        invitation=invitation,
                        delivery=last_email_delivery,
                    ),
                    'email_action_recommendation_tone': self._build_email_action_recommendation_tone(
                        invitation=invitation,
                        delivery=last_email_delivery,
                    ),
                }
            )
            recent_invites[-1]['whatsapp_url'] = build_invitation_whatsapp_url(
                invitation=invitation,
                invite_url=recent_invites[-1]['invite_url'],
            )
            recent_invites[-1]['can_open_whatsapp'] = bool(recent_invites[-1]['whatsapp_url'])
            recent_invites[-1]['can_send_email'] = self._can_send_email(
                invitation=invitation,
                delivery=last_email_delivery,
            )
            if self._is_stalled_invitation(
                invitation=invitation,
                email_delivery=last_email_delivery,
                whatsapp_delivery=last_whatsapp_delivery,
            ):
                stalled_since = (
                    getattr(last_email_delivery, 'failed_at', None)
                    or getattr(last_email_delivery, 'sent_at', None)
                    or invitation.created_at
                )
                stalled_invites.append(
                    {
                        'student_name': invitation.student.full_name,
                        'email_status_label': self._build_last_email_delivery_status_label(last_email_delivery),
                        'reason_label': self._build_stalled_reason_label(last_email_delivery),
                        'whatsapp_action_label': 'Enviar mensagem',
                        'invitation_id': invitation.id,
                        'priority_label': self._build_stalled_priority_label(last_email_delivery),
                        'priority_tone': self._build_stalled_priority_tone(last_email_delivery),
                        'stalled_since_label': self._build_stalled_since_label(stalled_since),
                        'sort_key': (
                            self._build_stalled_priority_rank(last_email_delivery),
                            stalled_since,
                        ),
                    }
                )
        stalled_invites.sort(key=lambda item: (item['sort_key'][0], item['sort_key'][1]))
        for item in stalled_invites:
            item.pop('sort_key', None)

        open_box_invites_in_window = StudentAppInvitation.objects.filter(
            box_root_slug=box_root_slug,
            invite_type=StudentInvitationType.OPEN_BOX,
            created_at__gte=open_box_window_start,
        ).count()
        accepted_invites_last_7d = StudentAppInvitation.objects.filter(
            box_root_slug=box_root_slug,
            accepted_at__isnull=False,
            accepted_at__gte=timezone.now() - timedelta(days=7),
        ).count()
        recent_invites_last_24h = StudentAppInvitation.objects.filter(
            box_root_slug=box_root_slug,
            created_at__gte=timezone.now() - timedelta(hours=24),
        ).count()
        observability_cards = [
            {
                'eyebrow': 'Janela de invite aberto',
                'value': f'{open_box_invites_in_window}/{open_box_limit_per_window}',
                'detail': f'Convites abertos emitidos nas ultimas {open_box_window_hours}h.',
                'tone': 'danger' if open_box_invites_in_window >= open_box_limit_per_window else 'attention' if open_box_invites_in_window >= max(1, int(open_box_limit_per_window * 0.7)) else 'ok',
            },
            {
                'eyebrow': 'Aprovacoes pendentes',
                'value': str(len(pending_memberships)),
                'detail': 'Alunos que ja fecharam identidade e esperam liberacao do box.',
                'tone': 'attention' if pending_memberships else 'ok',
            },
            {
                'eyebrow': 'Convites aceitos',
                'value': str(accepted_invites_last_7d),
                'detail': 'Entradas concluidas nos ultimos 7 dias.',
                'tone': 'ok',
            },
            {
                'eyebrow': 'Fila quente',
                'value': str(len(stalled_invites)),
                'detail': 'Convites travados que precisam de um corredor alternativo.',
                'tone': 'danger' if stalled_invites else 'ok',
            },
            {
                'eyebrow': 'Pulso de 24h',
                'value': str(recent_invites_last_24h),
                'detail': 'Todos os convites emitidos neste box nas ultimas 24h.',
                'tone': 'attention' if recent_invites_last_24h >= open_box_limit_per_window else 'ok',
            },
        ]
        observability_alerts = []
        if open_box_invites_in_window >= open_box_limit_per_window:
            observability_alerts.append(
                f'O limite tecnico de convites abertos por {open_box_window_hours}h foi alcancado. Use invites individuais ou aguarde a janela respirar.'
            )
        elif open_box_invites_in_window >= max(1, int(open_box_limit_per_window * 0.7)):
            observability_alerts.append(
                f'O box ja consumiu boa parte da janela de convites abertos ({open_box_invites_in_window}/{open_box_limit_per_window}).'
            )
        if len(stalled_invites) >= 3:
            observability_alerts.append(
                'A fila quente ja tem 3 ou mais convites travados. Vale revisar e-mail ruim, bounce e handoff via WhatsApp.'
            )
        if len(pending_memberships) >= 5:
            observability_alerts.append(
                'Ha uma fila grande de memberships aguardando aprovacao. Isso pode virar gargalo operacional e parecer app quebrado para o aluno.'
            )

        page_payload = build_student_invitation_operations_page(
            current_box_slug=box_root_slug,
            recent_invites=recent_invites,
            stalled_invites=stalled_invites,
            pending_memberships=pending_memberships,
            managed_memberships=managed_memberships,
            observability_cards=observability_cards,
            observability_alerts=observability_alerts,
        )
        attach_page_payload(
            context,
            payload_key='student_invitation_operations_page',
            payload=page_payload,
        )
        context['form'] = form
        return context

    def _map_failure_reason(self, reason: str) -> str:
        mapping = {
            'student-not-found': 'O aluno escolhido nao foi encontrado.',
            'email-required': 'Defina um e-mail no formulario ou no cadastro do aluno antes de gerar o convite.',
            'student-box-mismatch': 'Este aluno ja esta vinculado a outro box raiz.',
            'open-box-rate-limit-exceeded': 'O limite tecnico de convites abertos nesta janela foi alcancado. Gere invite individual ou aguarde a janela reiniciar.',
        }
        return mapping.get(reason, 'Nao foi possivel gerar o convite do app do aluno.')

    def _build_membership_status_tone(self, status: str) -> str:
        if status == StudentBoxMembershipStatus.ACTIVE:
            return 'ok'
        if status == StudentBoxMembershipStatus.PENDING_APPROVAL:
            return 'attention'
        if status in {
            StudentBoxMembershipStatus.SUSPENDED_FINANCIAL,
            StudentBoxMembershipStatus.REVOKED,
        }:
            return 'danger'
        return 'muted'

    def _build_status_label(self, invitation: StudentAppInvitation) -> str:
        if invitation.accepted_at:
            return 'Aceito'
        if invitation.is_expired:
            return 'Expirado'
        return 'Pendente'

    def _build_status_tone(self, invitation: StudentAppInvitation) -> str:
        if invitation.accepted_at:
            return 'ok'
        if invitation.is_expired:
            return 'muted'
        return 'attention'

    def _build_last_email_delivery_label(self, delivery) -> str:
        if delivery is None:
            return 'Nenhum envio de e-mail registrado ainda.'
        if delivery.status == StudentInvitationDeliveryStatus.SENT and delivery.sent_at:
            return f'Ultimo e-mail enviado em {delivery.sent_at:%d/%m/%Y %H:%M} via {delivery.provider}.'
        if delivery.status == StudentInvitationDeliveryStatus.DELIVERED and delivery.sent_at:
            return f'E-mail entregue em {delivery.sent_at:%d/%m/%Y %H:%M} via {delivery.provider}.'
        if delivery.status in {
            StudentInvitationDeliveryStatus.FAILED,
            StudentInvitationDeliveryStatus.BOUNCED,
            StudentInvitationDeliveryStatus.COMPLAINED,
            StudentInvitationDeliveryStatus.SUPPRESSED,
        } and delivery.failed_at:
            return f'Ultima falha de e-mail em {delivery.failed_at:%d/%m/%Y %H:%M} via {delivery.provider}.'
        if delivery.status == StudentInvitationDeliveryStatus.DELAYED:
            return f'E-mail atrasado no provedor {delivery.provider}.'
        return f'Ultimo status de e-mail: {delivery.status}.'

    def _build_last_email_delivery_status_label(self, delivery) -> str:
        if delivery is None:
            return 'Sem envio'
        mapping = {
            StudentInvitationDeliveryStatus.SENT: 'Enviado',
            StudentInvitationDeliveryStatus.DELIVERED: 'Entregue',
            StudentInvitationDeliveryStatus.DELAYED: 'Atrasado',
            StudentInvitationDeliveryStatus.FAILED: 'Falhou',
            StudentInvitationDeliveryStatus.BOUNCED: 'Bounce',
            StudentInvitationDeliveryStatus.COMPLAINED: 'Complaint',
            StudentInvitationDeliveryStatus.SUPPRESSED: 'Suprimido',
        }
        return mapping.get(delivery.status, delivery.status)

    def _build_last_email_delivery_status_tone(self, delivery) -> str:
        if delivery is None:
            return 'muted'
        if delivery.status == StudentInvitationDeliveryStatus.DELIVERED:
            return 'ok'
        if delivery.status in {
            StudentInvitationDeliveryStatus.BOUNCED,
            StudentInvitationDeliveryStatus.COMPLAINED,
            StudentInvitationDeliveryStatus.SUPPRESSED,
            StudentInvitationDeliveryStatus.FAILED,
        }:
            return 'danger'
        if delivery.status in {StudentInvitationDeliveryStatus.SENT, StudentInvitationDeliveryStatus.DELAYED}:
            return 'attention'
        return 'muted'

    def _build_last_whatsapp_delivery_label(self, delivery) -> str:
        if delivery is None:
            return 'Nenhum envio de WhatsApp registrado ainda.'
        if delivery.status == StudentInvitationDeliveryStatus.SENT and delivery.sent_at:
            return f'Ultima mensagem aberta em {delivery.sent_at:%d/%m/%Y %H:%M} pela equipe.'
        return f'Ultimo status de WhatsApp: {delivery.status}.'

    def _build_last_whatsapp_delivery_status_label(self, delivery) -> str:
        if delivery is None:
            return 'Sem mensagem'
        if delivery.status == StudentInvitationDeliveryStatus.SENT:
            return 'Mensagem aberta'
        return delivery.status

    def _build_last_whatsapp_delivery_status_tone(self, delivery) -> str:
        if delivery is None:
            return 'muted'
        if delivery.status == StudentInvitationDeliveryStatus.SENT:
            return 'ok'
        return 'attention'

    def _is_stalled_invitation(self, *, invitation: StudentAppInvitation, email_delivery, whatsapp_delivery) -> bool:
        if invitation.accepted_at or invitation.is_expired:
            return False
        if whatsapp_delivery is not None and whatsapp_delivery.status == StudentInvitationDeliveryStatus.SENT:
            return False
        if email_delivery is None:
            return False
        return email_delivery.status in {
            StudentInvitationDeliveryStatus.BOUNCED,
            StudentInvitationDeliveryStatus.COMPLAINED,
            StudentInvitationDeliveryStatus.SUPPRESSED,
        }

    def _build_stalled_reason_label(self, delivery) -> str:
        if delivery is None:
            return 'Sem handoff de WhatsApp ainda.'
        mapping = {
            StudentInvitationDeliveryStatus.BOUNCED: 'E-mail devolvido. Falta enviar mensagem no WhatsApp.',
            StudentInvitationDeliveryStatus.COMPLAINED: 'Aluno reclamou do e-mail. Falta seguir pelo WhatsApp.',
            StudentInvitationDeliveryStatus.SUPPRESSED: 'Endereco bloqueado no provedor. Falta seguir pelo WhatsApp.',
        }
        return mapping.get(delivery.status, 'Falta enviar mensagem no WhatsApp.')

    def _build_stalled_priority_rank(self, delivery) -> int:
        if delivery is None:
            return 99
        if delivery.status == StudentInvitationDeliveryStatus.COMPLAINED:
            return 0
        if delivery.status == StudentInvitationDeliveryStatus.BOUNCED:
            return 1
        if delivery.status == StudentInvitationDeliveryStatus.SUPPRESSED:
            return 2
        return 99

    def _build_stalled_priority_label(self, delivery) -> str:
        if delivery is None:
            return 'Fila'
        mapping = {
            StudentInvitationDeliveryStatus.COMPLAINED: 'Prioridade maxima',
            StudentInvitationDeliveryStatus.BOUNCED: 'Prioridade alta',
            StudentInvitationDeliveryStatus.SUPPRESSED: 'Prioridade alta',
        }
        return mapping.get(delivery.status, 'Fila')

    def _build_stalled_priority_tone(self, delivery) -> str:
        if delivery is None:
            return 'muted'
        if delivery.status == StudentInvitationDeliveryStatus.COMPLAINED:
            return 'danger'
        if delivery.status in {
            StudentInvitationDeliveryStatus.BOUNCED,
            StudentInvitationDeliveryStatus.SUPPRESSED,
        }:
            return 'attention'
        return 'muted'

    def _build_stalled_since_label(self, stalled_since) -> str:
        if stalled_since is None:
            return ''
        return f'Travado desde {stalled_since:%d/%m/%Y %H:%M}'

    def _can_send_email(self, *, invitation: StudentAppInvitation, delivery) -> bool:
        if not invitation.invited_email or invitation.is_expired or invitation.accepted_at:
            return False
        if delivery is None:
            return True
        return delivery.status not in {
            StudentInvitationDeliveryStatus.BOUNCED,
            StudentInvitationDeliveryStatus.COMPLAINED,
            StudentInvitationDeliveryStatus.SUPPRESSED,
        }

    def _build_email_action_recommendation_label(self, *, invitation: StudentAppInvitation, delivery) -> str:
        if invitation.accepted_at:
            return 'Convite concluido pelo aluno.'
        if invitation.is_expired:
            return 'Gere um novo convite antes de reenviar.'
        if not invitation.invited_email:
            return 'Use Enviar mensagem no WhatsApp. Quando o aluno entrar, o e-mail dele sincroniza com o cadastro.'
        if delivery is None:
            return 'Se quiser acelerar, use Enviar mensagem no WhatsApp com o link pronto.'
        if delivery.status == StudentInvitationDeliveryStatus.DELIVERED:
            return 'E-mail entregue. Se o aluno nao responder, acompanhe pelo WhatsApp.'
        if delivery.status == StudentInvitationDeliveryStatus.DELAYED:
            return 'E-mail atrasado. Para acelerar, use Enviar mensagem no WhatsApp.'
        if delivery.status == StudentInvitationDeliveryStatus.BOUNCED:
            return 'Bounce detectado. Use Enviar mensagem no WhatsApp com o link do convite.'
        if delivery.status == StudentInvitationDeliveryStatus.COMPLAINED:
            return 'Complaint detectado. Nao reenvie por e-mail; use Enviar mensagem no WhatsApp.'
        if delivery.status == StudentInvitationDeliveryStatus.SUPPRESSED:
            return 'Endereco suprimido pelo provedor. Use Enviar mensagem no WhatsApp para seguir com o convite.'
        if delivery.status == StudentInvitationDeliveryStatus.FAILED:
            return 'Falha transacional. Se precisar destravar agora, use Enviar mensagem no WhatsApp.'
        if delivery.status == StudentInvitationDeliveryStatus.SENT:
            return 'E-mail em rota. Se quiser acelerar, use Enviar mensagem no WhatsApp.'
        return 'Revise o status antes de escolher o proximo canal.'

    def _build_email_action_recommendation_tone(self, *, invitation: StudentAppInvitation, delivery) -> str:
        if invitation.accepted_at:
            return 'ok'
        if invitation.is_expired or not invitation.invited_email:
            return 'danger'
        if delivery is None:
            return 'muted'
        if delivery.status == StudentInvitationDeliveryStatus.DELIVERED:
            return 'ok'
        if delivery.status in {
            StudentInvitationDeliveryStatus.BOUNCED,
            StudentInvitationDeliveryStatus.COMPLAINED,
            StudentInvitationDeliveryStatus.SUPPRESSED,
        }:
            return 'danger'
        if delivery.status in {
            StudentInvitationDeliveryStatus.SENT,
            StudentInvitationDeliveryStatus.DELAYED,
            StudentInvitationDeliveryStatus.FAILED,
        }:
            return 'attention'
        return 'muted'
