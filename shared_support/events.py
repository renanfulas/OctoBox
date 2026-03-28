import json
import logging
from django.core.cache import cache

logger = logging.getLogger('octobox.events')

def get_redis_client():
    from django_redis import get_redis_connection
    return get_redis_connection('default')

def get_master_owner_id(box_id):
    """
    Regra do OctoBox CS2: Em Boxes com multiplos sócios, elege o Owner Mestre (Criador).
    Evita que o sistema faça disparo duplicado de notificações para os dois celulares.
    """
    try:
        from access.models import BoxUser
        # Busca o usuário com role 'owner' mais antigo dentro daquele Box
        master = BoxUser.objects.filter(box_id=box_id, role__slug='owner').order_by('created_at', 'id').first()
        return master.user_id if master else None
    except ImportError:
        # Fallback Antifragil para arquiteturas Single-Tenant legado
        from django.contrib.auth import get_user_model
        User = get_user_model()
        master = User.objects.filter(is_superuser=True).order_by('date_joined').first()
        return master.id if master else 1


def publish_checkin_event(box_id, student_id, student_name, student_photo_url, access_time, status='ok'):
    """
    Dispara um Push na RAM (Redis Pub/Sub). As abas de Recepção capturam isso via SSE Instantaneamente.
    Sem banco de dados.
    """
    try:
        redis_conn = get_redis_client()
        channel = f"box_{box_id}_reception_events"
        
        payload = {
            'type': 'checkin',
            'box_id': str(box_id),
            'student_id': str(student_id),
            'student_name': student_name,
            'photo_url': student_photo_url or '',
            'access_time': access_time.isoformat() if hasattr(access_time, 'isoformat') else str(access_time),
            'status': status
        }
        
        # Publica na cascata da Recepção (Broadcast para todos os computadores na catraca)
        redis_conn.publish(channel, json.dumps(payload))
        
        # Roteamento Inteligente P2P: Notifica APENAS o Master Owner (se for um alerta/métricas)
        master_id = get_master_owner_id(box_id)
        if master_id:
            owner_channel = f"owner_{master_id}_events"
            redis_conn.publish(owner_channel, json.dumps(payload))
            
    except Exception as e:
        logger.error(f"Falha ao propagar Evento de Check-in (PubSub): {e}")

