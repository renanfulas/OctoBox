from __future__ import annotations

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from access.permissions import RoleRequiredMixin
from access.roles import ROLE_COACH, ROLE_DEV, ROLE_MANAGER, ROLE_OWNER, ROLE_RECEPTION

from .funnel_events import record_student_onboarding_event
from .models import StudentAppInvitation
from .staff_action_dispatcher import dispatch_student_invitation_post_action
from .staff_operations_context import build_student_invitation_operations_context
from .security import check_student_flow_rate_limit, maybe_emit_student_anomaly_alert
from .staff_delivery_actions import StudentInvitationDeliveryActionsMixin
from .staff_invite_actions import StudentInvitationInviteActionsMixin
from .staff_membership_actions import StudentInvitationMembershipActionsMixin
from .staff_policies import (
    actor_has_student_operations_capability,
    build_student_operations_access_matrix,
    deny_read_only_student_operations_actor,
    get_student_operations_actor_role_slug,
    require_student_operations_action_role,
)


class StudentInvitationOperationsView(
    StudentInvitationInviteActionsMixin,
    StudentInvitationDeliveryActionsMixin,
    StudentInvitationMembershipActionsMixin,
    LoginRequiredMixin,
    RoleRequiredMixin,
    TemplateView,
):
    allowed_roles = (ROLE_OWNER, ROLE_DEV, ROLE_MANAGER, ROLE_RECEPTION, ROLE_COACH)
    template_name = 'student_identity/operations_invites.html'
    invite_operator_roles = (ROLE_OWNER, ROLE_DEV, ROLE_MANAGER, ROLE_RECEPTION)
    membership_approval_roles = (ROLE_RECEPTION, ROLE_MANAGER, ROLE_OWNER, ROLE_DEV)
    membership_lifecycle_roles = (ROLE_MANAGER, ROLE_OWNER, ROLE_DEV)

    def _build_access_matrix(self, request) -> dict:
        role_slug = self._get_actor_role_slug(request)
        return build_student_operations_access_matrix(
            role_slug=role_slug,
            invite_operator_roles=self.invite_operator_roles,
            membership_approval_roles=self.membership_approval_roles,
            membership_lifecycle_roles=self.membership_lifecycle_roles,
        )

    def _deny_read_only_actor(self, request):
        return deny_read_only_student_operations_actor(request)

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
        return get_student_operations_actor_role_slug(request.user)

    def _require_action_roles(self, request, *, allowed_roles: tuple[str, ...], denied_message: str):
        return require_student_operations_action_role(
            request,
            actor_role_slug=self._get_actor_role_slug(request),
            allowed_roles=allowed_roles,
            denied_message=denied_message,
        )

    def _dispatch_post_action(self, request):
        return dispatch_student_invitation_post_action(self, request)

    def post(self, request, *args, **kwargs):
        access_matrix = self._build_access_matrix(request)
        if not actor_has_student_operations_capability(access_matrix):
            return self._deny_read_only_actor(request)
        return self._dispatch_post_action(request)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return build_student_invitation_operations_context(self, context=context, **kwargs)

    def _map_failure_reason(self, reason: str) -> str:
        mapping = {
            'student-not-found': 'O aluno escolhido nao foi encontrado.',
            'email-required': 'Defina um e-mail no formulario ou no cadastro do aluno antes de gerar o convite.',
            'student-box-mismatch': 'Este aluno ja esta vinculado a outro box raiz.',
            'open-box-rate-limit-exceeded': 'O limite tecnico de convites abertos nesta janela foi alcancado. Gere invite individual ou aguarde a janela reiniciar.',
        }
        return mapping.get(reason, 'Nao foi possivel gerar o convite do app do aluno.')
