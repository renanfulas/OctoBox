import json
import logging

from django.core.cache import cache

from shared_support.cascade.ownership import resolve_box_owner_user_id


logger = logging.getLogger('octobox.events')


def get_redis_client():
    from django_redis import get_redis_connection
    return get_redis_connection('default')


def get_master_owner_id(box_id):
    """
    Regra do OctoBox CS2: em boxes com multiplos socios, elege o owner mestre.
    Nesta fase, a resolucao oficial mora no corredor compartilhado da cascata.
    """
    return resolve_box_owner_user_id(box_id)


def publish_checkin_event(box_id, student_id, student_name, student_photo_url, access_time, status='ok'):
    """
    Dispara um push em Redis Pub/Sub. As abas de recepcao capturam isso via SSE.
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
            'status': status,
        }

        redis_conn.publish(channel, json.dumps(payload))

        master_id = get_master_owner_id(box_id)
        if master_id:
            owner_channel = f"owner_{master_id}_events"
            redis_conn.publish(owner_channel, json.dumps(payload))

    except Exception as exc:
        logger.error(f"Falha ao propagar evento de check-in (PubSub): {exc}")
