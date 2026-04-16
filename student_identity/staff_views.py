from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import TemplateView

from access.permissions import RoleRequiredMixin
from access.roles import ROLE_DEV, ROLE_OWNER
from shared_support.box_runtime import get_box_runtime_slug
from shared_support.page_payloads import attach_page_payload
from .application.commands import CreateStudentInvitationCommand
from .application.use_cases import CreateStudentInvitation
from .delivery_audit import record_student_invitation_whatsapp_handoff
from .delivery_gateways import StudentEmailDeliveryError
from .forms import StudentInvitationCreateForm
from .infrastructure.repositories import DjangoStudentIdentityRepository
from .models import StudentAppInvitation, StudentInvitationDeliveryStatus
from .notifications import build_invitation_whatsapp_url, send_invitation_email
from .presentation import build_student_invitation_operations_page


class StudentInvitationOperationsView(LoginRequiredMixin, RoleRequiredMixin, TemplateView):
    allowed_roles = (ROLE_OWNER, ROLE_DEV)
    template_name = 'student_identity/operations_invites.html'

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action', 'create-invite').strip()
        if action == 'send-email':
            return self._handle_send_email(request)
        if action == 'open-whatsapp':
            return self._handle_open_whatsapp(request)

        form = StudentInvitationCreateForm(request.POST)
        if form.is_valid():
            command = CreateStudentInvitationCommand(
                student_id=form.cleaned_data['student'].id,
                invited_email=form.cleaned_data['invited_email'],
                box_root_slug=get_box_runtime_slug(),
                expires_in_days=form.cleaned_data['expires_in_days'],
                actor_id=request.user.id,
            )
            result = CreateStudentInvitation(DjangoStudentIdentityRepository()).execute(command)
            if result.success and result.invitation is not None:
                invite_url = request.build_absolute_uri(
                    reverse('student-identity-invite', kwargs={'token': result.invitation.token})
                )
                messages.success(
                    request,
                    f"Convite pronto para {result.invitation.student_name}. Link gerado: {invite_url}",
                )
                return redirect('student-invitation-operations')

            messages.error(request, self._map_failure_reason(result.failure_reason))
        return self.render_to_response(self.get_context_data(form=form))

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
        for invitation in (
            StudentAppInvitation.objects.select_related('student', 'created_by')
            .prefetch_related('deliveries')
            .filter(box_root_slug=get_box_runtime_slug())
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

        page_payload = build_student_invitation_operations_page(
            current_box_slug=get_box_runtime_slug(),
            recent_invites=recent_invites,
            stalled_invites=stalled_invites,
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
        }
        return mapping.get(reason, 'Nao foi possivel gerar o convite do app do aluno.')

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
