# Migration C do plano curva-grafico-hierarquia-e-set-role.md (Revisao 8,
# §7.12) -- torna `set_role` NOT NULL. Escrita a mao (nao gerada por
# `makemigrations`, que e' interativo pra este tipo de alteracao) pra
# poder embutir o RunPython de guarda abaixo.
#
# DEPLOY -- LER ANTES DE RODAR `migrate`:
# Esta migration tem que ser aplicada numa passada de `migrate` SEPARADA
# de 0028-0032, nunca no mesmo deploy que introduz o campo. Sequencia
# correta:
#   1. Deploy de 0028-0032 (campo nullable) + codigo que ja escreve
#      set_role sempre (record_load/correct_load/PublicWorkoutRecordLoadView).
#   2. Rodar o management command
#      backfill_public_workout_load_log_set_role em produção e confirmar
#      ZERO linha com set_role NULL.
#   3. So' ENTAO `python manage.py migrate public_workouts 0033`.
#
# Esta migration nao confia so' em alguem seguir os 3 passos acima: o
# RunPython abaixo recusa aplicar (levanta RuntimeError, a migration
# inteira faz rollback, incluindo o ALTER COLUMN) se encontrar QUALQUER
# linha com set_role NULL no momento em que `migrate` roda de verdade --
# a confirmacao do passo 2 fica garantida pelo codigo, nao so' pelo
# processo.

from django.db import migrations, models


def _refuse_if_any_null_set_role(apps, schema_editor):
    PublicWorkoutLoadLog = apps.get_model('public_workouts', 'PublicWorkoutLoadLog')
    remaining = PublicWorkoutLoadLog.objects.filter(set_role__isnull=True).count()
    if remaining:
        raise RuntimeError(
            f'Migration C recusada: {remaining} linha(s) de PublicWorkoutLoadLog ainda tem '
            'set_role NULL. Rode o management command '
            'backfill_public_workout_load_log_set_role e confirme 0 antes de reaplicar esta '
            'migration (ver docs/plans/curva-grafico-hierarquia-e-set-role.md, §7.12).'
        )


def _noop_reverse(apps, schema_editor):
    # Reverter e' so' voltar a aceitar NULL (proxima operacao de baixo
    # cuida do ALTER COLUMN) -- nao ha NULL nenhum pra "recriar" aqui.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('public_workouts', '0032_load_log_achievement'),
    ]

    operations = [
        migrations.RunPython(_refuse_if_any_null_set_role, _noop_reverse),
        migrations.RemoveConstraint(
            model_name='publicworkoutloadlog',
            name='public_workouts_loadlog_set_role_valid_or_null',
        ),
        migrations.AlterField(
            model_name='publicworkoutloadlog',
            name='set_role',
            field=models.CharField(choices=[('warmup', 'Aquecimento'), ('feeder', 'Aproximação'), ('top_set', 'Série principal'), ('max_set', 'Esforço máximo'), ('legacy_unknown', 'Histórico anterior (não classificado)')], max_length=16),
        ),
        migrations.AddConstraint(
            model_name='publicworkoutloadlog',
            constraint=models.CheckConstraint(condition=models.Q(('set_role__in', ['warmup', 'feeder', 'top_set', 'max_set', 'legacy_unknown'])), name='public_workouts_loadlog_set_role_valid'),
        ),
    ]
