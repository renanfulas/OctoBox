"""
ARQUIVO: script para inspecionar o usuário de id 31 e salvar informações em arquivo.

POR QUE ELE EXISTE:
- Facilita a depuração e análise de permissões/grupos do usuário 31 no banco de dados.

O QUE ESTE ARQUIVO FAZ:
1. Busca o usuário de id 31.
2. Salva username e grupos em inspect_user31.txt.
3. Indica se o usuário não existe.

PONTOS CRÍTICOS:
- Mudanças podem afetar a análise de permissões e depuração de ambiente.
"""
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
