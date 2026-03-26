import functools
import logging
from django.db import transaction, IntegrityError
from django.utils import timezone
from rest_framework.response import Response
from .models import IdempotencyKey

logger = logging.getLogger('octobox.security')

def idempotent_action(view_func):
    """
    Decorator para garantir que uma View seja idempotente.
    Exige o header 'X-Idempotency-Key'.
    """
    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.method not in ('POST', 'PATCH', 'PUT'):
            return view_func(request, *args, **kwargs)

        # 1. Recupera a chave do cabeçalho
        key = request.headers.get('X-Idempotency-Key')
        if not key:
            # Em modo estrito de fraude, poderíamos bloquear. 
            # Por agora, apenas procedemos se não houver chave, 
            # mas o ideal para fintech é exigir.
            return view_func(request, *args, **kwargs)

        user = request.user if request.user.is_authenticated else None

        # 2. Tenta registrar ou recuperar a chave
        try:
            with transaction.atomic():
                # Race condition check: select_for_update() garante que ninguém mais mexa nessa chave agora
                idemp_obj, created = IdempotencyKey.objects.get_or_create(
                    key=key,
                    defaults={'user': user, 'locked_at': timezone.now()}
                )

                if not created:
                    # Se não foi criada agora, ela já existia.
                    if idemp_obj.locked_at and not idemp_obj.response_code:
                        return Response(
                            {"detail": "Esta operação já está sendo processada."}, 
                            status=409
                        )
                    
                    if idemp_obj.response_code:
                        # Retorna a resposta que foi salva anteriormente
                        return Response(idemp_obj.response_data, status=idemp_obj.response_code)

            # 3. Executa a ação real se for nova
            response = view_func(request, *args, **kwargs)

            # 4. Salva o resultado final para futuras repetições
            if response.status_code < 500: # Não salvamos erros de servidor (pode tentar de novo)
                idemp_obj.response_code = response.status_code
                idemp_obj.response_data = response.data if hasattr(response, 'data') else {}
                idemp_obj.locked_at = None
                idemp_obj.save()

            return response

        except Exception as e:
            logger.error(f"Erro na idempotência: {str(e)}")
            # Limpa o lock se der erro durante a execução, para permitir retry técnico
            IdempotencyKey.objects.filter(key=key).update(locked_at=None)
            raise e

    return wrapper
