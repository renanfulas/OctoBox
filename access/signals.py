"""
ARQUIVO: sinais do app access.

POR QUE ELE EXISTE:
- Garante que mudancas crtíticas em papéis e permissoes reajam instantaneamente no sistema.

O QUE ESTE ARQUIVO FAZ:
1. Escuta mudanças na relação de Grupos de Usuários (m2m_changed).
2. Força a invalidação do Shadow Role (Cache 24h) no Redis caso um gerente seja admitido, demitido ou rebaixado.
"""

from django.db.models.signals import m2m_changed
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.core.cache import cache

User = get_user_model()

@receiver(m2m_changed, sender=User.groups.through)
def invalidate_shadow_role_on_group_change(sender, instance, action, **kwargs):
    """
    Invalida instantaneamente a Role guardada no Redis quando um papel do usuário muda.
    Explicação AAA: Isso permite que a leitura da Role tenha cache infinito (ou 24h) e custo Zero de Banco,
    mas se um admin demitir alguém ou rebaixá-lo, o efeito é IMEDIATO para o usuário na proxima requisição.
    """
    if action in ['post_add', 'post_remove', 'post_clear']:
        # Verifica a instância: ela pode ser o User ou o Group contendo os Users.
        if isinstance(instance, User):
            cache_key = f"octobox:user_role_slug:uid_{instance.id}"
            cache.delete(cache_key)
        else:
            # Caso 'instance' seja um Group de acesso onde usuários foram adicionados/removidos.
            # 'pk_set' contém os IDs dos usuários afetados
            pk_set = kwargs.get('pk_set', set())
            for user_id in pk_set:
                cache_key = f"octobox:user_role_slug:uid_{user_id}"
                cache.delete(cache_key)
