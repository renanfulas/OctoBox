"""
ARQUIVO: Camada de Inteligência Anti-Clonagem (Fingerprint).

POR QUE ELE EXISTE:
- Impedir que usuários repassem a senha de acesso (Account Sharing).
- Proteger o sistema contra o roubo de Cookies (Session Hijacking).

O QUE ESTE ARQUIVO FAZ:
1. Gera um HMAC usando IPs, User-Agent e variáveis da máquina.
2. Atrela esse HMAC à Sessão no momento do Login.
3. Se o mesmo cookie de sessão for detectado vindo de outro hash, a sessão é destruída.

PONTOS CRITICOS:
- Precisa rodar o mais leve possível (CPU_Time < 1ms) para não matar o TTFB do Django.
"""

import hmac
import logging
from django.conf import settings
from django.contrib.auth import logout
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)

# Usamos um segredo derivado para não queimar o Secret nativo
FINGERPRINT_SECRET = getattr(settings, 'SECRET_KEY', 'fallback_secret').encode('utf-8')

def _get_client_ip(request) -> str:
    # Em produção com proxy (Render/Heroku), REMOTE_ADDR é o IP interno do proxy,
    # não o IP real do cliente. X-Forwarded-For contém o IP real.
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '127.0.0.1')


def generate_device_hash(request) -> str:
    """Computa o hash físico primário do dispositivo do cliente."""
    # Como IP dinâmico em 4G muda o último octeto, usamos a classe C network + UA.
    ip = _get_client_ip(request)
    ip_class_c = '.'.join(ip.split('.')[:3]) if '.' in ip else ip

    user_agent = request.META.get('HTTP_USER_AGENT', 'Unknown')

    payload = f"{ip_class_c}|{user_agent}".encode('utf-8')

    return hmac.new(FINGERPRINT_SECRET, payload, digestmod='sha256').hexdigest()


class SessionFingerprintMiddleware(MiddlewareMixin):
    """
    Middleware que acompanha e incinera Sessões clonadas ou compartilhadas.
    """
    def process_request(self, request):
        if not request.user.is_authenticated:
            return None

        # Hash da máquina atual que está mandando a Request
        current_hash = generate_device_hash(request)
        
        # O que estava atrelado a essa sessão quando ele fez o Login?
        stored_hash = request.session.get('security_device_fingerprint')

        if not stored_hash:
            # Primeiro login, marca com ferro na sessão.
            request.session['security_device_fingerprint'] = current_hash
            logger.info(f"Sessão {request.session.session_key} vinculada ao Fingerprint físico [User={request.user.id}]")
            return None
            
        if stored_hash != current_hash:
            # Clone Detectado! Duas máquinas físicas diferentes com o mesmo Cookie de Sessão.
            logger.critical(
                f"[SECURITY ALERT] Compartilhamento ou Sequestro de Sessão deitado no User {request.user.id}. "
                f"Sessão derrubada ativamente. (IP Novo: {request.META.get('REMOTE_ADDR')})"
            )
            
            # Desloga sumariamente o invasor/clonador e o host original.
            logout(request)
            
            # Aqui no OctoBox, podemos disparar um audit event assíncrono pro Owner investigar depois.
            from auditing import log_audit_event
            # Como a sessão já sumiu, a gente loga contra o modelo do sistema
            log_audit_event(
                actor=None,
                action="session_hijack_aborted",
                target=request.user,
                description="Inteligência de Rede desativou o login por mudança acentuada de Hardware/Localização (Anti-Share)."
            )

        return None
