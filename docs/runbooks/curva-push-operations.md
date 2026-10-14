# Curva: operação de notificações Web Push

## Estado em 13/10/2026

O PostgreSQL local recebeu as migrations até `public_workouts.0043`. O `.env` local, ignorado pelo Git, tem VAPID de desenvolvimento, hosts de push e `PUBLIC_WORKOUT_PUBLIC_BASE_URL=http://localhost:8000`; `public_workouts.push.configured()` retornou `True` na verificação anterior. Isso comprova somente configuração local, não entrega pública a um aparelho.

Na verificação pública de 13/10/2026, `https://app.octoboxfit.com.br/renan/bruno` ainda não servia o guia nem o controle de push e `/renan/sw.js` não tinha listener `push`. O código está no PR #322 e a homologação física depende de sua publicação. Não usar um resultado de teste local como confirmação de entrega no iPhone.

## Ativação pública

1. Guardar um par VAPID persistente no gestor de segredos do servidor. Usar `STUDENT_WEB_PUSH_VAPID_PUBLIC_KEY`, `STUDENT_WEB_PUSH_VAPID_PRIVATE_KEY` (PEM com `\n` entre linhas) e `STUDENT_WEB_PUSH_VAPID_CLAIMS_SUBJECT=mailto:...`. Trocar a chave depois de inscrições ativas exige nova inscrição dos dispositivos.
2. Definir `PUBLIC_WORKOUT_PUSH_ALLOWED_HOSTS` com os hosts de endpoint efetivamente observados nos navegadores suportados e `PUBLIC_WORKOUT_PUBLIC_BASE_URL=https://<domínio público>`. Não copiar a URL `localhost` do ambiente local.
3. Aplicar `python manage.py migrate_schemas --shared --noinput` e `python manage.py migrate_schemas --noinput`. Confirmar `public_workouts.0040` a `.0043` aplicadas.
4. Ativar o timer `octobox-public-workout-outbox.timer` por meio do instalador `scripts/linux/install_public_workout_operations_timers.sh`. Conferir `systemctl status` e logs da unidade antes de liberar a interface amplamente.
5. Num aparelho com o PWA instalado, entrar na conta correta, tocar **Ativar avisos**, aceitar a permissão e verificar a linha `PublicWorkoutPushSubscription` ativa. Drenar a outbox após publicar um programa de ensaio; conferir recebimento, clique para o mesmo domínio e desativação do dispositivo.

## Homologação isolada no iPhone

1. Após o deploy, confirmar em HTTP que `/renan/sw.js` contém os listeners `push` e `notificationclick`, e que a conta de ensaio autenticada vê o botão **Ativar avisos**. Confirmar HTTPS e `PUBLIC_WORKOUT_PUBLIC_BASE_URL` do mesmo domínio.
2. No iPhone, abrir o Curva instalado na tela de início, entrar na conta de ensaio e tocar **Ativar avisos**. Aceitar a permissão. Não compartilhar endpoint, chaves do dispositivo nem token de login em capturas ou tickets.
3. No servidor, verificar apenas os indicadores da conta de ensaio: uma inscrição ativa com `revoked_at` vazio, mensagem `push_welcome` em estado `sent`, `last_push_sent_at` preenchido e `last_error` vazio. O aviso **Avisos ativados** deve aparecer no aparelho; tocar nele deve abrir o mesmo domínio.
4. Registrar uma sessão de ensaio e concluir as séries mínimas. Conferir o fato `PublicWorkoutTrainingSession.outcome=completed`, `completed_at`, a contagem de `PublicWorkoutTrainingSet(status=performed)`, uma única mensagem `training_completed` enviada e o aviso no iPhone. Repetir o comando de conclusão para provar idempotência sem duplicar a sessão nem o aviso.
5. Desativar os avisos no aparelho. Confirmar `revoked_at` na inscrição e que o botão volta para **Ativar avisos**. Reativar e verificar nova inscrição funcional antes de encerrar o ensaio.

Se qualquer etapa falhar, manter o resultado como **não homologado** e anotar o primeiro ponto de divergência (interface, permissão, inscrição, outbox, gateway ou exibição no iPhone). A outbox agora retém mensagens quando a configuração de push está ausente no momento do envio; conferir `last_error` e a cadência de retry antes de reenviar.

## Diagnóstico

- Botão ausente: verificar `configured()` e as quatro variáveis de operação; a interface mostra configuração pendente quando faltam.
- Inscrição rejeitada: conferir o host real do endpoint contra `PUBLIC_WORKOUT_PUSH_ALLOWED_HOSTS`. O servidor exige HTTPS e rejeita IP não público.
- Mensagem pendente: usar `python manage.py drain_public_workout_outbox --limit 50` uma vez para diagnosticar; conferir timer e `last_error` da inscrição. A transação do treino permanece concluída mesmo se a rede push falhar.
- Aparelho antigo após troca de VAPID: desativar avisos nele e ativar novamente; em implantação pública, planejar comunicação para nova inscrição.

Nunca registrar chave privada, subscription completa ou dados de treino nos logs de diagnóstico.
