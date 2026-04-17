from __future__ import annotations

from django.conf import settings
from django.contrib import messages
from django.http import HttpResponseNotAllowed
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import FormView, TemplateView, View

from shared_support.box_runtime import get_box_runtime_slug
from auditing.models import AuditEvent
from .application.commands import AuthenticateStudentWithProviderCommand
from .application.use_cases import AuthenticateStudentWithProvider
from .infrastructure.repositories import DjangoStudentIdentityRepository
from .infrastructure.session import attach_student_session_cookie, clear_student_session_cookie
from .models import StudentBoxMembership, StudentBoxMembershipStatus
from .oauth_providers import OAuthProviderError, build_provider
from .oauth_state import build_oauth_state, read_oauth_state
from .security import (
    build_student_device_fingerprint,
    check_student_flow_rate_limit,
    maybe_emit_student_anomaly_alert,
    resolve_student_client_ip,
)


class StudentSignInView(TemplateView):
    template_name = 'student_identity/login.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        invite_token = self.request.GET.get('invite', '').strip()
        context['invite_token'] = invite_token
        context['google_start_url'] = reverse('student-identity-oauth-start', kwargs={'provider': 'google'})
        context['apple_start_url'] = reverse('student-identity-oauth-start', kwargs={'provider': 'apple'})
        context['google_available'] = bool(getattr(settings, 'STUDENT_GOOGLE_OAUTH_CLIENT_ID', '').strip())
        context['apple_available'] = bool(getattr(settings, 'STUDENT_APPLE_OAUTH_CLIENT_ID', '').strip())
        return context

    def authenticate_identity(self, *, provider_name: str, email: str, provider_subject: str, invite_token: str = ''):
        use_case = AuthenticateStudentWithProvider(DjangoStudentIdentityRepository())
        command = AuthenticateStudentWithProviderCommand(
            provider=provider_name,
            email=email,
            provider_subject=provider_subject,
            box_root_slug=get_box_runtime_slug(),
            invite_token=invite_token,
        )
        return use_case.execute(command)

    def _map_failure_reason(self, reason: str) -> str:
        mapping = {
            'invite-not-found': 'O convite informado nao foi encontrado.',
            'invite-box-mismatch': 'Este convite nao pertence ao box atual.',
            'invite-expired': 'Este convite ja expirou.',
            'invite-email-mismatch': 'O email informado nao corresponde ao convite.',
            'student-email-ambiguous': 'Nao foi possivel validar este aluno por email neste box.',
            'box-root-mismatch': 'Esta conta de aluno pertence a outro box.',
            'student-box-mismatch': 'Este aluno ja esta vinculado a outro box.',
            'provider-subject-required': 'Nao foi possivel validar a identidade social informada.',
        }
        return mapping.get(reason, 'Nao foi possivel autorizar este aluno no box atual.')


class StudentOAuthStartView(View):
    def get(self, request, provider, *args, **kwargs):
        invite_token = request.GET.get('invite', '').strip()
        try:
            oauth_provider = build_provider(provider)
            authorize_url = oauth_provider.get_authorize_url(
                state=build_oauth_state(provider=provider, invite_token=invite_token),
                request=request,
            )
        except OAuthProviderError as exc:
            messages.error(request, self._map_provider_error(str(exc)))
            return redirect(f"{reverse('student-identity-login')}?invite={invite_token}" if invite_token else reverse('student-identity-login'))
        return redirect(authorize_url)

    def _map_provider_error(self, reason: str) -> str:
        mapping = {
            'google-client-id-missing': 'Google ainda nao foi configurado para o app do aluno.',
            'apple-client-id-missing': 'Apple ainda nao foi configurada para o app do aluno.',
            'provider-not-supported': 'O provedor solicitado nao e suportado.',
        }
        return mapping.get(reason, 'Nao foi possivel iniciar a autenticacao social agora.')


class StudentOAuthCallbackView(StudentSignInView):
    def dispatch(self, request, *args, **kwargs):
        if request.method not in {'GET', 'POST'}:
            return HttpResponseNotAllowed(['GET', 'POST'])
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, provider, *args, **kwargs):
        return self._handle_callback(request, provider)

    def post(self, request, provider, *args, **kwargs):
        return self._handle_callback(request, provider)

    def _handle_callback(self, request, provider: str):
        allowed, retry_after = check_student_flow_rate_limit(
            scope='student-oauth-callback',
            token=f'ip:{resolve_student_client_ip(request)}',
            limit=max(1, int(getattr(settings, 'STUDENT_OAUTH_CALLBACK_RATE_LIMIT_MAX_REQUESTS', 12))),
            window_seconds=max(1, int(getattr(settings, 'STUDENT_OAUTH_CALLBACK_RATE_LIMIT_WINDOW_SECONDS', 300))),
        )
        if not allowed:
            AuditEvent.objects.create(
                actor=None,
                actor_role='',
                action='student_oauth_callback.rate_limited',
                target_model='student_identity.StudentOAuthCallback',
                target_label=provider,
                description='Callback social do aluno bloqueado por rajada.',
                metadata={
                    'provider': provider,
                    'client_ip': resolve_student_client_ip(request),
                    'path': request.path,
                },
            )
            response = HttpResponse('Muitas tentativas de callback social em pouco tempo. Aguarde e tente novamente.', status=429)
            response['Retry-After'] = str(retry_after)
            return response

        error = request.GET.get('error') or request.POST.get('error')
        if error:
            messages.error(request, 'O provedor cancelou ou recusou a autenticacao.')
            return redirect('student-identity-login')

        state_payload = read_oauth_state(request.GET.get('state') or request.POST.get('state') or '')
        if state_payload is None or state_payload.get('provider') != provider:
            messages.error(request, 'O estado da autenticacao nao e valido. Tente novamente.')
            return redirect('student-identity-login')

        code = (request.GET.get('code') or request.POST.get('code') or '').strip()
        if not code:
            messages.error(request, 'O provedor nao retornou um codigo de autenticacao valido.')
            return redirect('student-identity-login')

        try:
            oauth_provider = build_provider(provider)
            identity_payload = oauth_provider.exchange_code(code=code, request=request)
        except OAuthProviderError as exc:
            messages.error(request, self._map_provider_callback_error(str(exc)))
            return redirect('student-identity-login')

        result = self.authenticate_identity(
            provider_name=identity_payload.provider,
            email=identity_payload.email,
            provider_subject=identity_payload.provider_subject,
            invite_token=state_payload.get('invite_token', ''),
        )
        if not result.success or result.identity is None:
            messages.error(request, self._map_failure_reason(result.failure_reason))
            redirect_url = reverse('student-identity-login')
            invite_token = state_payload.get('invite_token', '')
            if invite_token:
                redirect_url = f'{redirect_url}?invite={invite_token}'
            return redirect(redirect_url)

        active_membership = StudentBoxMembership.objects.filter(
            identity_id=result.identity.id,
            box_root_slug=result.identity.box_root_slug,
        ).first()
        redirect_name = 'student-app-home'
        if active_membership is not None and active_membership.status == StudentBoxMembershipStatus.PENDING_APPROVAL:
            redirect_name = 'student-app-membership-pending'
            messages.info(request, 'Sua identidade foi validada. Agora o box precisa aprovar este acesso.')

        response = redirect(redirect_name)
        attach_student_session_cookie(
            response,
            identity_id=result.identity.id,
            box_root_slug=result.identity.box_root_slug,
            device_fingerprint=build_student_device_fingerprint(request),
        )
        client_ip = resolve_student_client_ip(request)
        actor_label = result.identity.student_name
        ip_anomaly_allowed, _ = check_student_flow_rate_limit(
            scope='student-invite-accept-ip-alert',
            token=f'ip:{client_ip}',
            limit=max(1, int(getattr(settings, 'STUDENT_INVITE_ACCEPT_IP_ALERT_THRESHOLD', 8))),
            window_seconds=max(1, int(getattr(settings, 'STUDENT_INVITE_ACCEPT_IP_ALERT_WINDOW_SECONDS', 600))),
        )
        if not ip_anomaly_allowed:
            maybe_emit_student_anomaly_alert(
                scope='student-invite-accept-ip',
                actor=None,
                actor_role='',
                target_label=client_ip,
                description='Volume suspeito de aceite de invite/callback social vindo do mesmo IP.',
                metadata={
                    'box_root_slug': result.identity.box_root_slug,
                    'student_identity_id': result.identity.id,
                    'provider': provider,
                },
                dedupe_window_seconds=max(60, int(getattr(settings, 'STUDENT_INVITE_ACCEPT_IP_ALERT_WINDOW_SECONDS', 600))),
            )
        box_anomaly_allowed, _ = check_student_flow_rate_limit(
            scope='student-invite-accept-box-alert',
            token=f'box:{result.identity.box_root_slug}',
            limit=max(1, int(getattr(settings, 'STUDENT_INVITE_ACCEPT_BOX_ALERT_THRESHOLD', 12))),
            window_seconds=max(1, int(getattr(settings, 'STUDENT_INVITE_ACCEPT_BOX_ALERT_WINDOW_SECONDS', 600))),
        )
        if not box_anomaly_allowed:
            maybe_emit_student_anomaly_alert(
                scope='student-invite-accept-box',
                actor=None,
                actor_role='',
                target_label=result.identity.box_root_slug,
                description='Volume suspeito de aceite de invites concentrado no mesmo box em janela curta.',
                metadata={
                    'client_ip': client_ip,
                    'student_identity_id': result.identity.id,
                    'student_name': actor_label,
                    'provider': provider,
                },
                dedupe_window_seconds=max(60, int(getattr(settings, 'STUDENT_INVITE_ACCEPT_BOX_ALERT_WINDOW_SECONDS', 600))),
            )
        if redirect_name == 'student-app-home':
            messages.success(request, f'Acesso do aluno {result.identity.student_name} confirmado.')
        return response

    def _map_provider_callback_error(self, reason: str) -> str:
        mapping = {
            'google-client-config-missing': 'Google ainda nao foi configurado com client secret.',
            'google-token-exchange-failed': 'O Google nao liberou o token de acesso.',
            'google-userinfo-failed': 'Nao foi possivel ler a identidade retornada pelo Google.',
            'google-email-not-verified': 'O email retornado pelo Google ainda nao esta verificado.',
            'apple-client-config-missing': 'Apple ainda nao foi configurada com as chaves do app do aluno.',
            'apple-token-exchange-failed': 'A Apple nao liberou o token de autenticacao.',
            'apple-id-token-missing': 'A Apple nao retornou a identidade esperada.',
            'apple-jwks-fetch-failed': 'Nao foi possivel validar a assinatura retornada pela Apple.',
            'jwks-key-not-found': 'A chave publica do provedor nao foi encontrada para validar a identidade.',
            'invalid-issuer': 'O emissor retornado pelo provedor nao confere.',
            'invalid-audience': 'O token retornado nao pertence a este app.',
            'token-expired': 'O token retornado pelo provedor expirou.',
            'apple-email-missing': 'A Apple nao retornou um email utilizavel para este aluno.',
        }
        return mapping.get(reason, 'Nao foi possivel concluir a autenticacao social agora.')


class StudentSignOutView(View):
    def post(self, request, *args, **kwargs):
        response = redirect('student-identity-login')
        clear_student_session_cookie(response)
        return response


class StudentInviteLandingView(TemplateView):
    template_name = 'student_identity/invite_landing.html'

    def dispatch(self, request, *args, **kwargs):
        allowed, retry_after = check_student_flow_rate_limit(
            scope='student-invite-landing',
            token=f'ip:{resolve_student_client_ip(request)}',
            limit=max(1, int(getattr(settings, 'STUDENT_INVITE_LANDING_RATE_LIMIT_MAX_REQUESTS', 20))),
            window_seconds=max(1, int(getattr(settings, 'STUDENT_INVITE_LANDING_RATE_LIMIT_WINDOW_SECONDS', 300))),
        )
        if not allowed:
            AuditEvent.objects.create(
                actor=None,
                actor_role='',
                action='student_invite_landing.rate_limited',
                target_model='student_identity.StudentAppInvitation',
                target_label=str(self.kwargs.get('token', '')),
                description='Landing de invite do aluno bloqueada por rajada.',
                metadata={
                    'client_ip': resolve_student_client_ip(request),
                    'path': request.path,
                },
            )
            response = HttpResponse('Muitas tentativas de abrir convites em pouco tempo. Aguarde e tente novamente.', status=429)
            response['Retry-After'] = str(retry_after)
            return response
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['invite_token'] = self.kwargs['token']
        context['login_url'] = f"{reverse('student-identity-login')}?invite={self.kwargs['token']}"
        return context
