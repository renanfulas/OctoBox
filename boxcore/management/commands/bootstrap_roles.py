"""
ARQUIVO: comando interno para criar grupos e permissões dos papéis.

POR QUE ELE EXISTE:
- Automatiza a preparação de Owner, DEV, Manager e Coach no banco.

O QUE ESTE ARQUIVO FAZ:
1. Lê o mapa de permissões por papel.
2. Cria os grupos se não existirem.
3. Vincula permissões corretas a cada grupo.

PONTOS CRITICOS:
- Mudanças aqui afetam segurança e escopo real de acesso do sistema.
- Uma permissão errada pode liberar ou bloquear áreas de negócio sem perceber.
"""

from django.apps import apps
from django.contrib.auth import get_permission_codename
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand

from access.roles import ROLE_PERMISSION_MAP


class Command(BaseCommand):
    help = 'Cria os grupos Owner, DEV, Manager, Recepcao e Coach com permissões iniciais do projeto.'

    def handle(self, *args, **options):
        model_index = {model._meta.model_name: model for model in apps.get_models()}

        for role_name, permission_map in ROLE_PERMISSION_MAP.items():
            group, _ = Group.objects.get_or_create(name=role_name)
            permissions = []

            for model_name, actions in permission_map.items():
                model = model_index[model_name]
                content_type = ContentType.objects.get_for_model(model)
                permissions_for_model = []
                for action in actions:
                    codename = get_permission_codename(action, model._meta)
                    permission, _ = Permission.objects.get_or_create(
                        content_type=content_type,
                        codename=codename,
                        defaults={
                            'name': f'Can {action} {model._meta.verbose_name_raw}',
                        },
                    )
                    permissions_for_model.append(permission)

                # O vínculo permission -> content_type garante que cada papel receba acesso ao modelo correto.
                # O get_or_create torna o bootstrap autocorretivo quando um flush parcial ou uma
                # migração interrompida deixa permissões padrão ausentes.
                permissions.extend(permissions_for_model)

            # set substitui permissões antigas e mantém o grupo sincronizado com a definição atual.
            group.permissions.set(permissions)
            self.stdout.write(self.style.SUCCESS(f'Grupo preparado: {role_name}'))

        self.stdout.write(self.style.SUCCESS('Papéis do sistema configurados com sucesso.'))
