# Curva: operação de notificações Web Push

## Estado em 13/10/2026

O PostgreSQL local recebeu as migrations até `public_workouts.0043`. O `.env` local, ignorado pelo Git, tem VAPID de desenvolvimento, hosts de push e `PUBLIC_WORKOUT_PUBLIC_BASE_URL=http://localhost:8000`; `public_workouts.push.configured()` retornou `True` na verificação anterior. Isso comprova somente configuração local, não entrega pública a um aparelho.

## Ativação pública

1. Guardar um par VAPID persistente no gestor de segredos do servidor. Usar `STUDENT_WEB_PUSH_VAPID_PUBLIC_KEY`, `STUDENT_WEB_PUSH_VAPID_PRIVATE_KEY` (PEM com `\n` entre linhas) e `STUDENT_WEB_PUSH_VAPID_CLAIMS_SUBJECT=mailto:...`. Trocar a chave depois de inscrições ativas exige nova inscrição dos dispositivos.
2. Definir `PUBLIC_WORKOUT_PUSH_ALLOWED_HOSTS` com os hosts de endpoint efetivamente observados nos navegadores suportados e `PUBLIC_WORKOUT_PUBLIC_BASE_URL=https://<domínio público>`. Não copiar a URL `localhost` do ambiente local.
3. Aplicar `python manage.py migrate_schemas --shared --noinput` e `python manage.py migrate_schemas --noinput`. Confirmar `public_workouts.0040` a `.0043` aplicadas.
4. Ativar o timer `octobox-public-workout-outbox.timer` por meio do instalador `scripts/linux/install_public_workout_operations_timers.sh`. Conferir `systemctl status` e logs da unidade antes de liberar a interface amplamente.
5. Num aparelho com o PWA instalado, entrar na conta correta, tocar **Ativar avisos**, aceitar a permissão e verificar a linha `PublicWorkoutPushSubscription` ativa. Drenar a outbox após publicar um programa de ensaio; conferir recebimento, clique para o mesmo domínio e desativação do dispositivo.

## Diagnóstico

- Botão ausente: verificar `configured()` e as quatro variáveis de operação; a interface mostra configuração pendente quando faltam.
- Inscrição rejeitada: conferir o host real do endpoint contra `PUBLIC_WORKOUT_PUSH_ALLOWED_HOSTS`. O servidor exige HTTPS e rejeita IP não público.
- Mensagem pendente: usar `python manage.py drain_public_workout_outbox --limit 50` uma vez para diagnosticar; conferir timer e `last_error` da inscrição. A transação do treino permanece concluída mesmo se a rede push falhar.
- Aparelho antigo após troca de VAPID: desativar avisos nele e ativar novamente; em implantação pública, planejar comunicação para nova inscrição.

Nunca registrar chave privada, subscription completa ou dados de treino nos logs de diagnóstico.
