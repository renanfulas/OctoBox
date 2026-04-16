from __future__ import annotations

import base64
import json
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import requests
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from django.conf import settings
from django.urls import reverse


class OAuthProviderError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class OAuthIdentityPayload:
    provider: str
    email: str
    provider_subject: str


def _urlsafe_b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('ascii')


def _decode_segment(value: str) -> dict[str, Any]:
    padding_size = (-len(value)) % 4
    padded = value + ('=' * padding_size)
    return json.loads(base64.urlsafe_b64decode(padded.encode('ascii')))


def _encode_jwt(header: dict[str, Any], payload: dict[str, Any], private_key_pem: str) -> str:
    normalized_private_key = private_key_pem.replace('\\n', '\n').strip()
    header_segment = _urlsafe_b64(json.dumps(header, separators=(',', ':')).encode('utf-8'))
    payload_segment = _urlsafe_b64(json.dumps(payload, separators=(',', ':')).encode('utf-8'))
    signing_input = f'{header_segment}.{payload_segment}'.encode('ascii')
    private_key = serialization.load_pem_private_key(normalized_private_key.encode('utf-8'), password=None)
    signature = private_key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
    return f'{header_segment}.{payload_segment}.{_urlsafe_b64(signature)}'


def _verify_rs256_jwt(token: str, *, audience: str, issuer: str, jwks: dict[str, Any]) -> dict[str, Any]:
    header_segment, payload_segment, signature_segment = token.split('.')
    header = _decode_segment(header_segment)
    payload = _decode_segment(payload_segment)
    key_id = header.get('kid')
    jwk = next((key for key in jwks.get('keys', []) if key.get('kid') == key_id), None)
    if jwk is None:
        raise OAuthProviderError('jwks-key-not-found')

    from cryptography.hazmat.primitives.asymmetric import rsa

    n = int.from_bytes(base64.urlsafe_b64decode(jwk['n'] + '=='), 'big')
    e = int.from_bytes(base64.urlsafe_b64decode(jwk['e'] + '=='), 'big')
    public_key = rsa.RSAPublicNumbers(e, n).public_key()
    public_key.verify(
        base64.urlsafe_b64decode(signature_segment + '=='),
        f'{header_segment}.{payload_segment}'.encode('ascii'),
        padding.PKCS1v15(),
        hashes.SHA256(),
    )

    if payload.get('iss') != issuer:
        raise OAuthProviderError('invalid-issuer')
    audiences = payload.get('aud')
    if isinstance(audiences, str):
        audiences = [audiences]
    if audience not in (audiences or []):
        raise OAuthProviderError('invalid-audience')
    if int(payload.get('exp', 0)) <= int(time.time()):
        raise OAuthProviderError('token-expired')
    return payload


class BaseOAuthProvider:
    provider = ''

    def __init__(self):
        self.http = requests.Session()

    def get_authorize_url(self, *, state: str, request) -> str:
        raise NotImplementedError

    def exchange_code(self, *, code: str, request) -> OAuthIdentityPayload:
        raise NotImplementedError

    def _build_callback_uri(self, request) -> str:
        callback_path = reverse('student-identity-oauth-callback', kwargs={'provider': self.provider})
        public_base_url = getattr(settings, 'STUDENT_OAUTH_PUBLIC_BASE_URL', '').strip().rstrip('/')
        if public_base_url:
            return f'{public_base_url}{callback_path}'
        return request.build_absolute_uri(callback_path)


class GoogleOAuthProvider(BaseOAuthProvider):
    provider = 'google'
    authorize_endpoint = 'https://accounts.google.com/o/oauth2/v2/auth'
    token_endpoint = 'https://oauth2.googleapis.com/token'
    userinfo_endpoint = 'https://openidconnect.googleapis.com/v1/userinfo'

    def get_authorize_url(self, *, state: str, request) -> str:
        client_id = getattr(settings, 'STUDENT_GOOGLE_OAUTH_CLIENT_ID', '').strip()
        if not client_id:
            raise OAuthProviderError('google-client-id-missing')
        query = urlencode(
            {
                'client_id': client_id,
                'redirect_uri': self._build_callback_uri(request),
                'response_type': 'code',
                'scope': 'openid email profile',
                'state': state,
                'access_type': 'online',
                'prompt': 'select_account',
            }
        )
        return f'{self.authorize_endpoint}?{query}'

    def exchange_code(self, *, code: str, request) -> OAuthIdentityPayload:
        client_id = getattr(settings, 'STUDENT_GOOGLE_OAUTH_CLIENT_ID', '').strip()
        client_secret = getattr(settings, 'STUDENT_GOOGLE_OAUTH_CLIENT_SECRET', '').strip()
        if not client_id or not client_secret:
            raise OAuthProviderError('google-client-config-missing')
        token_response = self.http.post(
            self.token_endpoint,
            data={
                'code': code,
                'client_id': client_id,
                'client_secret': client_secret,
                'redirect_uri': self._build_callback_uri(request),
                'grant_type': 'authorization_code',
            },
            timeout=10,
        )
        if token_response.status_code != 200:
            raise OAuthProviderError('google-token-exchange-failed')
        token_payload = token_response.json()
        access_token = token_payload.get('access_token', '')
        userinfo_response = self.http.get(
            self.userinfo_endpoint,
            headers={'Authorization': f'Bearer {access_token}'},
            timeout=10,
        )
        if userinfo_response.status_code != 200:
            raise OAuthProviderError('google-userinfo-failed')
        userinfo = userinfo_response.json()
        if not userinfo.get('email_verified', False):
            raise OAuthProviderError('google-email-not-verified')
        return OAuthIdentityPayload(
            provider=self.provider,
            email=(userinfo.get('email') or '').strip().lower(),
            provider_subject=str(userinfo.get('sub') or ''),
        )


class AppleOAuthProvider(BaseOAuthProvider):
    provider = 'apple'
    authorize_endpoint = 'https://appleid.apple.com/auth/authorize'
    token_endpoint = 'https://appleid.apple.com/auth/token'
    jwks_endpoint = 'https://appleid.apple.com/auth/keys'
    issuer = 'https://appleid.apple.com'

    def get_authorize_url(self, *, state: str, request) -> str:
        client_id = getattr(settings, 'STUDENT_APPLE_OAUTH_CLIENT_ID', '').strip()
        if not client_id:
            raise OAuthProviderError('apple-client-id-missing')
        query = urlencode(
            {
                'client_id': client_id,
                'redirect_uri': self._build_callback_uri(request),
                'response_type': 'code',
                'response_mode': 'form_post',
                'scope': 'name email',
                'state': state,
            }
        )
        return f'{self.authorize_endpoint}?{query}'

    def exchange_code(self, *, code: str, request) -> OAuthIdentityPayload:
        client_id = getattr(settings, 'STUDENT_APPLE_OAUTH_CLIENT_ID', '').strip()
        team_id = getattr(settings, 'STUDENT_APPLE_OAUTH_TEAM_ID', '').strip()
        key_id = getattr(settings, 'STUDENT_APPLE_OAUTH_KEY_ID', '').strip()
        private_key = getattr(settings, 'STUDENT_APPLE_OAUTH_PRIVATE_KEY', '').strip()
        if not all([client_id, team_id, key_id, private_key]):
            raise OAuthProviderError('apple-client-config-missing')
        now = int(time.time())
        client_secret = _encode_jwt(
            {'alg': 'RS256', 'kid': key_id},
            {
                'iss': team_id,
                'iat': now,
                'exp': now + 300,
                'aud': self.issuer,
                'sub': client_id,
            },
            private_key,
        )
        token_response = self.http.post(
            self.token_endpoint,
            data={
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': self._build_callback_uri(request),
                'client_id': client_id,
                'client_secret': client_secret,
            },
            timeout=10,
        )
        if token_response.status_code != 200:
            raise OAuthProviderError('apple-token-exchange-failed')
        token_payload = token_response.json()
        id_token = token_payload.get('id_token', '')
        if not id_token:
            raise OAuthProviderError('apple-id-token-missing')
        jwks_response = self.http.get(self.jwks_endpoint, timeout=10)
        if jwks_response.status_code != 200:
            raise OAuthProviderError('apple-jwks-fetch-failed')
        claims = _verify_rs256_jwt(
            id_token,
            audience=client_id,
            issuer=self.issuer,
            jwks=jwks_response.json(),
        )
        email = (claims.get('email') or '').strip().lower()
        if not email:
            raise OAuthProviderError('apple-email-missing')
        return OAuthIdentityPayload(
            provider=self.provider,
            email=email,
            provider_subject=str(claims.get('sub') or ''),
        )


def build_provider(provider: str) -> BaseOAuthProvider:
    normalized = (provider or '').strip().lower()
    if normalized == 'google':
        return GoogleOAuthProvider()
    if normalized == 'apple':
        return AppleOAuthProvider()
    raise OAuthProviderError('provider-not-supported')
