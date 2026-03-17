import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
django.setup()
from django.contrib.auth import get_user_model
User = get_user_model()
u = User.objects.filter(pk=31).first()
with open('inspect_user31.txt', 'w', encoding='utf-8') as f:
    if not u:
        f.write('no-user')
    else:
        f.write('username=' + str(u.username) + '\n')
        f.write('groups=' + ','.join(list(u.groups.values_list('name', flat=True))) + '\n')
print('wrote inspect_user31.txt')
