# MIGRAÇÃO C (PENDENTE) do plano curva-grafico-hierarquia-e-set-role.md
# (Revisão 8, §7.12) -- torna `set_role` NOT NULL. Escrita a mão (não
# gerada por `makemigrations`, que é interativo pra este tipo de
# alteração) pra poder embutir o RunPython de guarda abaixo.
#
# POR QUE ESTE ARQUIVO NÃO ESTÁ EM public_workouts/migrations/:
# achado real via CI (PR #293): `migrate` sem alvo aplica TODAS as
# migrations pendentes, incluindo esta -- não rodar `migrate
# public_workouts 0033` deliberadamente NÃO é garantia nenhuma, é só
# disciplina de processo. A suíte de testes cria o banco do zero e roda
# `migrate` até o fim; um banco vazio passa qualquer cheque de "zero
# linha NULL" trivialmente, tornando a coluna NOT NULL cedo demais e
# quebrando testes que criam PublicWorkoutLoadLog sem set_role
# explícito. Uma segunda trava (variável de ambiente) dentro da própria
# migration NÃO resolve: se ela recusar aplicar (raise), `migrate`
# aborta o processo INTEIRO -- nenhum teste roda, pior que os 3 que
# quebravam antes. Django não tem "pular esta migration e continuar".
# A única forma segura de ter isto "escrito, pronto, mas não aplicado"
# é manter o arquivo FORA da pasta migrations/ até o momento certo.
#
# COMO ATIVAR (quando o backfill em produção confirmar zero NULL):
#   1. Confirmar o número da última migration em
#      public_workouts/migrations/ (na Revisão desta escrita, 0032 --
#      pode já ter mudado).
#   2. Copiar este arquivo pra
#      public_workouts/migrations/00XX_load_log_set_role_not_null.py
#      (XX = número seguinte).
#   3. Atualizar `dependencies` abaixo pro nome real da migration
#      anterior.
#   4. Remover `null=True` do campo `set_role` em
#      public_workouts/models.py e trocar a constraint
#      `public_workouts_loadlog_set_role_valid_or_null` por
#      `public_workouts_loadlog_set_role_valid` (sem o ramo
#      `set_role__isnull=True`) -- ver histórico desta mesma revisão
#      pra o texto exato dos dois.
#   5. Rodar `backfill_public_workout_load_log_set_role` em produção e
#      confirmar ZERO linha com set_role NULL.
#   6. Só ENTÃO, numa passada de deploy dedicada, com
#      OCTOBOX_APPLY_SET_ROLE_NOT_NULL_MIGRATION=1 no ambiente:
#      `python manage.py migrate public_workouts`.
#
# A variável de ambiente abaixo é defesa em profundidade (protege contra
# copiar o arquivo pra migrations/ cedo demais e rodar `migrate` sem
# querer) -- não substitui manter o arquivo fora da pasta até o passo 2.

import os

from django.db import migrations, models

_UNLOCK_ENV_VAR = 'OCTOBOX_APPLY_SET_ROLE_NOT_NULL_MIGRATION'


def _refuse_unless_unlocked_and_clean(apps, schema_editor):
    if os.environ.get(_UNLOCK_ENV_VAR) != '1':
        raise RuntimeError(
            f'Migration C bloqueada por padrao (mesmo em banco vazio) -- defina '
            f'{_UNLOCK_ENV_VAR}=1 no ambiente do deploy SOMENTE depois de rodar '
            'backfill_public_workout_load_log_set_role e confirmar ZERO linha com '
            'set_role NULL em produção (ver docs/plans/'
            'curva-grafico-hierarquia-e-set-role.md, §7.12).'
        )
    PublicWorkoutLoadLog = apps.get_model('public_workouts', 'PublicWorkoutLoadLog')
    remaining = PublicWorkoutLoadLog.objects.filter(set_role__isnull=True).count()
    if remaining:
        raise RuntimeError(
            f'Migration C recusada: {remaining} linha(s) de PublicWorkoutLoadLog ainda tem '
            'set_role NULL mesmo com a variável de ambiente definida. Rode o backfill de novo '
            'e confirme 0 antes de reaplicar esta migration.'
        )


def _noop_reverse(apps, schema_editor):
    # Reverter e' so' voltar a aceitar NULL (proxima operacao de baixo
    # cuida do ALTER COLUMN) -- nao ha NULL nenhum pra "recriar" aqui.
    pass


class Migration(migrations.Migration):

    dependencies = [
        # TODO na ativação (passo 3 acima): trocar pelo nome real da
        # última migration em public_workouts/migrations/ nesse momento.
        ('public_workouts', '0032_load_log_achievement'),
    ]

    operations = [
        migrations.RunPython(_refuse_unless_unlocked_and_clean, _noop_reverse),
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
