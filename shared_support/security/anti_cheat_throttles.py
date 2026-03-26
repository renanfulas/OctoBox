"""
ARQUIVO: Camada de Proteção L7 (Application) contra Comportamento Core.

POR QUE ELE EXISTE:
- Impedir que bots criem cadastros em massa via endpoints publicos ou autenticados (Spam Injection).
- Impedir que robôs de Credential Stuffing testem senhas infinitamente (Brute Force).

O QUE ESTE ARQUIVO FAZ:
1. Define Throttles para Cadastro Rápido de Aluno (StudentCreationSpamThrottle).
2. Define Throttles de Autenticação para Login (LoginBruteForceThrottle).

PONTOS CRITICOS:
- Cache backend (Redis) deve estar operante para contar precisamente a chave IP.
- Falhas silenciosas (não bloquear usuários legitimos com limites baixos demais).
"""

from shared_support.security.extraction_throttles import BaseSecurityThrottle

class StudentCreationSpamThrottle(BaseSecurityThrottle):
    """
    Bloqueia ex-funcionários ou bots de inundar o banco com inscrições falsas (Spam).
    Limite: 10 cadastros por IP por hora.
    Se cruzar a linha, toma block de 1 hora.
    """
    RATE_LIMIT_WINDOW_SECONDS = 3600  # 1 Hora
    RATE_LIMIT_MAX_REQUESTS = 10
    scope_name = 'student_creation_spam_throttle'
    
    def on_throttle_exceeded(self, request, view):
        from auditing.services import log_audit_event
        # Avisar no Ghost Log que alguem está tentando Spam.
        log_audit_event(
            actor=request.user if request.user.is_authenticated else None,
            action='RED_FLAG_STUDENT_SPAM',
            target_label=self.get_client_ip(request),
            description='Injeção em massa de alunos detectada e bloqueada pelo Anti-Cheat L7.',
            metadata={'ip': self.get_client_ip(request), 'headers': dict(request.headers)}
        )
        super().on_throttle_exceeded(request, view)


class LoginBruteForceThrottle(BaseSecurityThrottle):
    """
    Bloqueia credential stuffing na porta da frente (LoginView).
    Limite: 5 GET/POST rápidos ao login = Tolerável. Porém, essa classe
    foi ajustada para só contabilizar tentativas nas actions POST se tiver falhado (usando interceptor na view ou check nativo do POST).
    Se usarmos genericamente no dispatch: limitará acessos à pagina de login.
    Limite geral: 15 acessos à página /login/ por IP por 10 minutos.
    (O check fino de "senha errada" requer lógica custom, mas o limit da view mata bots atirando pra todo lado).
    """
    RATE_LIMIT_WINDOW_SECONDS = 600  # 10 Minutos
    RATE_LIMIT_MAX_REQUESTS = 15
    scope_name = 'login_brute_force_throttle'

    def on_throttle_exceeded(self, request, view):
        from auditing.services import log_audit_event
        log_audit_event(
            actor=None,
            action='RED_FLAG_LOGIN_BRUTEFORCE',
            target_label=self.get_client_ip(request),
            description='Múltiplas requisições de Login suspeitas. IP Ejetado para Cooldown.',
            metadata={'ip': self.get_client_ip(request)}
        )
        super().on_throttle_exceeded(request, view)
