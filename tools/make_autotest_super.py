import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
django.setup()
from django.contrib.auth import get_user_model
User = get_user_model()
try:
    u = User.objects.get(username='autotest')
    u.is_staff = True
    u.is_superuser = True
    u.save()
    print('autotest promoted to staff/superuser')
except Exception as e:
    print('error:', e)
