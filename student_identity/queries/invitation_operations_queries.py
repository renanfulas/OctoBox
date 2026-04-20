"""
ARQUIVO: queries da central operacional de ativacao do aluno.

POR QUE ELE EXISTE:
- tira leituras densas e repetitivas da view HTTP principal.

O QUE ESTE ARQUIVO FAZ:
1. monta snapshots de memberships pendentes e gerenciados.
2. monta a leitura de convites recentes e fila travada.
3. calcula cards e alertas de observabilidade.
4. centraliza a leitura do link em massa ativo.
"""

from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.urls import reverse
from django.utils import timezone

from shared_support.box_runtime import get_box_runtime_slug

from ..models import (
    StudentAppInvitation,
    StudentBoxInviteLink,
    StudentBoxMembership,
    StudentBoxMembershipStatus,
    StudentInvitationType,
)
from ..notifications import build_invitation_whatsapp_url


class StudentInvitationOperationsQueries:
    def __init__(self, *, presenter, request, access_matrix: dict):
        self.presenter = presenter
        self.request = request
        self.access_matrix = access_matrix
        self.box_root_slug = get_box_runtime_slug()

    def get_box_root_slug(self) -> str:
        return self.box_root_slug

    def get_active_box_invite_link(self):
        return (
            StudentBoxInviteLink.objects.filter(
                box_root_slug=self.box_root_slug,
                revoked_at__isnull=True,
            )
            .order_by('-created_at')
            .first()
        )

    def build_pending_memberships(self) -> list[dict]:
        return [
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
                ) if self.access_matrix['can_view_sensitive_identity_data'] else 'Oculto para este papel',
            }
            for membership in (
                StudentBoxMembership.objects.select_related('student', 'identity', 'created_from_invite')
                .filter(
                    box_root_slug=self.box_root_slug,
                    status=StudentBoxMembershipStatus.PENDING_APPROVAL,
                )
                .order_by('created_at')
            )
        ]

    def build_managed_memberships(self) -> list[dict]:
        managed_memberships = []
        for membership in (
            StudentBoxMembership.objects.select_related('student', 'identity', 'created_from_invite')
            .filter(box_root_slug=self.box_root_slug)
            .exclude(status=StudentBoxMembershipStatus.INACTIVE)
            .order_by('student__full_name', 'box_root_slug')
        ):
            managed_memberships.append(
                {
                    'id': membership.id,
                    'student_name': membership.student.full_name,
                    'student_email': (
                        membership.student.email if self.access_matrix['can_view_sensitive_identity_data'] else ''
                    ),
                    'identity_email': (
                        membership.identity.email
                        if self.access_matrix['can_view_sensitive_identity_data'] else 'Oculto para este papel'
                    ),
                    'identity_id': membership.identity_id,
                    'box_root_slug': membership.box_root_slug,
                    'status': membership.status,
                    'status_label': membership.get_status_display(),
                    'status_tone': self.presenter.build_membership_status_tone(membership.status),
                    'invite_type_label': (
                        membership.created_from_invite.get_invite_type_display()
                        if membership.created_from_invite_id else 'Sem convite'
                    ),
                    'is_primary': membership.box_root_slug == membership.identity.primary_box_root_slug,
                    'can_suspend_financial': (
                        self.access_matrix['can_manage_membership_lifecycle']
                        and membership.status == StudentBoxMembershipStatus.ACTIVE
                    ),
                    'can_reactivate': membership.status in {
                        StudentBoxMembershipStatus.SUSPENDED_FINANCIAL,
                        StudentBoxMembershipStatus.REVOKED,
                    } and self.access_matrix['can_manage_membership_lifecycle'],
                    'can_revoke': membership.status in {
                        StudentBoxMembershipStatus.ACTIVE,
                        StudentBoxMembershipStatus.SUSPENDED_FINANCIAL,
                        StudentBoxMembershipStatus.PENDING_APPROVAL,
                    } and self.access_matrix['can_manage_membership_lifecycle'],
                    'can_change_email': (
                        self.access_matrix['can_change_email']
                        and membership.status != StudentBoxMembershipStatus.REVOKED
                    ),
                }
            )
        return managed_memberships

    def build_recent_invites_snapshot(self) -> tuple[list[dict], list[dict]]:
        recent_invites = []
        stalled_invites = []
        for invitation in (
            StudentAppInvitation.objects.select_related('student', 'created_by')
            .prefetch_related('deliveries')
            .filter(box_root_slug=self.box_root_slug)
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
            invite_url = (
                self.request.build_absolute_uri(
                    reverse('student-identity-invite', kwargs={'token': invitation.token})
                )
                if self.access_matrix['can_view_invite_links'] else ''
            )
            invite_item = {
                'id': invitation.id,
                'student_name': invitation.student.full_name,
                'invite_type_label': invitation.get_invite_type_display(),
                'onboarding_journey_label': invitation.get_onboarding_journey_display(),
                'invited_email': (
                    invitation.invited_email
                    if self.access_matrix['can_view_sensitive_identity_data'] else 'Oculto para este papel'
                ),
                'status_label': self.presenter.build_status_label(invitation),
                'status_tone': self.presenter.build_status_tone(invitation),
                'expires_at': invitation.expires_at,
                'accepted_at': invitation.accepted_at,
                'created_by_name': (
                    invitation.created_by.get_full_name().strip() or invitation.created_by.username
                ) if invitation.created_by else '',
                'invite_url': invite_url,
                'can_send_email': False,
                'can_open_whatsapp': False,
                'last_email_delivery_label': self.presenter.build_last_email_delivery_label(last_email_delivery),
                'last_email_delivery_status_label': self.presenter.build_last_email_delivery_status_label(last_email_delivery),
                'last_email_delivery_status_tone': self.presenter.build_last_email_delivery_status_tone(last_email_delivery),
                'last_whatsapp_delivery_label': self.presenter.build_last_whatsapp_delivery_label(last_whatsapp_delivery),
                'last_whatsapp_delivery_status_label': self.presenter.build_last_whatsapp_delivery_status_label(last_whatsapp_delivery),
                'last_whatsapp_delivery_status_tone': self.presenter.build_last_whatsapp_delivery_status_tone(last_whatsapp_delivery),
                'email_action_recommendation_label': self.presenter.build_email_action_recommendation_label(
                    invitation=invitation,
                    delivery=last_email_delivery,
                ),
                'email_action_recommendation_tone': self.presenter.build_email_action_recommendation_tone(
                    invitation=invitation,
                    delivery=last_email_delivery,
                ),
            }
            invite_item['whatsapp_url'] = (
                build_invitation_whatsapp_url(
                    invitation=invitation,
                    invite_url=invite_item['invite_url'],
                )
                if self.access_matrix['can_operate_invites'] and invite_item['invite_url'] else ''
            )
            invite_item['can_open_whatsapp'] = (
                self.access_matrix['can_operate_invites'] and bool(invite_item['whatsapp_url'])
            )
            invite_item['can_send_email'] = self.access_matrix['can_operate_invites'] and self.presenter.can_send_email(
                invitation=invitation,
                delivery=last_email_delivery,
            )
            recent_invites.append(invite_item)

            if self.presenter.is_stalled_invitation(
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
                        'email_status_label': self.presenter.build_last_email_delivery_status_label(last_email_delivery),
                        'reason_label': self.presenter.build_stalled_reason_label(last_email_delivery),
                        'whatsapp_action_label': 'Enviar mensagem',
                        'invitation_id': invitation.id,
                        'priority_label': self.presenter.build_stalled_priority_label(last_email_delivery),
                        'priority_tone': self.presenter.build_stalled_priority_tone(last_email_delivery),
                        'stalled_since_label': self.presenter.build_stalled_since_label(stalled_since),
                        'can_open_whatsapp': self.access_matrix['can_operate_invites'],
                        'sort_key': (
                            self.presenter.build_stalled_priority_rank(last_email_delivery),
                            stalled_since,
                        ),
                    }
                )

        stalled_invites.sort(key=lambda item: (item['sort_key'][0], item['sort_key'][1]))
        for item in stalled_invites:
            item.pop('sort_key', None)
        return recent_invites, stalled_invites

    def build_observability_snapshot(
        self,
        *,
        pending_memberships: list[dict],
        stalled_invites: list[dict],
    ) -> dict:
        open_box_window_hours = max(1, int(getattr(settings, 'STUDENT_OPEN_BOX_INVITE_WINDOW_HOURS', 24)))
        open_box_limit_per_window = max(1, int(getattr(settings, 'STUDENT_OPEN_BOX_INVITE_LIMIT_PER_WINDOW', 25)))
        now = timezone.now()
        open_box_window_start = now - timedelta(hours=open_box_window_hours)

        open_box_invites_in_window = StudentAppInvitation.objects.filter(
            box_root_slug=self.box_root_slug,
            invite_type=StudentInvitationType.OPEN_BOX,
            created_at__gte=open_box_window_start,
        ).count()
        accepted_invites_last_7d = StudentAppInvitation.objects.filter(
            box_root_slug=self.box_root_slug,
            accepted_at__isnull=False,
            accepted_at__gte=now - timedelta(days=7),
        ).count()
        recent_invites_last_24h = StudentAppInvitation.objects.filter(
            box_root_slug=self.box_root_slug,
            created_at__gte=now - timedelta(hours=24),
        ).count()

        observability_cards = [
            {
                'eyebrow': 'Janela de invite aberto',
                'value': f'{open_box_invites_in_window}/{open_box_limit_per_window}',
                'detail': f'Convites abertos emitidos nas ultimas {open_box_window_hours}h.',
                'tone': (
                    'danger'
                    if open_box_invites_in_window >= open_box_limit_per_window
                    else 'attention'
                    if open_box_invites_in_window >= max(1, int(open_box_limit_per_window * 0.7))
                    else 'ok'
                ),
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

        return {
            'open_box_window_hours': open_box_window_hours,
            'open_box_limit_per_window': open_box_limit_per_window,
            'recent_invites_last_24h': recent_invites_last_24h,
            'observability_cards': observability_cards,
            'observability_alerts': observability_alerts,
        }
