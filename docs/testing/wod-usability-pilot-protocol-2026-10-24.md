# Protocolo do piloto de usabilidade — WOD diário e semanal

**Estado:** instrumento preparado; nenhuma sessão com participantes foi executada.
**Autoridade:** operacionaliza as metas propostas na seção 4 do plano C.O.R.D.A.; não altera metas, ACL, contratos ou gates de segurança.
**Fontes:** plano C.O.R.D.A. (pacote documental P00), [contrato diário/semanal](../reference/wod-daily-weekly-contract.md) e [corpus WOD](wod-input-contract-corpus.md).

## Objetivo e limites

Observar se pessoas que exercem os papéis Owner, Manager e Coach conseguem montar e conferir um WOD diário e organizar uma semana completa sem intervenção do moderador. A amostra fica fixada em **3 Coaches, 1 Manager e 1 Owner**. A leitura do treino publicado pelo aluno é uma checagem técnica separada, conduzida pelo moderador com a conta sintética; não conta como sexto participante nem entra no denominador operacional. O estudo mede usabilidade; não substitui testes de ACL, isolamento entre tenants, concorrência, navegador ou provider.

Usar somente tenant isolado e dados sintéticos. Preparar uma instância limpa por participante, com aulas/programas de teste e política de aprovação que impeça publicação acidental para alunos reais. Não reutilizar a conta Coach compartilhada da prévia como credencial de estudo. Não chamar IA/provider externo. Não registrar nome, e-mail, peso corporal, telefone, conteúdo privado ou gravação sem consentimento explícito.

## Amostra e denominador definidos

P01–P03 exercem Coach, P04 Manager e P05 Owner. Os cinco têm permissão nas rotas de apply diário, Smart Paste semanal e drafts, portanto o denominador é **5** para as tarefas 1–3 e para cada critério `4/5`. Esta composição cobre o papel primário de autoria e os papéis de gestão sem ampliar ACL. Reception não entra porque o contrato atual não lhe dá essas operações. A elegibilidade foi conferida em `operations/workout_day_apply_views.py`, `operations/workout_board_views.py::WorkoutSmartPasteView` e `operations/workout_draft_views.py`.

A tarefa 4 é um controle funcional independente: o moderador abre uma sessão de aluno sintético e confirma o snapshot publicado. Registrar passa/falha uma vez por fixture publicada, sem somá-la ao número de participantes nem ao denominador `4/5`. Nas tarefas 1–3, falha, abandono, conclusão após 120/300 segundos ou necessidade de dica contam como não sucesso; uma falha de infraestrutura que impeça iniciar a tarefa invalida e deve ser reagendada, registrando o desvio sem pontuá-la como falha de usabilidade.

Registrar apenas código anônimo (`P01`–`P05`), papel exercido, experiência declarada em faixa, dispositivo/navegador e se houve orientação inicial. O resultado individual fica na ficha; relatórios compartilhados usam contagens agregadas e notas sem dados identificáveis.

## Preparação padronizada

1. Anotar SHA/código da aplicação, tenant sintético, navegador/versão, viewport, tema, fuso horário e data de execução.
2. Confirmar que a pessoa está autenticada no papel indicado e que o tenant contém somente fixtures. Fazer captura do estado inicial sem dados pessoais.
3. Usar o corpus `W-00` para a tarefa diária e `W-07` para a tarefa semanal. Para o W-07, criar uma aula elegível por dia (`HY-W01`…`HY-W07`) em `P-HY` e uma aula decoy no mesmo dia (`CF-W01`…`CF-W07`) em `P-CF`. Ambas as trilhas usam `ClassType=cross`; todas as aulas começam sem WOD, em estado aplicável. A prévia/distribuição esperada contém sete destinos HYROX e não altera nenhuma aula CrossFit.
4. Usar sempre a mesma versão das fixtures e reiniciar o tenant entre participantes. Preservar WODs publicados sintéticos apenas para a etapa de leitura do aluno.
5. Dar uma orientação curta e idêntica sobre onde fica o corredor de WOD; não demonstrar como concluir as tarefas. O cronômetro começa depois dessa orientação, quando a tarefa é apresentada.

Antes das sessões, confirmar que `WOD_WEEKLY_NORMALIZER_ENABLED=False`, que nenhum box está allowlisted e que o navegador não envia texto a provider. O parser determinístico deve ser o único caminho usado neste piloto. Se a configuração ou a rede permitir chamada externa, interromper e corrigir o isolamento antes de iniciar.

Se o ambiente estiver com banco compartilhado, usuários reais, destinatário/provider configurado ou classe/programa fora do isolamento esperado, não iniciar a sessão.

## Roteiro do moderador

Ler somente o texto entre aspas. Não sugerir botão, caminho, modalidade ou correção. Se a pessoa pedir ajuda, responder “faça como faria normalmente” e registrar a intervenção. Se houver risco de escrita fora do tenant de teste, interromper imediatamente.

### Tarefa 1 — aplicar o WOD diário

> “Uma aula de CrossFit precisa receber o treino de segunda-feira. Use o modelo indicado no material e confira quais aulas serão afetadas antes de concluir.”

Usar `W-00`, a data e o programa definidos na fixture. Sucesso: a pessoa abre o fluxo correto, escolhe explicitamente o programa, confere a prévia, confirma uma única vez e identifica o resultado final. Registrar qualquer tentativa de aplicar ao programa que compartilha `ClassType`.

### Tarefa 2 — montar e distribuir a semana

> “Organize esta semana para o programa HYROX. Confira se os sete dias e o conteúdo estão corretos e conclua a distribuição no ambiente de teste.”

Usar o texto `W-07`. A prévia deve ser conferida antes da confirmação. Sucesso exige sete dias de segunda a domingo, programa HYROX (`P-HY`) explícito e nenhum destino CrossFit (`P-CF`) alterado. A confirmação cria apenas os resultados sintéticos permitidos pela política do tenant de teste.

### Tarefa 3 — recuperar um rascunho

> “Você começou a preparar a semana, mudou de tela e voltou. Recupere o que já foi salvo e continue sem perder o conteúdo.”

Começar com um texto parcial em `WeeklyWodPlan` ou `WodInputDraft`, esperar o estado “salvo” e então recarregar/voltar conforme o fluxo previsto. Sucesso: conteúdo salvo reaparece e a pessoa entende qualquer diferença entre último ACK e texto ainda não salvo. Não simular perda de rede de modo diferente entre participantes.

### Tarefa 4 — conferir a leitura do aluno

> “Abra a área do aluno e confirme qual treino está disponível para a aula concluída pelo coach.”

Usar conta sintética de aluno em sessão separada. Sucesso: somente o snapshot publicado aparece, com a versão correta; rascunho, prévia e conteúdo pendente não aparecem. Registrar este resultado separadamente da amostra e do denominador operacional até a decisão de composição acima.

## Medidas e critérios

Para cada tarefa, registrar tempo em segundos, conclusão, intervenção (`0`, `1`, `2+`), erros, trocas de contexto, recuperação/correção, modalidade/dia/programa escolhido e dificuldade percebida numa escala de 1 (fácil) a 5 (muito difícil). No fim de cada tarefa, pedir uma nota de confiança de 1 a 5. Não inferir satisfação por silêncio ou rapidez.

- **WOD diário:** pelo menos 4/5 participantes elegíveis concluem sem intervenção em até 120 s, após orientação inicial curta.
- **WOD semanal:** pelo menos 4/5 participantes elegíveis concluem em até 300 s; nenhum aplica dia ou modalidade incorretos.
- **Recuperação:** relatar taxa de recuperação correta e distinguir estado confirmado de edição ainda sem ACK; o plano não define limiar numérico para esta tarefa.
- **Leitura do aluno:** nenhuma prévia, rascunho ou versão pendente fica visível como publicada; relatar separadamente e não misturar com tempo do coach.

Uma aplicação incorreta de dia, programa, modalidade ou Box reprova o critério de segurança/usabilidade mesmo se a pessoa concluir rapidamente. Encerrar e restaurar o tenant sintético antes de novo participante.

## Ficha por participante

| Código | Papel | Dispositivo/browser | Diária (s / concluiu / intervenção / dificuldade) | Semanal (s / concluiu / intervenção / dificuldade) | Rascunho recuperado | Leitura publicada correta | Notas sem identificadores |
|---|---|---|---|---|---|---|---|
| P01 | Coach |  |  |  |  |  |  |
| P02 | Coach |  |  |  |  |  |  |
| P03 | Coach |  |  |  |  |  |  |
| P04 | Manager |  |  |  |  |  |  |
| P05 | Owner |  |  |  |  |  |  |

## Relatório de saída

Registrar amostra/denominador efetivo por tarefa, critérios aprovados e reprovados, mediana e faixa dos tempos, quantidade de intervenções, erros de escopo, versão/dispositivo usados e qualquer desvio do protocolo. Separar observações de fato verificado e recomendação. Anexar evidência sintética sem dados pessoais; atualizar o plano C.O.R.D.A. e `STATUS.md` sem marcar o piloto como aprovado antes de executar as cinco sessões elegíveis.
