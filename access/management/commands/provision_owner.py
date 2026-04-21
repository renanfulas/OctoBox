"""
ARQUIVO: comando de provisionamento do Owner de um box.

POR QUE ELE EXISTE:
- Onboarding de novo cliente é um ato deliberado de infra, não um botão de UI.
- DEV não precisa de permissão de criação de usuário na interface — roda via SSH.

O QUE ESTE ARQUIVO FAZ:
1. Cria o usuário Owner com senha temporária gerada automaticamente.
2. Atribui o grupo Owner (criado pelo bootstrap_roles).
3. Imprime as credenciais iniciais no terminal para repasse seguro ao cliente.
4. É idempotente: se o usuário já existe, apenas garante o grupo e exibe aviso.

USO:
    python manage.py provision_owner --username=joao --email=joao@crossfitsul.com.br

    # Com nome completo opcional:
    python manage.py provision_owner --username=joao --email=joao@crossfitsul.com.br --name="João Silva"

PONTOS CRÍTICOS:
- Uma instância comporta no máximo 2 Owners enquanto o multitenancy não estiver aberto.
  Tentativas de criar um terceiro Owner são bloqueadas por padrão.
- A senha temporária aparece UMA VEZ no terminal. Guarde antes de fechar.
- O Owner deve trocar a senha no primeiro acesso via /accounts/password/change/.
- Rode bootstrap_roles antes se o grupo Owner ainda não existir.
"""

import secrets
import string

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

User = get_user_model()

_ALPHABET = string.ascii_letters + string.digits + "!@#$%&*"
_PASSWORD_LENGTH = 16


def _generate_temp_password() -> str:
    # Garante pelo menos um de cada classe para atender políticas de senha comuns.
    password = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.digits),
        secrets.choice("!@#$%&*"),
    ]
    password += [secrets.choice(_ALPHABET) for _ in range(_PASSWORD_LENGTH - 4)]
    secrets.SystemRandom().shuffle(password)
    return "".join(password)


class Command(BaseCommand):
    help = "Provisiona um usuário Owner para um novo box. Rode após bootstrap_roles."

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True, help="Username do Owner (sem espaços).")
        parser.add_argument("--email", required=True, help="E-mail do Owner.")
        parser.add_argument("--name", default="", help="Nome completo (opcional).")
        parser.add_argument(
            "--force",
            action="store_true",
            default=False,
            help="Ignora a trava de 2 Owners por instância. Use só em migração ou suporte explícito.",
        )

    def handle(self, *args, **options):
        username = options["username"].strip()
        email = options["email"].strip().lower()
        full_name = options["name"].strip()

        try:
            owner_group = Group.objects.get(name="Owner")
        except Group.DoesNotExist:
            raise CommandError(
                "Grupo 'Owner' não encontrado. Rode primeiro: python manage.py bootstrap_roles"
            )

        _MAX_OWNERS = 2

        if not options["force"]:
            existing_owners = User.objects.filter(groups=owner_group)
            count = existing_owners.count()
            if count >= _MAX_OWNERS:
                names = ", ".join(existing_owners.values_list("username", flat=True))
                raise CommandError(
                    f"Esta instância já possui {count} Owner(s): {names}\n"
                    f"O limite é {_MAX_OWNERS} Owners por box enquanto o multitenancy "
                    "não estiver habilitado.\n"
                    "Use --force somente em migração de dados ou suporte explícito."
                )

        existing = User.objects.filter(username=username).first()
        if existing:
            self._handle_existing(existing, owner_group)
            return

        temp_password = _generate_temp_password()

        first_name = ""
        last_name = ""
        if full_name:
            parts = full_name.split(" ", 1)
            first_name = parts[0]
            last_name = parts[1] if len(parts) > 1 else ""

        with transaction.atomic():
            user = User.objects.create_user(
                username=username,
                email=email,
                password=temp_password,
                first_name=first_name,
                last_name=last_name,
                is_active=True,
            )
            user.groups.add(owner_group)

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 52))
        self.stdout.write(self.style.SUCCESS("  Owner provisionado com sucesso"))
        self.stdout.write(self.style.SUCCESS("=" * 52))
        self.stdout.write(f"  Usuário : {username}")
        self.stdout.write(f"  E-mail  : {email}")
        if full_name:
            self.stdout.write(f"  Nome    : {full_name}")
        self.stdout.write(f"  Papel   : Owner")
        self.stdout.write("")
        self.stdout.write(self.style.WARNING("  SENHA TEMPORÁRIA (anote agora):"))
        self.stdout.write(self.style.WARNING(f"  {temp_password}"))
        self.stdout.write("")
        self.stdout.write("  O Owner deve trocar a senha no primeiro acesso:")
        self.stdout.write("  /accounts/password/change/")
        self.stdout.write(self.style.SUCCESS("=" * 52))
        self.stdout.write("")

    def _handle_existing(self, user: "User", owner_group: Group) -> None:
        already_owner = user.groups.filter(name="Owner").exists()
        if not already_owner:
            user.groups.add(owner_group)
            self.stdout.write(self.style.WARNING(
                f"Usuário '{user.username}' já existia — grupo Owner adicionado."
            ))
        else:
            self.stdout.write(self.style.WARNING(
                f"Usuário '{user.username}' já existe e já é Owner. Nenhuma alteração feita."
            ))
        self.stdout.write("Para redefinir a senha: python manage.py changepassword " + user.username)
