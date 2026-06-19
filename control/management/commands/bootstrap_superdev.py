"""
ARQUIVO: comando que garante a conta unica de suporte (superdev).

POR QUE ELE EXISTE:
- Todo box provisionado anexa o superdev (control.services._attach_support_membership).
  A conta precisa existir em public; este comando a cria/garante idempotentemente.

O QUE ESTE ARQUIVO FAZ:
1. Cria (ou garante) o User superdev resolvido por SUPERDEV_USERNAME/SUPERDEV_EMAIL.
2. Garante is_staff=is_superuser=is_active=True.
3. Define a senha a partir de SUPERDEV_PASSWORD (env). Sem ela, deixa a senha
   inutilizavel e avisa para configurar via SSO ou `manage.py changepassword`.

USO:
    python manage.py bootstrap_superdev
    SUPERDEV_PASSWORD=... python manage.py bootstrap_superdev   # define a senha

PONTOS CRITICOS:
- Idempotente: rodar 2x nao duplica nem reseta a senha (a menos que SUPERDEV_PASSWORD
  esteja setada).
- A conta tem acesso OWNER a TODOS os boxes — proteja a senha (raio de explosao alto).
"""

import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

User = get_user_model()


class Command(BaseCommand):
    help = 'Garante a conta unica de suporte (superdev) usada no provisionamento de boxes.'

    def handle(self, *args, **options):
        username = (getattr(settings, 'SUPERDEV_USERNAME', '') or '').strip()
        email = (getattr(settings, 'SUPERDEV_EMAIL', '') or '').strip().lower()
        if not username:
            self.stderr.write('SUPERDEV_USERNAME nao configurado. Defina no .env/settings.')
            return

        raw_password = os.environ.get('SUPERDEV_PASSWORD', '')

        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': email,
                'is_staff': True,
                'is_superuser': True,
                'is_active': True,
                'first_name': 'OctoBox',
                'last_name': 'Suporte',
            },
        )

        changed = []
        if not created:
            if email and user.email != email:
                user.email = email
                changed.append('email')
            for flag in ('is_staff', 'is_superuser', 'is_active'):
                if not getattr(user, flag):
                    setattr(user, flag, True)
                    changed.append(flag)

        if raw_password:
            user.set_password(raw_password)
            changed.append('password')
        elif created:
            # Conta nova sem senha fornecida: deixa explicitamente inutilizavel.
            user.set_unusable_password()
            changed.append('password')

        if created or changed:
            user.save()

        if created:
            self.stdout.write(self.style.SUCCESS(f'Superdev "{username}" criado.'))
        elif changed:
            self.stdout.write(self.style.WARNING(
                f'Superdev "{username}" ja existia — atualizado: {", ".join(sorted(set(changed)))}.'
            ))
        else:
            self.stdout.write(f'Superdev "{username}" ja estava ok. Nenhuma alteracao.')

        if not raw_password and not user.has_usable_password():
            self.stdout.write(self.style.WARNING(
                'Conta SEM senha utilizavel. Defina via SSO ou '
                f'`python manage.py changepassword {username}` '
                '(ou rode de novo com SUPERDEV_PASSWORD=...).'
            ))
