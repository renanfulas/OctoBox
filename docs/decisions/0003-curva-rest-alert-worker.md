<!-- ARQUIVO: lição 0003 — aviso do fim do descanso da Curva com worker próprio, não pela outbox. -->
# 0003 — Fim do descanso por push agendado: worker com advisory lock + LISTEN/NOTIFY

- **date:** 2026-10-16
- **area:** `public_workouts/rest_alerts.py`, `public_workouts/management/commands/run_public_workout_rest_alerts.py`, `infra/hostgator-vps/systemd/octobox-public-workout-rest-alerts.service`, `static/js/public_workouts/guided-rest-alert.js`, `templates/public_workouts/sw.js`
- **status:** active

## O que mudou
O modo foco da Curva agenda no servidor um push "Descanso acabou · <exercício>, série N" quando o descanso começa (`POST /renan/<slug>/push/descanso`, com `remaining_ms` relativo). "+30 s" reagenda, pular e encerrar cancelam (`DELETE`). Um worker de processo único (`run_public_workout_rest_alerts`, unit systemd `octobox-public-workout-rest-alerts.service`) dorme até o próximo aviso pendente e envia na hora. A tabela é `PublicWorkoutRestAlert`, um registro por sessão guiada (upsert).

## Por quê
- O iOS congela o PWA poucos segundos depois que ele sai da tela. O bipe e a vibração do app param ali. Com o app fechado ou a tela bloqueada, só um push vindo do servidor faz o aluno sentir o fim do descanso.
- A web não permite pedir "só vibrar": a notificação segue o modo do aparelho. No silencioso ela vibra; no modo normal toca o som padrão e vibra. O produto aceitou isso.
- A outbox (`drain_public_workout_outbox`, timer de 1 min) erraria um descanso de 60–90 s em até um minuto. Celery/Redis como broker seria uma peça nova só para isso. O worker usa só o Postgres que já existe.

## Como funciona
- **Um worker por banco:** `pg_try_advisory_lock` de sessão. Um segundo processo fica de reserva e assume se o primeiro cair (o lock some com a conexão).
- **Dormir até o horário:** espera no socket da conexão até `min(próximo due_at, max_idle)`. O agendamento faz `pg_notify` na mesma transação, entregue no COMMIT, e acorda o worker na hora. O psycopg 3.2 guarda NOTIFY recebidos fora da espera e os devolve primeiro, sem janela de corrida. `max_idle` (15 s) é só a rede de segurança.
- **Reivindicar sem duplicar:** `SELECT … FOR UPDATE SKIP LOCKED` passa a linha para `sending`, envia fora da transação e fecha com `UPDATE … WHERE revision = <reivindicada>`. Se o aluno der "+30 s" durante o envio, a revisão muda e o aviso novo continua pendente.
- **Não alertar tarde nem em dobro:** atraso acima de 30 s vence como `expired`, e o TTL do push também é 30 s. O app cancela o aviso a 4 s do fim se a tela estiver à vista, e toca o próprio bipe. Se a tela for bloqueada depois disso, reagenda com `keepalive`. O worker cancela o aviso de sessão já encerrada mesmo sem o `DELETE` do app.
- **Só o aparelho que treina:** o app manda o `endpoint` da própria inscrição. O servidor exige sessão `identity_verified`, inscrição ativa da mesma conta e sessão guiada ativa. Os outros aparelhos da conta não recebem.

## Lição / padrão reutilizável
1. **Para tarefa com hora marcada, use processo que dorme até o horário, não timer de varredura.** Advisory lock para instância única, LISTEN/NOTIFY para acordar e `SKIP LOCKED` com `revision` para reivindicar. Tudo isso sai do Postgres, sem broker.
2. **No iOS, todo push precisa mostrar notificação** (push sem notificação leva à revogação da inscrição). O service worker não pode suprimir o aviso quando o app está à vista. Quem evita o alerta duplo é o cliente, cancelando antes do envio.
3. **Prazo relativo, relógio do servidor:** o app manda "faltam N ms", não um horário absoluto. Isso evita erro de relógio do celular.
4. **Testar o NOTIFY exige commit:** o `TestCase` nunca comita, então o NOTIFY não é entregue. O teste usa threads com conexão própria (`public_workouts/test_curva_rest_alerts.py`). TransactionTestCase não serve, porque o flush não conhece os schemas de tenant.

## Limites conhecidos
- Envio em série: com muitos avisos no mesmo segundo, cada um espera o anterior (timeout de 5 s por envio). No volume atual da Curva isso é desprezível. Se crescer, o próximo passo é um pool pequeno de threads no `dispatch_due`.
- O som e a vibração no iPhone seguem o modo do aparelho. O padrão de `vibrate` só vale no Android.
