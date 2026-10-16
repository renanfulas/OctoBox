# Curva: operação de notificações Web Push

## Estado verificado em 14/10/2026

O PR #322 foi publicado em `https://app.octoboxfit.com.br` no commit `1a7b7f05d21bbb0af7538e143d6733672a886bae`. O health endpoint confirmou esse SHA; `/renan/sw.js` contém os listeners `push` e `notificationclick`; as migrations `public_workouts.0040` a `.0043` estão aplicadas. O timer `octobox-public-workout-outbox.timer` está ativo.

O ambiente público tem VAPID persistente, `PUBLIC_WORKOUT_PUBLIC_BASE_URL` em HTTPS e `PUBLIC_WORKOUT_PUSH_ALLOWED_HOSTS` para Apple e FCM. A chave privada foi normalizada para um único bloco PEM válido, sem trocar o par. `public_workouts.push.configured()` retornou `True`. O PR #327 (`15f83a21e4dcef5b1040535b06c6c3365c3a7bb2`) levou os controles de instalação e avisos para **Perfil** após a ativação; o convite inicial continua em **Início** enquanto a ação ainda cabe ao aluno.

Uma conta de ensaio com plano próprio inscreveu um iPhone instalado. O envio isolado para essa inscrição foi aceito pelo gateway, e a destinatária confirmou o recebimento no aparelho. Essa foi a primeira comprovação de inscrição e entrega direta; a validação posterior do fluxo automático está registrada abaixo. Não confundir o recibo do gateway com exibição no dispositivo: a confirmação da destinatária é a evidência desta entrega.

## Homologação real em 15/10/2026

No plano de ensaio `giovanna`, a sessão de quinta-feira foi concluída com **seis séries realizadas em seis exercícios**. O registro `PublicWorkoutTrainingSession` tem `outcome=completed` e `completed_at`; a linha do analytics mostra **Concluído** e seis séries. A outbox criou uma única mensagem `training_completed`, processada como `sent` na primeira tentativa e sem erro. O gateway aceitou o envio para as duas inscrições ativas dessa conta; isso não permite afirmar que são dois aparelhos físicos distintos.

A destinatária confirmou que o aviso automático **Treino concluído** apareceu na Central de Notificações do iPhone e que tocar nele abriu o Curva no plano `giovanna`. Ela também confirmou que o aviso **Avisos ativados** chegou após a inscrição mais recente. Um único envio de diagnóstico para essa inscrição, com o iPhone bloqueado, apareceu na tela bloqueada. Assim, criação do fato de treino, analytics, outbox, gateway, exibição e abertura do aviso automático estão homologados nesse iPhone.

O aviso automático não foi percebido como banner no momento da chegada, embora a entrega imediata e os banners estivessem ativados e não houvesse Foco declarado. Ele estava na Central, e o aviso de diagnóstico posterior apareceu na tela bloqueada. O motivo dessa diferença de apresentação permanece **não determinado**; não tratar a ausência de banner, isoladamente, como falha de entrega. Android e o ciclo completo de desativação/reativação ainda precisam de ensaio próprio.

## Ativação pública

1. Guardar um par VAPID persistente no gestor de segredos do servidor. Usar `STUDENT_WEB_PUSH_VAPID_PUBLIC_KEY`, `STUDENT_WEB_PUSH_VAPID_PRIVATE_KEY` (PEM com `\n` entre linhas) e `STUDENT_WEB_PUSH_VAPID_CLAIMS_SUBJECT=mailto:...`. Trocar a chave depois de inscrições ativas exige nova inscrição dos dispositivos.
2. Definir `PUBLIC_WORKOUT_PUSH_ALLOWED_HOSTS` com os hosts de endpoint efetivamente observados nos navegadores suportados e `PUBLIC_WORKOUT_PUBLIC_BASE_URL=https://<domínio público>`. Não copiar a URL `localhost` do ambiente local.
3. Aplicar `python manage.py migrate_schemas --shared --noinput` e `python manage.py migrate_schemas --noinput`. Confirmar `public_workouts.0040` a `.0043` aplicadas.
4. Ativar o timer `octobox-public-workout-outbox.timer` por meio do instalador `scripts/linux/install_public_workout_operations_timers.sh`. Conferir `systemctl status` e logs da unidade antes de liberar a interface amplamente.
5. Num aparelho com o PWA instalado, entrar na conta correta, tocar **Ativar avisos** em **Início**, aceitar a permissão e verificar a linha `PublicWorkoutPushSubscription` ativa. Após ativar, consultar e desativar avisos em **Perfil → Aplicativo**. Drenar a outbox após publicar um programa de ensaio; conferir recebimento, clique para o mesmo domínio e desativação do dispositivo.

## Homologação isolada no iPhone

1. Confirmar que a conta de ensaio tem assinatura `active` com `plan_slug` próprio e programa publicado. A tela `/renan/<slug>` deve ser desse mesmo plano. Confirmar em HTTP que `/renan/sw.js` contém os listeners `push` e `notificationclick`, e que essa conta, após login confirmado, vê o botão **Ativar avisos**. A posse de um link legado não basta para inscrever um dispositivo (PR #325). Confirmar HTTPS e `PUBLIC_WORKOUT_PUBLIC_BASE_URL` do mesmo domínio.
2. No iPhone, abrir o Curva instalado na tela de início, entrar na conta de ensaio e tocar **Ativar avisos**. Aceitar a permissão. Não compartilhar endpoint, chaves do dispositivo nem token de login em capturas ou tickets.
3. No servidor, verificar apenas os indicadores da conta de ensaio: uma inscrição ativa com `revoked_at` vazio, mensagem `push_welcome` em estado `sent`, `last_push_sent_at` preenchido e `last_error` vazio. O aviso **Avisos ativados** deve aparecer no aparelho; tocar nele deve abrir o mesmo domínio.
4. Registrar uma sessão de ensaio e concluir as séries mínimas. Conferir o fato `PublicWorkoutTrainingSession.outcome=completed`, `completed_at`, a contagem de `PublicWorkoutTrainingSet(status=performed)`, uma única mensagem `training_completed` enviada e o aviso no iPhone. Repetir o comando de conclusão para provar idempotência sem duplicar a sessão nem o aviso.
   Em exercícios livres, a conclusão exige ao menos uma série realizada **em cada exercício**. “Encerrar como parcial” grava `outcome=partial` no analytics e não cria `training_completed`; conferir essa distinção antes de diagnosticar uma falha de push. Se o aluno afirma ter feito mais séries do que o servidor registrou, investigar a fila local e a sincronização no aparelho antes de repetir o teste.
5. Desativar os avisos em **Perfil → Aplicativo**. Confirmar `revoked_at` na inscrição e que o controle volta para **Ativar avisos** no perfil. Reativar e verificar nova inscrição funcional antes de encerrar o ensaio.

Se qualquer etapa falhar, manter o resultado como **não homologado** e anotar o primeiro ponto de divergência (interface, permissão, inscrição, outbox, gateway ou exibição no iPhone). A outbox agora retém mensagens quando a configuração de push está ausente no momento do envio; conferir `last_error` e a cadência de retry antes de reenviar.

## Diagnóstico

- Botão ausente: conferir a conta logada e a aba **Perfil → Aplicativo** quando os avisos já estiverem ativos. O convite em **Início** desaparece após a ativação. Ele só aparece em `/renan/<slug>` quando a conta tem uma assinatura daquele plano; sem isso, o acesso pode levar a login, pagamento pendente ou 404. Após o PR #325, a posse do link legado mostra **Entrar para ativar**, e só o login confirmado mostra **Ativar avisos**. Depois verificar `configured()` e as quatro variáveis de operação: com conta proprietária e configuração incompleta, o cartão mostra a pendência, mas não o botão. Se o HTML tem o botão e ele some no iPhone, verificar suporte a `PushManager`/`Notification` e o estado de permissão no JavaScript.
- Inscrição rejeitada: conferir o host real do endpoint contra `PUBLIC_WORKOUT_PUSH_ALLOWED_HOSTS`. O servidor exige HTTPS e rejeita IP não público.
- Mensagem pendente: usar `python manage.py drain_public_workout_outbox --limit 50` uma vez para diagnosticar; conferir timer e `last_error` da inscrição. A transação do treino permanece concluída mesmo se a rede push falhar.
- Aparelho antigo após troca de VAPID: desativar avisos nele e ativar novamente; em implantação pública, planejar comunicação para nova inscrição.

Nunca registrar chave privada, subscription completa ou dados de treino nos logs de diagnóstico.
