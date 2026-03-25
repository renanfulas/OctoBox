import os
from celery import Celery

# Ajuste: defina DJANGO_SETTINGS_MODULE antes de executar o worker
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('django_import_example')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
