from __future__ import annotations

import hashlib

from django.conf import settings

_INVITE_COOKIE = 'student_invite_pending'
_INVITE_COOKIE_MAX_AGE = 900  # 15 min
from django.contrib import messages
from django.http import HttpResponseNotAllowed
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import TemplateView, View

from shared_support.box_runtime import get_box_runtime_slug
from auditing.models import AuditEvent
from .application.commands import AuthenticateStudentWithProviderCommand
from .application.use_cases import AuthenticateStudentWithProvider
from .infrastructure.repositories import DjangoStudentIdentityRepository
from .infrastructure.session import clear_student_session_cookie
from .funnel_events import record_student_onboarding_event
from .models import StudentOnboardingJourney
from .oauth_actions import (
    StudentOAuthProviderExchangeError,
    authenticate_student_oauth_identity,
    exchange_student_oauth_identity_payload,
    finalize_student_oauth_callback,
)
from .oauth_journeys import resolve_student_oauth_journey
from .oauth_loader import enforce_student_oauth_callback_rate_limit
from .oauth_policy import StudentOAuthCallbackPolicyError, read_student_oauth_callback_input
from .oauth_providers import OAuthProviderError, build_provider
from .oauth_state import build_oauth_state
from .security import (
    check_student_flow_rate_limit,
    resolve_student_client_ip,
)


class StudentSignInView(TemplateView):
    template_name = 'student_identity/login.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        invite_token = (
            self.request.COOKIES.get(_INVITE_COOKIE, '').strip()
            or self.request.GET.get('invite', '').strip()
        )
        invite_context_label = ''
        repository = DjangoStudentIdentityRepository()
        invitation = repository.find_invitation_by_token(invite_token) if invite_token else None
        box_invite_link = None
        if invitation is not None:
            invite_context_label = invitation.box_root_slug.replace('-', ' ').title()
        elif invite_token:
            box_invite_link = repository.find_box_invite_link_by_token(invite_token)
            if box_invite_link is not None:
                invite_context_label = box_invite_link.box_root_slug.replace('-', ' ').title()
        context['invite_token'] = invite_token
        context['invite_context_label'] = invite_context_label
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
            'invite-not-found': 'O convite informado nao foi encontrado ou expirou. Tente entrar sem convite.',
            'invite-box-mismatch': 'Este convite nao pertence ao box atual.',
            'invite-expired': 'O convite informado nao foi encontrado ou expirou. Tente entrar sem convite.',
            'invite-email-mismatch': 'O email informado nao corresponde ao convite.',
            'student-email-ambiguous': 'Nao foi possivel validar este aluno por email neste box.',
            'box-root-mismatch': 'Esta conta de aluno pertence a outro box.',
            'student-box-mismatch': 'Este aluno ja esta vinculado a outro box.',
            'provider-subject-required': 'Nao foi possivel validar a identidade social informada.',
        }
        return mapping.get(reason, 'Nao foi possivel autorizar este aluno no box atual.')


class StudentOAuthStartView(View):
    def get(self, request, provider, *args, **kwargs):
        invite_token = (
            request.COOKIES.get(_INVITE_COOKIE, '').strip()
            or request.GET.get('invite', '').strip()
        )
        journey = resolve_student_oauth_journey(
            repository=DjangoStudentIdentityRepository(),
            invite_token=invite_token,
        )
        if journey:
            record_student_onboarding_event(
                actor=None,
                actor_role='',
                journey=journey,
                event='oauth_started',
                target_model='student_identity.StudentOAuthStart',
                target_label=provider,
                description='Fluxo de OAuth iniciado para onboarding do aluno.',
                metadata={
                    'box_root_slug': get_box_runtime_slug(),
                    'invite_token': invite_token,
                    'provider': provider,
                },
            )
        try:
            oauth_provider = build_provider(provider)
            authorize_url = oauth_provider.get_authorize_url(
                state=build_oauth_state(provider=provider, invite_token=invite_token),
                request=request,
            )
        except OAuthProviderError as exc:
            messages.error(request, self._map_provider_error(str(exc)))
            response = redirect(reverse('student-identity-login'))
            if invite_token:
                response.set_cookie(
                    _INVITE_COOKIE, invite_token,
                    max_age=_INVITE_COOKIE_MAX_AGE,
                    httponly=True, secure=not settings.DEBUG, samesite='Lax',
                )
            return response
        return redirect(authorize_url)

    def _map_provider_error(self, reason: str) -> str:
        mapping = {
            'google-client-id-missing': 'Google ainda nao foi configurado para o app do aluno.',
            'apple-client-id-missing': 'Apple ainda nao foi configurada para o app do aluno.',
            'provider-not-supported': 'O provedor solicitado nao e suportado.',
        }
        return mapping.get(reason, 'Nao foi possivel iniciar a autenticacao social agora.')


class StudentOAuthCallbackView(StudentSignInView):
    identity_repository_class = DjangoStudentIdentityRepository

    def dispatch(self, request, *args, **kwargs):
        if request.method not in {'GET', 'POST'}:
            return HttpResponseNotAllowed(['GET', 'POST'])
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, provider, *args, **kwargs):
        return self._handle_callback(request, provider)

    def post(self, request, provider, *args, **kwargs):
        return self._handle_callback(request, provider)

    def _handle_callback(self, request, provider: str):
        rate_limit_response = enforce_student_oauth_callback_rate_limit(request=request, provider=provider)
        if rate_limit_response is not None:
            return rate_limit_response
        try:
            callback_input = read_student_oauth_callback_input(request=request, provider=provider)
        except StudentOAuthCallbackPolicyError as exc:
            messages.error(request, str(exc))
            return redirect('student-identity-login')
        try:
            identity_payload = exchange_student_oauth_identity_payload(
                provider=provider,
                code=callback_input.code,
                request=request,
                provider_builder=build_provider,
            )
        except StudentOAuthProviderExchangeError as exc:
            messages.error(request, self._map_provider_callback_error(str(exc)))
            return redirect('student-identity-login')

        result = authenticate_student_oauth_identity(
            authenticate_identity=self.authenticate_identity,
            identity_payload=identity_payload,
            invite_token=callback_input.invite_token,
        )
        return finalize_student_oauth_callback(
            request=request,
            provider=provider,
            state_payload=callback_input.state_payload,
            identity_payload=identity_payload,
            authentication_result=result,
            identity_repository_class=self.identity_repository_class,
            map_failure_reason=self._map_failure_reason,
        )

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
                target_label=hashlib.sha256(str(self.kwargs.get('token', '')).encode()).hexdigest()[:16],
                description='Landing de invite do aluno bloqueada por rajada.',
                metadata={
                    'ip_hash': hashlib.sha256(resolve_student_client_ip(request).encode()).hexdigest()[:8],
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
        context['login_url'] = reverse('student-identity-login')
        context['journey_label'] = 'aluno'
        invitation = DjangoStudentIdentityRepository().find_invitation_by_token(str(self.kwargs['token']))
        context['invite_not_found'] = invitation is None
        context['invite_expired'] = bool(invitation and invitation.is_expired)
        context['invite_already_accepted'] = bool(invitation and invitation.accepted_at)
        if invitation is not None:
            record_student_onboarding_event(
                actor=None,
                actor_role='',
                journey=invitation.onboarding_journey,
                event='landing_viewed',
                target_model='student_identity.StudentAppInvitation',
                target_id=str(invitation.id),
                target_label=invitation.student.full_name,
                description='Landing do convite do aluno visualizada.',
                metadata={
                    'box_root_slug': invitation.box_root_slug,
                    'student_id': invitation.student_id,
                    'invitation_id': invitation.id,
                },
            )
        else:
            _token_hash = hashlib.sha256(str(self.kwargs['token']).encode()).hexdigest()[:16]
            AuditEvent.objects.create(
                actor=None,
                actor_role='',
                action='student_invite_landing.invalid_token_accessed',
                target_model='student_identity.StudentAppInvitation',
                target_label=_token_hash,
                description='Tentativa de abrir convite individual inexistente.',
                metadata={
                    'box_root_slug': get_box_runtime_slug(),
                    'token_hash': _token_hash,
                    'path': self.request.path,
                },
            )
        return context

    def render_to_response(self, context, **response_kwargs):
        response = super().render_to_response(context, **response_kwargs)
        if not context.get('invite_not_found') and not context.get('invite_expired'):
            response.set_cookie(
                _INVITE_COOKIE, str(self.kwargs['token']),
                max_age=_INVITE_COOKIE_MAX_AGE,
                httponly=True, secure=not settings.DEBUG, samesite='Lax',
            )
        return response


class StudentBoxInviteLandingView(TemplateView):
    template_name = 'student_identity/invite_landing.html'

    def dispatch(self, request, *args, **kwargs):
        allowed, retry_after = check_student_flow_rate_limit(
            scope='student-box-invite-landing',
            token=f'ip:{resolve_student_client_ip(request)}',
            limit=max(1, int(getattr(settings, 'STUDENT_INVITE_LANDING_RATE_LIMIT_MAX_REQUESTS', 20))),
            window_seconds=max(1, int(getattr(settings, 'STUDENT_INVITE_LANDING_RATE_LIMIT_WINDOW_SECONDS', 300))),
        )
        if not allowed:
            AuditEvent.objects.create(
                actor=None,
                actor_role='',
                action='student_box_invite_landing.rate_limited',
                target_model='student_identity.StudentBoxInviteLink',
                target_label=hashlib.sha256(str(self.kwargs.get('token', '')).encode()).hexdigest()[:16],
                description='Landing de link em massa do aluno bloqueada por rajada.',
                metadata={
                    'ip_hash': hashlib.sha256(resolve_student_client_ip(request).encode()).hexdigest()[:8],
                    'path': request.path,
                },
            )
            response = HttpResponse('Muitas tentativas de abrir links de convite em pouco tempo. Aguarde e tente novamente.', status=429)
            response['Retry-After'] = str(retry_after)
            return response
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['invite_token'] = self.kwargs['token']
        context['login_url'] = reverse('student-identity-login')
        context['journey_label'] = 'grupo do box'
        context['mass_invite_mode'] = True
        box_invite_link = DjangoStudentIdentityRepository().find_box_invite_link_by_token(str(self.kwargs['token']))
        context['invite_not_found'] = box_invite_link is None
        context['invite_unavailable'] = bool(box_invite_link is not None and not box_invite_link.can_accept)
        if box_invite_link is not None:
            record_student_onboarding_event(
                actor=None,
                actor_role='',
                journey=StudentOnboardingJourney.MASS_BOX_INVITE,
                event='landing_viewed',
                target_model='student_identity.StudentBoxInviteLink',
                target_id=str(box_invite_link.id),
                target_label=box_invite_link.box_root_slug,
                description='Landing do link em massa visualizada.',
                metadata={
                    'box_root_slug': box_invite_link.box_root_slug,
                    'box_invite_link_id': box_invite_link.id,
                },
            )
        else:
            _token_hash = hashlib.sha256(str(self.kwargs['token']).encode()).hexdigest()[:16]
            AuditEvent.objects.create(
                actor=None,
                actor_role='',
                action='student_box_invite_landing.invalid_token_accessed',
                target_model='student_identity.StudentBoxInviteLink',
                target_label=_token_hash,
                description='Tentativa de abrir link em massa inexistente.',
                metadata={
                    'box_root_slug': get_box_runtime_slug(),
                    'token_hash': _token_hash,
                    'path': self.request.path,
                },
            )
        return context

    def render_to_response(self, context, **response_kwargs):
        response = super().render_to_response(context, **response_kwargs)
        if not context.get('invite_not_found') and not context.get('invite_unavailable'):
            response.set_cookie(
                _INVITE_COOKIE, str(self.kwargs['token']),
                max_age=_INVITE_COOKIE_MAX_AGE,
                httponly=True, secure=not settings.DEBUG, samesite='Lax',
            )
        return response
