"""
ARQUIVO: migration 0004 de ampliacao do perfil do aluno.

POR QUE ELE EXISTE:
- adapta o cadastro de alunos ao modelo operacional atual com dados mais uteis para atendimento.

O QUE ESTE ARQUIVO FAZ:
1. adiciona campos de cpf, genero e status de questao de saude.
2. ajusta o telefone principal para refletir o uso como WhatsApp.
3. remove campos antigos que deixaram de fazer parte do fluxo.

PONTOS CRITICOS:
- remocoes e renomeacoes implicitas em migrations antigas podem impactar restauracoes e comparacoes de schema.
- qualquer alteracao aqui precisa respeitar a sequencia historica de migracao.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('boxcore', '0003_auditevent'),
    ]

    operations = [
        migrations.AddField(
            model_name='student',
            name='cpf',
            field=models.CharField(blank=True, max_length=14),
        ),
        migrations.AddField(
            model_name='student',
            name='gender',
            field=models.CharField(blank=True, choices=[('male', 'Masculino'), ('female', 'Feminino')], max_length=16),
        ),
        migrations.AddField(
            model_name='student',
            name='health_issue_status',
            field=models.CharField(blank=True, choices=[('yes', 'Sim'), ('no', 'Nao')], max_length=8),
        ),
        migrations.AlterField(
            model_name='student',
            name='phone',
            field=models.CharField(max_length=20, unique=True, verbose_name='WhatsApp'),
        ),
        migrations.RemoveField(
            model_name='student',
            name='emergency_contact',
        ),
        migrations.RemoveField(
            model_name='student',
            name='source',
        ),
        migrations.RemoveField(
            model_name='student',
            name='whatsapp_verified',
        ),
    ]