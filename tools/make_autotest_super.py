"""
ARQUIVO: script para promover usuário autotest a superuser/staff.

POR QUE ELE EXISTE:
- Facilita a configuração do ambiente de testes automatizados, garantindo permissões elevadas ao usuário autotest.

O QUE ESTE ARQUIVO FAZ:
1. Busca o usuário autotest no banco de dados.
2. Define os flags is_staff e is_superuser como True.
3. Salva as alterações e exibe mensagem de sucesso ou erro.

PONTOS CRÍTICOS:
- Mudanças podem afetar a execução de testes automatizados e permissões do ambiente de CI.
"""
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
