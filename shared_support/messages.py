import json
import os
from django.conf import settings

def load_microcopy():
    """
    Carrega o catalogo de mensagens didaticas (Microcopy) do OctoBox.
    """
    catalog_path = os.path.join(settings.BASE_DIR, 'load_tests', 'messages_pt_BR.json')
    try:
        with open(catalog_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

# Singleton-like access
MICROCOPY = load_microcopy()

def msg(key, fallback=None, **kwargs):
    """
    Recupera uma mensagem do catalogo injetando argumentos se necessário.
    """
    message = MICROCOPY.get(key) or fallback or key
    if message and kwargs:
        try:
            return str(message).format(**kwargs)
        except (KeyError, IndexError):
            pass
    return message
