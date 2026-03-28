import logging
import time
from django.shortcuts import render
from django.conf import settings
from access.roles import ROLE_HONEYPOT, get_user_role
from .honeypot_service import is_ip_honeypotted, is_honeypot_active_globally

# Configurando um logger específico para inteligência de ameaças
threat_logger = logging.getLogger('octobox.security.honeypot')

class HoneypotMiddleware:
    """
    O Coração da Decepção: Isola usuários com ROLE_HONEYPOT em uma realidade paralela.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 🚀 PERFORMANCE AAA: 'DEEP SLEEP MODE'
        # Se não houver nenhum intruso marcado nas últimas 24h, o middleware
        # nem sequer toca no Redis. Overhead = 0.00ms.
        if not is_honeypot_active_globally():
            return self.get_response(request)

        role_slug = None
        if request.user.is_authenticated:
            role = get_user_role(request.user)
            role_slug = role.slug if role else None

        # 🍯 O USUÁRIO ESTÁ NO LABIRINTO (ROLE_HONEYPOT ou IP Marcado)
        ip_addr = request.META.get('REMOTE_ADDR')
        is_honeypotted = (role_slug == ROLE_HONEYPOT) or is_ip_honeypotted(ip_addr)
        
        if not is_honeypotted:
            return self.get_response(request)

        path = request.path
        method = request.method
        
        # 1. Registro de Passos (Threat Intel)
        threat_logger.warning(
            f"[HONEYPOT] User ID: {request.user.id} | Path: {path} | Method: {method} | "
            f"IP: {request.META.get('REMOTE_ADDR')} | Agent: {request.META.get('HTTP_USER_AGENT')}"
        )

        # 2. Gatilho do Easter Egg (O Fim do Jogo)
        # Se tentar ações críticas (exportação, admin, deleção), mostramos a mensagem do Fundador.
        critical_keywords = ['/exportar/', '/admin/', '/delete/', '/configuracoes/']
        if any(keyword in path.lower() for keyword in critical_keywords):
            return render(request, 'security/founder_message.html', status=200)

        # 3. Shadow Reality (Intercepção de Dados)
        # Aqui, poderíamos injetar dados falsos no context, mas para a v1 do labirinto,
        # vamos deixar o sistema carregar o template, mas o Middleware poderia 
        # mocar as queries aqui se quiséssemos um nível AAA de isolamento.
        
        response = self.get_response(request)
        
        # Micro-atrasos simulados (Simula processamento pesado para manter o hacker calmo/lento)
        if method == 'POST':
            time.sleep(1.5) 
            
        return response
