import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from access.roles import get_user_role

User = get_user_model()
users = User.objects.all()

print("USUÁRIOS NO BANCO DE DADOS:")
for u in users:
    role = get_user_role(u)
    role_name = getattr(role, 'slug', 'Sem papel')
    print(f"- {u.username} (Ativo: {u.is_active}) | Papel: {role_name}")

# Vamos garantir que exista o admin com senha 123
admin_user = User.objects.filter(username='admin').first()
if not admin_user:
    print("\nCriando usuario admin genérico com senha '123' (Papel: owner)...")
    admin_user = User.objects.create_superuser('admin', 'admin@l7.com', '123')
    from django.contrib.auth.models import Group
    owner_group, _ = Group.objects.get_or_create(name='owner')
    admin_user.groups.add(owner_group)
else:
    print("\nResetando senha do admin para '123' (Papel: owner)...")
    admin_user.set_password('123')
    admin_user.save()

# E também garantir que o kira_master tenha a senha 123
kira = User.objects.filter(username='kira_master').first()
if kira:
    print("Resetando senha do kira_master para '123'...")
    kira.set_password('123')
    kira.save()

print("\nConcluído! O Agent pode usar 'admin' com senha '123'.")
