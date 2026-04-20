"""
ARQUIVO: apresentacao da central operacional de ativacao do aluno.

POR QUE ELE EXISTE:
- centraliza labels, tons e snapshots prontos para a UI.

O QUE ESTE ARQUIVO FAZ:
1. traduz status de convite, membership e entregas para texto e tom visual.
2. monta a leitura pronta do link em massa ativo.
3. encapsula pequenas heuristicas de apresentacao para a tela operacional.
"""

from __future__ import annotations

from django.urls import reverse

from .models import StudentBoxMembershipStatus, StudentInvitationDeliveryStatus, StudentOnboardingJourney


class StudentInvitationOperationsPresenter:
    def __init__(self, *, request, access_matrix: dict):
        self.request = request
        self.access_matrix = access_matrix

    def build_membership_status_tone(self, status: str) -> str:
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

    def build_status_label(self, invitation) -> str:
        if invitation.accepted_at:
            return 'Aceito'
        if invitation.is_expired:
            return 'Expirado'
        return 'Pendente'

    def build_status_tone(self, invitation) -> str:
        if invitation.accepted_at:
            return 'ok'
        if invitation.is_expired:
            return 'muted'
        return 'attention'

    def build_box_invite_link_status_label(self, link) -> str:
        if link.is_revoked:
            return 'Revogado'
        if link.is_paused:
            return 'Pausado'
        if link.is_expired:
            return 'Expirado'
        if link.is_exhausted:
            return 'Limite atingido'
        return 'Disponivel'

    def build_box_invite_link_status_tone(self, link) -> str:
        if link.can_accept:
            return 'ok'
        if link.is_paused:
            return 'attention'
        return 'muted'

    def build_active_box_invite_link_payload(self, *, active_box_invite_link):
        if active_box_invite_link is None:
            return None
        return {
            'id': active_box_invite_link.id,
            'token': str(active_box_invite_link.token),
            'invite_url': (
                self.request.build_absolute_uri(
                    reverse('student-identity-box-invite', kwargs={'token': active_box_invite_link.token})
                )
                if self.access_matrix['can_view_invite_links'] else ''
            ),
            'use_count': active_box_invite_link.use_count,
            'max_uses': active_box_invite_link.max_uses,
            'expires_at': active_box_invite_link.expires_at,
            'is_paused': active_box_invite_link.is_paused,
            'can_accept': active_box_invite_link.can_accept,
            'can_operate': self.access_matrix['can_operate_invites'],
            'status_label': self.build_box_invite_link_status_label(active_box_invite_link),
            'status_tone': self.build_box_invite_link_status_tone(active_box_invite_link),
        }

    def build_last_email_delivery_label(self, delivery) -> str:
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

    def build_last_email_delivery_status_label(self, delivery) -> str:
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

    def build_last_email_delivery_status_tone(self, delivery) -> str:
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

    def build_last_whatsapp_delivery_label(self, delivery) -> str:
        if delivery is None:
            return 'Nenhum envio de WhatsApp registrado ainda.'
        if delivery.status == StudentInvitationDeliveryStatus.SENT and delivery.sent_at:
            return f'Ultima mensagem aberta em {delivery.sent_at:%d/%m/%Y %H:%M} pela equipe.'
        return f'Ultimo status de WhatsApp: {delivery.status}.'

    def build_last_whatsapp_delivery_status_label(self, delivery) -> str:
        if delivery is None:
            return 'Sem mensagem'
        if delivery.status == StudentInvitationDeliveryStatus.SENT:
            return 'Mensagem aberta'
        return delivery.status

    def build_last_whatsapp_delivery_status_tone(self, delivery) -> str:
        if delivery is None:
            return 'muted'
        if delivery.status == StudentInvitationDeliveryStatus.SENT:
            return 'ok'
        return 'attention'

    def is_stalled_invitation(self, *, invitation, email_delivery, whatsapp_delivery) -> bool:
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

    def build_stalled_reason_label(self, delivery) -> str:
        if delivery is None:
            return 'Sem handoff de WhatsApp ainda.'
        mapping = {
            StudentInvitationDeliveryStatus.BOUNCED: 'E-mail devolvido. Falta enviar mensagem no WhatsApp.',
            StudentInvitationDeliveryStatus.COMPLAINED: 'Aluno reclamou do e-mail. Falta seguir pelo WhatsApp.',
            StudentInvitationDeliveryStatus.SUPPRESSED: 'Endereco bloqueado no provedor. Falta seguir pelo WhatsApp.',
        }
        return mapping.get(delivery.status, 'Falta enviar mensagem no WhatsApp.')

    def build_stalled_priority_rank(self, delivery) -> int:
        if delivery is None:
            return 99
        if delivery.status == StudentInvitationDeliveryStatus.COMPLAINED:
            return 0
        if delivery.status == StudentInvitationDeliveryStatus.BOUNCED:
            return 1
        if delivery.status == StudentInvitationDeliveryStatus.SUPPRESSED:
            return 2
        return 99

    def build_stalled_priority_label(self, delivery) -> str:
        if delivery is None:
            return 'Fila'
        mapping = {
            StudentInvitationDeliveryStatus.COMPLAINED: 'Prioridade maxima',
            StudentInvitationDeliveryStatus.BOUNCED: 'Prioridade alta',
            StudentInvitationDeliveryStatus.SUPPRESSED: 'Prioridade alta',
        }
        return mapping.get(delivery.status, 'Fila')

    def build_stalled_priority_tone(self, delivery) -> str:
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

    def build_stalled_since_label(self, stalled_since) -> str:
        if stalled_since is None:
            return ''
        return f'Travado desde {stalled_since:%d/%m/%Y %H:%M}'

    def can_send_email(self, *, invitation, delivery) -> bool:
        if not invitation.invited_email or invitation.is_expired or invitation.accepted_at:
            return False
        if delivery is None:
            return True
        return delivery.status not in {
            StudentInvitationDeliveryStatus.BOUNCED,
            StudentInvitationDeliveryStatus.COMPLAINED,
            StudentInvitationDeliveryStatus.SUPPRESSED,
        }

    def build_email_action_recommendation_label(self, *, invitation, delivery) -> str:
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

    def build_email_action_recommendation_tone(self, *, invitation, delivery) -> str:
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

    def build_empty_journey_copy(self, *, journey: str) -> str:
        copy_by_journey = {
            StudentOnboardingJourney.MASS_BOX_INVITE: 'Copie o link em massa e publique no grupo oficial do box com uma chamada curta para entrar com Google ou Apple.',
            StudentOnboardingJourney.IMPORTED_LEAD_INVITE: 'A recepcao pode comecar pelos leads mais quentes usando o botao de 1 clique no WhatsApp.',
            StudentOnboardingJourney.REGISTERED_STUDENT_INVITE: 'Escolha alguns alunos ja cadastrados e dispare convites diretos para abrir este corredor.',
        }
        return copy_by_journey.get(journey, 'Comece gerando volume neste corredor para o painel aprender.')
