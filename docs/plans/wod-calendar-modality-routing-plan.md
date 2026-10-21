# Plano — calendário e SmartPaste por modalidade

**Status:** implementação e QA local concluídos; PR isolado aguardando CI/revisão.
**Objetivo de produto:** permitir que a equipe programe modalidades independentes na mesma semana sem misturar treinos nem exigir edição manual aula por aula.

## Decisão de produto

Cada ocorrência (`ClassSession`) pertence a uma modalidade principal (`WorkoutProgram`). Um treino semanal também pertence a uma modalidade. O título é apenas um rótulo humano: “WOD 19h” pode nomear uma aula CrossFit e uma aula HYROX no mesmo horário; a modalidade, não o texto, determina o destino.

Se uma academia oferece CrossFit, HYROX e alongamento no mesmo dia, cria turmas separadas por trilha. O usuário seleciona “CrossFit” no SmartPaste para distribuir à grade CrossFit, depois pode repetir o fluxo para HYROX. Uma turma realmente híbrida ou com dois WODs simultâneos fica fora do MVP e precisa de contrato de prescrição próprio.

## Fluxo esperado

1. Na grade, criar cada ocorrência recorrente com nome, horário e modalidade explícita. O seletor não sugere CrossFit silenciosamente; ajuda explica que a modalidade define qual programação semanal pode chegar à aula.
2. No SmartPaste, escolher a modalidade antes de organizar. Ao editar uma semana existente, preservar sua modalidade. Planos antigos com POST sem o campo continuam temporariamente compatíveis via CrossFit; a tela envia seleção explícita e rejeita seleção vazia.
3. A prévia lista destinos apenas da mesma modalidade e semana. Aula com WOD existente, cancelada e sem destino continuam como estados distintos; confirmar revalida antes de gravar.
4. Mostrar o nome da modalidade na grade diária, semanal e mensal para facilitar a conferência visual.
5. Não permitir reclassificar uma aula que já possui WOD por edição rápida; primeiro deve-se ajustar o WOD conscientemente.

## Contratos e invariantes técnicos

- Criação recorrente requer `workout_program_id` ativo; o writer rejeita chamada direta sem modalidade mesmo quando não passa pelo formulário.
- Deduplicação é `(título, horário, modalidade)`: repetições reais da mesma trilha são ignoradas conforme opção existente, mas CrossFit e HYROX no mesmo horário coexistem.
- Seletores de edição exigem modalidade ativa. Atualização não aceita modalidade inativa/desconhecida nem troca silenciosa de sessão com WOD.
- SmartPaste persiste a trilha no plano; projeção e distribuição usam o FK do plano. Nunca usar inferência pelo nome da aula como fallback de roteamento.
- Modalidade é por tenant. Leitura das grades carrega `workout_program` com `select_related` para manter o custo da serialização previsível.
- Mudança de modalidade feita entre prévia e confirmação deve invalidar/recalcular os destinos; nenhuma confirmação pode aplicar plano a trilha diferente.

## Experiência e recuperação de erro

- O calendário mostra nome da aula e modalidade em conjunto; o campo é obrigatório também no formulário de rodízio de fim de semana.
- O SmartPaste deixa claro que CrossFit, HYROX e Alongamento não se misturam e que a seleção é o filtro de distribuição.
- Sem modalidade: erro junto ao campo, sem criar sessão/plano. Modalidade inativa: orientar nova escolha. Modalidade incompatível com uma aula já programada: não sobrescrever; indicar ajuste consciente.
- Uma modalidade sem aulas elegíveis na semana não cria lote; a prévia deve explicar que falta configurar a grade daquela trilha.

## Entrega e rollout

1. Validar escrita da grade/formulários e chave de deduplicação por modalidade.
2. Validar SmartPaste explícito, persistência e isolamento de prévia/distribuição entre CrossFit e HYROX.
3. Validar browser em desktop e mobile, incluindo rodízio de fim de semana, edição, modal e semana sem destinos.
4. Rodar a suíte focada PostgreSQL/tenant, E2E do composer, verificações Django e migrations.
5. Fazer merge sem escalar tráfego. Após deploy, observar sessões sem programa, POST legado sem modalidade, prévias sem destino, itens ignorados e mismatch plano/aula antes de remover o fallback legado.

## Matriz de aceite

| Caso | Resultado necessário |
|---|---|
| Criar grade sem modalidade | Bloqueada na UI e no writer |
| Criar HYROX com título genérico | Salva HYROX, sem depender do título |
| Mesmo nome/horário em CrossFit e HYROX | Duas aulas independentes |
| Repetir mesma aula/modalidade | Duplicata detectada e política atual de skip preservada |
| SmartPaste CrossFit com ambas as grades na semana | Prévia e distribuição só tocam CrossFit |
| SmartPaste HYROX para a mesma semana | Prévia e distribuição só tocam HYROX |
| Campo vazio explicitamente enviado no SmartPaste | Rejeitado; conteúdo e semana permanecem recuperáveis |
| POST legado que omite modalidade | CrossFit apenas como ponte compatível e monitorável |
| Alterar modalidade com WOD associado | Bloqueado, sem mover/apagar treino |
| Semana sem turma da trilha | Não cria lote e oferece ação para abrir grade |
| Semana/requisição repetida após timeout | Idempotência preservada; nenhum WOD duplicado |
| Conferência do aluno | WOD da aula correta, após os gates atuais de aprovação/publicação |

## Riscos e itens fora do aceite atual

- **Compatibilidade legada:** omissão de campo no POST ainda equivale a CrossFit. Medir para remoção futura; o formulário visual não usa esse fallback.
- **Recursos simultâneos:** permitir duas modalidades paralelas não resolve conflito de coach, espaço ou equipamento. Essa política é operacional e precisa de decisão independente antes de abrir o mesmo slot a dois grupos reais.
- **Dados históricos:** sessões com `workout_program=NULL` ainda podem existir em integrações legadas. Não reclassificar em massa pelo título sem auditoria por tenant.
- **Evidência E2E:** o teste de browser precisa cobrir a sequência calendário → SmartPaste por duas modalidades → distribuição → leitura do aluno; testes menores não substituem esse gate.

## Resultado da validação local

Em 30/09/2026, num banco PostgreSQL novo com migrations e schema tenant:

- 145 testes focados passaram (grade, roteamento/projeção, compatibilidade do SmartPaste e testes de catálogo).
- A mesma suíte focada também passou com `--randomly-seed=42`; o seed de programas de modalidade nos testes de catálogo é explícito e não depende da ordem em que outra classe rodou.
- 4 cenários E2E browser passaram: SmartPaste CrossFit, SmartPaste HYROX, bloqueio de submissão sem modalidade e calendário com seletor obrigatório e turmas paralelas identificadas.
- `manage.py check` não apontou problemas; `makemigrations --check --dry-run` não detectou migrations ausentes; `git diff --check` passou.

Isso valida seleção, persistência, isolamento de modalidade e visualização do calendário. Não substitui o gate completo calendário → distribuição real → app do aluno, nem valida conflito de coach/espaço ou dados históricos de produção. Esses pontos permanecem explicitamente como rollout/decisão operacional, não como evidência já concluída.
