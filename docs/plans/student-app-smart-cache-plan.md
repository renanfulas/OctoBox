<!--
ARQUIVO: plano de cache inteligente do app do aluno.

POR QUE ELE EXISTE:
- Define como acelerar Home, Agenda, WOD e RM do app do aluno sem misturar dados entre alunos.
- Separa cache compartilhado por box de cache personalizado por aluno.

O QUE ESTE ARQUIVO FAZ:
1. Registra a verdade atual observada no runtime.
2. Define os snapshots que podem nascer com baixo risco.
3. Define eventos de invalidacao, chaves, TTLs e guardrails de SQL.
4. Organiza a implementacao em fases pequenas e testaveis.

PONTOS CRITICOS:
- Cache nao deve virar fonte de verdade transacional.
- Reservas, cancelamentos e RM do aluno precisam invalidar ou recompor a leitura personalizada.
- O isolamento por box precisa permanecer no prefixo das chaves.
-->

# Plano de cache inteligente do app do aluno

## Leitura executiva

O app do aluno deve usar cache por snapshot de leitura, nao cache bruto de HTML.

O melhor primeiro movimento e separar o que e igual para todos os alunos do box do que e pessoal de cada aluno:

1. compartilhado por box: grade dos proximos dias, capacidade das aulas, WOD publicado e blocos do treino.
2. personalizado por aluno: reserva ativa, status da reserva por aula, plano ativo, progresso semanal e RMs.

Em linguagem simples: a grade da academia e como o cardapio na parede. Todo mundo pode olhar o mesmo cardapio. Ja a sua reserva e o seu RM sao como o seu prato e sua ficha pessoal. Nao podem ser servidos de uma panela compartilhada sem conferir o nome.

## Evidencia do runtime atual

Leitura medida localmente em `127.0.0.1:8005` com uma identidade real do aluno:

1. `GetStudentDashboard.execute(...)`: 13 a 14 queries no cenario local.
2. `GetStudentWorkoutDay.execute(...)`: 4 queries no cenario local.
3. A Home reconstruiu sessao, presencas, WOD publicado, matricula, RM do dia e progresso semanal no mesmo request.
4. O projeto ja tem cache `default` com Redis em homologacao/producao e fallback `LocMemCache` local.
5. O prefixo de cache ja passa por `shared_support.box_runtime.build_box_cache_key_prefix(...)`, preservando namespace por box runtime.

## Verdade atual do banco e ownership

### Persistido hoje

1. `ClassSession` preserva estado historico em `boxcore`, com ownership de codigo em `operations`.
2. `Attendance` tambem preserva estado historico em `boxcore`.
3. `SessionWorkout`, `SessionWorkoutBlock`, `SessionWorkoutMovement`, `StudentExerciseMax` e leituras de WOD/RM moram em `student_app`.
4. `SessionWorkout.session` e `OneToOneField`, entao a busca de WOD por sessao ja tem uma chave forte.
5. `Attendance` tem unicidade por `(student, session)`, que protege uma reserva duplicada do mesmo aluno na mesma aula.

### Risco SQL atual

1. `ClassSession` e consultada repetidamente por `status` e janela de `scheduled_at`, mas o model nao declara indice composto para esse padrao.
2. A Home faz consultas separadas para inscricao ativa e ultima inscricao do aluno.
3. A montagem do RM do dia pode procurar RM e historico por movimento; com WODs maiores, isso pode crescer para N+1 se nao for agrupado.

## Objetivo tecnico

Alvo inicial de performance:

1. Home do aluno: sair de 13-14 queries para 5-7 queries no primeiro cache hit.
2. WOD do dia: sair de 4 queries para 1-2 queries no cache hit.
3. P95 local/homologacao percebido: reduzir a montagem de tela em 40% a 70% nos hits quentes.
4. Manter consistencia forte para escrita de reserva, cancelamento e RM.

## Arquitetura proposta

### Camada 1: indices antes do cache

Adicionar indice composto para a query quente de agenda:

1. `ClassSession(status, scheduled_at)`.

Motivo:

1. A Home filtra `status__in=['scheduled', 'open']` e faixa de `scheduled_at`.
2. Sem esse indice, o cache mascara o custo em hit, mas o miss continua caro conforme a base cresce.

Opcional depois de medir:

1. `SessionWorkout(status, session)` se o PostgreSQL mostrar custo alto em listas maiores.
2. `Attendance(student, status)` se a busca de reserva ativa crescer em boxes com muito historico por aluno.

### Camada 2: snapshot compartilhado de agenda por box

Novo snapshot sugerido:

`student_app:agenda:v1:{box_slug}:{start_date}:{window_days}`

Conteudo:

1. sessoes futuras visiveis.
2. coach display name.
3. capacidade total.
4. ocupacao por status ativo.
5. titulo dos WODs publicados por sessao.
6. runtime status basico da aula.

TTL:

1. 60 a 180 segundos com jitter.
2. Invalidacao por evento quando aula, presenca ou WOD mudar.

Por que pode ser compartilhado:

1. Agenda, horario, coach, capacidade e WOD publicado sao iguais para alunos do mesmo box.

O que nao entra:

1. status da reserva do aluno.
2. regra de bloqueio por plano.
3. progresso semanal do aluno.
4. RM do aluno.

### Camada 3: envelope personalizado da Home

Novo snapshot leve sugerido:

`student_app:home:v1:{box_slug}:student:{student_id}:{selected_date}:{window_days}`

Conteudo:

1. id da reserva ativa futura.
2. attendance por sessao do radar atual.
3. membership label e estado de plano.
4. progress days.
5. rm_of_the_day.
6. focal_session resolvida.

TTL:

1. 20 a 45 segundos com jitter.
2. Invalidacao imediata em reserva, cancelamento, check-in, check-out, update de RM, update de matricula e troca de box ativo.

Regra:

1. Este cache pode recompor em cima do snapshot compartilhado de agenda.
2. Nunca deve ser usado para autorizar uma reserva; a escrita continua no workflow transacional.

### Camada 4: snapshot do WOD publicado

Novo snapshot sugerido:

`student_app:wod:v1:{box_slug}:session:{session_id}:version:{workout_version}`

Conteudo:

1. titulo do WOD.
2. notas do coach.
3. blocos ordenados.
4. movimentos ordenados.
5. carga prescrita, tipo de carga e percentual.

TTL:

1. 6 a 24 horas com invalidacao por versao.
2. A chave inclui `workout.version`, entao edicoes de WOD quebram naturalmente a chave antiga.

Personalizacao fora do snapshot:

1. recomendacao de carga calculada com RM do aluno.
2. preview de RM.
3. tracking de visualizacao.

### Camada 5: snapshot de RM do aluno

Novo snapshot sugerido:

`student_app:rm:v1:{box_slug}:student:{student_id}`

Conteudo:

1. lista de RMs por movimento.
2. mapa `exercise_slug -> one_rep_max_kg`.
3. delta recente por movimento.

TTL:

1. 5 a 15 minutos com invalidacao imediata em criar/editar RM.

Uso:

1. Calculo de recomendacao do WOD.
2. Tela de RM.
3. Fallback rapido para formularios de percentual.

## Invalidacao por evento

Eventos que limpam agenda compartilhada:

1. criar, editar ou deletar `ClassSession`.
2. criar, cancelar, check-in ou check-out em `Attendance`.
3. publicar, rejeitar, editar, duplicar ou remover `SessionWorkout`.
4. criar, editar ou deletar bloco/movimento de WOD.

Eventos que limpam Home personalizada:

1. qualquer mudanca em `Attendance` do aluno.
2. qualquer mudanca em `Enrollment` do aluno.
3. qualquer mudanca em `StudentExerciseMax` do aluno.
4. troca de box ativo ou membership.
5. registro de atividade que afeta progresso semanal.

Eventos que limpam WOD:

1. alteracao em `SessionWorkout`.
2. alteracao em `SessionWorkoutBlock`.
3. alteracao em `SessionWorkoutMovement`.
4. aprovacao/publicacao/rejeicao.

Eventos que limpam RM:

1. criar ou editar `StudentExerciseMax`.
2. criar historico de RM.

## Guardrails de consistencia

1. Cache so acelera leitura.
2. Escritas de reserva continuam em `confirm_student_attendance(...)` com `transaction.atomic()` e locks.
3. Workflow de reserva sempre reler o banco antes de confirmar.
4. Se Redis falhar, a tela monta pelo banco sem quebrar a experiencia.
5. Nenhuma chave pode depender apenas de `student_id`; precisa carregar namespace de box quando o dado aparecer em superficie do aluno.
6. Dado compartilhado por box nunca pode carregar `attendance_status` do aluno.

## Implementacao recomendada

### Fase 1: medir e endurecer SQL

1. Adicionar telemetria local para `student_dashboard_queries`, `student_dashboard_cache_hit`, `student_wod_cache_hit`.
2. Criar teste de query budget para Home e WOD.
3. Adicionar indice composto `ClassSession(status, scheduled_at)`.
4. Revisar `GetStudentDashboard` para evitar lazy load de `identity.student`.

Saida esperada:

1. Menos variacao em miss de cache.
2. Baseline confiavel antes do Redis entrar pesado.

### Fase 2: WOD snapshot primeiro

1. Criar modulo `student_app/application/cache_keys.py`.
2. Criar modulo `student_app/application/wod_snapshots.py`.
3. Serializar WOD publicado para dicionario JSON-safe.
4. Reidratar para `StudentWorkoutDayResult`.
5. Invalidar em acoes de editor/aprovacao de WOD.

Por que comecar pelo WOD:

1. Ele e quase todo compartilhavel.
2. O risco de vazar dado pessoal e baixo.
3. A chave por `workout.version` reduz risco de stale data.

### Fase 3: agenda compartilhada

1. Criar `student_app/application/agenda_snapshots.py`.
2. Montar agenda por janela de dias usando consultas agregadas.
3. Trocar contagem de vagas por `Count(..., filter=Q(attendances__status__in=[...]))`.
4. Invalidar agenda em alteracao de aula, presenca e WOD.

Saida esperada:

1. Home deixa de recalcular ocupacao e titulos de WOD para cada aluno.
2. Varias aberturas simultaneas da Home usam o mesmo pacote compartilhado.

### Fase 4: envelope personalizado da Home

1. Criar snapshot curto por aluno.
2. Recompor `StudentDashboardResult` usando agenda compartilhada + estado pessoal.
3. Invalidar no workflow de reserva/cancelamento/RM/matricula.

Saida esperada:

1. Home quente em 5-7 queries ou menos.
2. Reserva continua consistente porque escrita nao usa cache para decidir.

### Fase 5: RM snapshot

1. Criar cache de mapa de RMs do aluno.
2. Usar no WOD e na tela de RM.
3. Invalidar em create/update de RM.

Saida esperada:

1. WOD maior nao vira N+1 por movimento.
2. Recomendacoes de carga ficam baratas.

## Formato das chaves

Padrao:

`student_app:{surface}:v{schema_version}:{box_slug}:{scope}:{id_or_date}`

Exemplos:

1. `student_app:agenda:v1:control:2026-04-27:7`
2. `student_app:home:v1:control:student:123:2026-04-28:7`
3. `student_app:wod:v1:control:session:7:version:3`
4. `student_app:rm:v1:control:student:123`

Observacao:

O Django ja aplica `KEY_PREFIX` com o namespace do box runtime. Mesmo assim, manter `box_slug` explicito na chave ajuda depuracao, logs e futura migracao para celulas compartilhadas.

## Risco e mitigacao

### Risco: dado velho em reserva

Mitigacao:

1. Reserva nunca e confirmada com base no cache.
2. Workflow reler banco e usa transacao.
3. Invalidar Home do aluno e agenda do box apos salvar Attendance.

### Risco: vazamento entre alunos

Mitigacao:

1. Snapshot compartilhado nao carrega dado pessoal.
2. Snapshot personalizado sempre inclui `student_id`.
3. Testes garantem que aluno A nao recebe status de reserva do aluno B.

### Risco: cache stampede

Mitigacao:

1. TTL com jitter via `shared_support.performance.get_cache_ttl_with_jitter`.
2. Preferir `cache.get_or_set` para snapshots pequenos.
3. Prewarm opcional apos publicacao de WOD ou montagem da semana.

### Risco: Redis virar dependencia dura

Mitigacao:

1. `CACHE_IGNORE_EXCEPTIONS=True` em Redis.
2. Fallback para banco em cache miss/falha.
3. Logs de miss/failure sem quebrar tela.

## Testes de aceite

1. Home sem cache e com cache retornam mesmo `StudentDashboardResult`.
2. Aluno com reserva ve a aula reservada; aluno sem reserva ve a proxima aula.
3. Ao cancelar reserva, Home nao mostra mais status antigo.
4. Ao editar RM, WOD recalcula recomendacao com valor novo.
5. Ao publicar WOD, `/aluno/wod/?session_id=...` mostra o treino novo no primeiro request depois da invalidacao.
6. Query budget: Home cache hit fica abaixo do limite definido.
7. Query budget: WOD cache hit fica abaixo do limite definido.

## Decisao recomendada

Comecar pela Fase 1 e Fase 2.

Motivo:

1. O WOD publicado e o melhor candidato para cache com baixo risco.
2. O indice de `ClassSession(status, scheduled_at)` melhora o miss de cache e protege crescimento.
3. A Home tem regra personalizada sensivel; deve receber cache depois que a invalidacao estiver provada.

## O que nao fazer agora

1. Nao cachear HTML completo da Home autenticada.
2. Nao criar uma tabela materializada no banco antes de medir necessidade real.
3. Nao colocar regra de reserva dentro do cache.
4. Nao ativar multitenancy aberto por causa deste plano.
5. Nao usar `AuditEvent` como read model quente do aluno.

## Execucao em ondas

### C - Contexto

O app do aluno ja possuia cache `default`, Redis em homologacao/producao e fallback local. A leitura inicial mostrou que a Home mistura dados compartilhados com dados pessoais, enquanto o WOD publicado e majoritariamente compartilhavel.

### O - Objetivo

Executar primeiro as mudancas de menor risco:

1. endurecer a consulta quente de agenda com indice.
2. criar contrato de chave versionada.
3. cachear o WOD publicado sem armazenar RM ou recomendacao pessoal do aluno.

### R - Riscos tratados

1. cache velho entre alunos: o snapshot de WOD nao carrega dado pessoal.
2. reserva inconsistente: escrita de reserva continua fora do cache.
3. miss caro no banco: indice composto entrou antes de cache mais agressivo da Home.
4. cache contaminando testes: a suite limpa cache no `setUp` da experiencia do aluno.

### D - Direcao aplicada

Onda 1 e Onda 2 foram executadas. A Home completa fica para uma onda posterior porque envolve reserva ativa, plano, progresso e RM.

### A - Acoes executadas

1. `ClassSession(status, scheduled_at)` recebeu indice composto.
2. `STUDENT_WOD_CACHE_TTL_SECONDS` foi adicionado como configuracao.
3. `student_app/application/cache_keys.py` centraliza chaves versionadas.
4. `student_app/application/wod_snapshots.py` serializa WOD publicado em payload JSON-safe.
5. `GetStudentWorkoutDay` passou a usar snapshot compartilhado e recalcular a recomendacao por RM fora do cache.
6. Teste de contrato garante que `recommended_load_kg` nao entra no snapshot compartilhado.

### Resultado medido

1. `GetStudentWorkoutDay` frio: 4 queries.
2. `GetStudentWorkoutDay` quente: 2 queries.
3. `GetStudentDashboard` frio depois da agenda compartilhada: 11 queries.
4. `GetStudentDashboard` quente depois da agenda compartilhada: 7 queries.
5. Suite `student_app/tests.py`: 66 testes passando.

### Onda 3 executada: agenda compartilhada por box

#### C - Contexto

A Home recalculava agenda, ocupacao e titulos de WOD para cada aluno. Esses dados sao compartilhados por box, mas o status de reserva e pessoal.

#### O - Objetivo

Cachear a agenda compartilhada sem colocar reserva, plano, progresso ou RM do aluno dentro do snapshot comum.

#### R - Riscos tratados

1. status de reserva vazando entre alunos.
2. ocupacao ficando velha apos reserva ou cancelamento.
3. WOD publicado mudando sem atualizar a Home.

#### D - Direcao aplicada

A agenda virou snapshot compartilhado por box e data. A Home recompõe `StudentSessionCard` com esse snapshot e injeta o estado pessoal do aluno depois.

#### A - Acoes executadas

1. `student_app/application/agenda_snapshots.py` monta agenda compartilhada com lotacao agregada.
2. `student_app/application/cache_invalidation.py` centraliza invalidacao de agenda.
3. `student_app/signals.py` limpa agenda em mudancas de aula, presenca e WOD.
4. `GetStudentDashboard` passou a usar `get_student_agenda_snapshot(...)`.
5. Teste garante que o snapshot de agenda nao guarda `Reservado`, mas cada aluno continua vendo seu proprio status.

### Proxima onda recomendada

Onda 4 deve criar o envelope personalizado curto da Home. Essa onda deve ser mais conservadora, com TTL de 20 a 45 segundos e invalidacao em reserva, cancelamento, RM, plano e atividade semanal.

### Onda 4 executada: envelope personalizado curto da Home

#### C - Contexto

Depois da agenda compartilhada, a Home ainda consultava estado pessoal do aluno para reserva, plano, progresso e RM do dia.

#### O - Objetivo

Colocar esse estado pessoal em um envelope curto com TTL baixo, sem colocar a verdade transacional dentro do cache.

#### R - Riscos tratados

1. reserva mudando e a Home continuar velha.
2. RM alterado e a carga recomendada continuar antiga.
3. plano cancelado e a Home continuar mostrando acesso ativo.
4. cache pessoal vazando entre alunos.

#### D - Direcao aplicada

O envelope foi dividido em duas partes pequenas:

1. estado pessoal da Home: reserva por sessao, reserva ativa futura, plano e progresso semanal.
2. `home-rm`: `rm_of_the_day` por aluno e sessao alvo.

#### A - Acoes executadas

1. `student_app/application/home_snapshots.py` cria o envelope curto e o `home-rm`.
2. `student_app/application/cache_invalidation.py` passou a invalidar `home` e `home-rm`.
3. `student_app/signals.py` agora invalida Home em presenca, RM, historico de RM, atividade do app e matricula.
4. `GetStudentDashboard` passou a usar agenda compartilhada + envelope pessoal + `home-rm`.
5. Testes cobrem invalidacao por reserva, RM e plano.

### Resultado medido

1. `GetStudentDashboard` frio: 11 queries.
2. `GetStudentDashboard` quente: 0 queries no cenario local medido.
3. Suite `student_app/tests.py`: 69 testes passando.

### Proxima onda recomendada

Onda 5 pode consolidar o snapshot de RM para reutilizacao tambem na tela `/aluno/rm/` e no calculo do WOD, reduzindo ainda mais trabalho repetido fora da Home.

### Onda 5 executada: snapshot consolidado de RM

#### C - Contexto

Mesmo depois do envelope curto da Home, o RM ainda era consultado por caminhos separados na Home, no WOD e na tela `/aluno/rm/`.

#### O - Objetivo

Transformar RM em uma fonte unica de leitura pessoal do aluno, reaproveitavel na Home, na calculadora do WOD e na tela de records.

#### R - Riscos tratados

1. valor de RM velho em uma tela e novo em outra.
2. query repetida para o mesmo aluno em varias leituras curtas.
3. cache de RM sem invalidacao depois de editar record ou historico.

#### D - Direcao aplicada

O RM virou snapshot proprio por aluno, com records leves e ultimo delta por exercicio. Home, WOD e `/aluno/rm/` agora consomem esse snapshot.

#### A - Acoes executadas

1. `student_app/application/rm_snapshots.py` centraliza records e delta recente.
2. `cache_keys.py` ganhou a chave `student_app:rm:v1:{box_slug}:student:{student_id}`.
3. `cache_invalidation.py` e `signals.py` passaram a invalidar o snapshot de RM em create/update de RM e historico.
4. `GetStudentWorkoutPrescription`, `GetStudentWorkoutDay`, `home_snapshots.py` e `StudentRmView` passaram a reutilizar o snapshot consolidado.
5. Testes cobrem reuso do snapshot e invalidacao apos update de RM.

### Resultado medido

1. `GetStudentDashboard` frio: 11 queries.
2. `GetStudentDashboard` quente: 0 queries.
3. `GetStudentWorkoutDay` quente: 1 query no cenario local medido.
4. `GetStudentWorkoutPrescription` quente: 0 queries.
5. `/aluno/rm/` quente: 2 queries no cenario local medido.
6. Suite `student_app/tests.py`: 71 testes passando.

### Proxima onda recomendada

Onda 6 pode focar em telemetria dedicada do cache do app do aluno, com `Server-Timing` e contadores de hit/miss para Home, WOD e RM, para a gente acompanhar o ganho sem depender de medicao manual.

### Onda 6 executada: telemetria de hit/miss no Server-Timing

#### C - Contexto

O cache do app do aluno ja estava entregando ganho real, mas a leitura desse ganho ainda dependia de medicao manual com `CaptureQueriesContext`.

#### O - Objetivo

Expor hit/miss e duracao dos snapshots no `Server-Timing`, para Home, WOD e RM ficarem auditaveis pelo browser e por smoke manual.

#### R - Riscos tratados

1. telemetria cara demais para o proprio request.
2. multiplos headers paralelos sem contrato unico.
3. sinais de cache visiveis apenas em teste e nao no navegador.

#### D - Direcao aplicada

Cada snapshot passou a registrar `total_ms`, `cache_lookup_ms`, `build_ms` e `cache_hit` no `_octobox_request_perf`; o middleware central transformou isso em `Server-Timing` e headers de debug opcionais.

#### A - Acoes executadas

1. `student_app/application/cache_telemetry.py` centraliza o collector leve.
2. `agenda_snapshots.py`, `home_snapshots.py`, `wod_snapshots.py` e `rm_snapshots.py` passaram a registrar hit/miss.
3. `GetStudentDashboard`, `GetStudentWorkoutDay`, `GetStudentWorkoutPrescription` e as views do app passaram o `request_perf`.
4. `shared_support/request_timing_middleware.py` agora publica:
   `student-home`, `student-agenda`, `student-home-personal`, `student-home-rm`, `student-wod`, `student-wod-shared`, `student-rm`.
5. Testes validam `Server-Timing` e headers de debug de Home e RM.

### Resultado medido

1. `student-app-home` mostrou `student-home`, `student-agenda`, `student-home-personal` e `student-home-rm` no `Server-Timing`.
2. `student-app-wod` mostrou `student-wod`, `student-wod-shared` e `student-rm`.
3. `student-app-rm` mostrou `student-rm`.
4. Headers de debug opcionais passaram a indicar hit para agenda, Home, WOD e RM quando a flag esta aberta.
5. Suite `student_app/tests.py`: 73 testes passando.

### Proxima onda recomendada

Onda 7 pode focar em reduzir o custo frio da Home, especialmente o primeiro `11 queries`, agora usando a telemetria como mapa real de onde ainda existe peso.

### Onda 7 executada: reducao do custo frio da Home

#### C - Contexto

A telemetria mostrou que o primeiro hit da Home ainda custava `11 queries`, com dois blocos mais pesados:

1. leitura duplicada de matricula.
2. caminho caro demais para descobrir apenas o `rm_of_the_day`.

#### O - Objetivo

Reduzir o custo frio da Home sem aumentar risco de inconsistência e sem reintroduzir lógica duplicada.

#### R - Riscos tratados

1. simplificar demais a leitura de plano e quebrar o rótulo da Home.
2. cortar o caminho do `rm_of_the_day` e perder a recomendação correta.
3. mexer no frio e sem querer piorar o quente.

#### D - Direcao aplicada

Atacamos exatamente os dois hotspots medidos:

1. matricula passou a ser resolvida em uma consulta só.
2. `rm_of_the_day` deixou de carregar o WOD completo e passou a buscar apenas o primeiro movimento relevante.

#### A - Acoes executadas

1. `home_snapshots.py` agora resolve enrolamentos em uma leitura unica ordenada.
2. `home_snapshots.py` troca o caminho do `rm_of_the_day` por uma query dirigida em `SessionWorkoutMovement`.
3. O snapshot de RM continua sendo reutilizado, sem regressao no cache quente.

### Resultado medido

1. `GetStudentDashboard` frio caiu de `11` para `8` queries.
2. `GetStudentDashboard` quente permaneceu em `0` queries no cenario local medido.
3. Suite `student_app/tests.py`: 73 testes passando.

### Proxima onda recomendada

Onda 8 pode atacar as 8 queries restantes da Home fria, especialmente o par de consultas de presenca e a leitura de atividade semanal, agora com muito mais clareza sobre o custo real.

### Onda 8 executada: presenca e progresso semanal

#### C - Contexto

A telemetria fria da Home apontava duas pecas ainda visiveis no custo residual:

1. um par de consultas de presenca.
2. a leitura do progresso semanal.

#### O - Objetivo

Diminuir o custo frio sem mexer na regra de reserva e sem perder a leitura do progresso do aluno.

#### R - Riscos tratados

1. juntar presenca demais e quebrar o bloqueio de reserva ativa.
2. simplificar progresso semanal e perder a prioridade do primeiro evento do dia.
3. cortar query e sem querer piorar o cache quente.

#### D - Direcao aplicada

As consultas de presenca foram fundidas em uma so, carregando apenas os campos necessarios para:

1. montar `attendance_by_session`;
2. descobrir `active_reserved_session_id`.

O progresso semanal foi mantido em uma query unica, mas ficou mais magro usando apenas `values_list`.

#### A - Acoes executadas

1. `home_snapshots.py` passou a fazer uma unica leitura de presenca com `Q(session_id__in=...) OR Q(status__in=ACTIVE_ATTENDANCE_CODES)`.
2. `build_student_progress_days(...)` foi promovido para o modulo de snapshot e agora usa apenas `activity_date` e `kind`.
3. `GetStudentDashboard` passou a usar esse builder enxuto.

### Resultado medido

1. `GetStudentDashboard` frio caiu de `8` para `7` queries.
2. `GetStudentDashboard` quente continuou em `0` queries.
3. Suite `student_app/tests.py`: 73 testes passando.

### Proxima onda recomendada

Onda 9 pode atacar os ultimos pontos frios da Home, especialmente:

1. a leitura dos titulos de WOD na agenda;
2. a leitura do primeiro movimento relevante para `rm_of_the_day`.

### Onda 9 executada: titulos de WOD e primeiro movimento relevante

#### C - Contexto

A Home fria ainda carregava dois pontos residuais:

1. uma query so para descobrir os titulos do WOD na agenda;
2. uma query so para descobrir o primeiro movimento relevante do `rm_of_the_day`.

#### O - Objetivo

Embutir esses dois sinais na propria leitura compartilhada da agenda, para o primeiro hit da Home aproveitar o que ja esta sendo lido da sessao.

#### R - Riscos tratados

1. carregar demais a query da agenda e piorar o caminho quente.
2. perder a ordem correta do primeiro movimento `% RM`.
3. quebrar a exibicao de WOD em sessao especifica.

#### D - Direcao aplicada

Os titulos do WOD publicado e o primeiro movimento `% RM` passaram a ser anotados na query base da agenda via `Subquery`. Depois a Home reutiliza esse hint para montar o `rm_of_the_day` sem uma viagem extra ao banco.

#### A - Acoes executadas

1. `agenda_snapshots.py` ganhou `published_workout_title`, `rm_movement_slug`, `rm_movement_label` e `rm_movement_load_value`.
2. `home_snapshots.py` passou a aceitar `movement_hint` no `home-rm`.
3. `GetStudentDashboard` agora passa o hint da sessao focal/ativa para o `home-rm`.

### Resultado medido

1. `GetStudentDashboard` frio caiu de `7` para `5` queries.
2. `GetStudentDashboard` quente continuou em `0` queries.
3. Suite `student_app/tests.py`: 73 testes passando.

### Proxima onda recomendada

Onda 10 pode mirar os ultimos 5 pontos frios da Home e decidir se vale reduzir mais ou se o custo atual ja esta bom o bastante para o produto e para a fase atual.
