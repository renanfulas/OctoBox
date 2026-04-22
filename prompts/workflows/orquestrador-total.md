<!--
ARQUIVO: workflow-orquestrador total de prompts do OctoBOX.

POR QUE ELE EXISTE:
- junta diagnostico, estruturacao, execucao e validacao em um fluxo unico.
- reduz a friccao entre ideia crua e prompt final operacional.

O QUE ESTE ARQUIVO FAZ:
1. recebe uma ideia vaga ou semi-estruturada.
2. decide qual trilho de prompt deve ser usado.
3. monta o C.O.R.D.A, escolhe o prompt-base e sugere checklist e metricas.

PONTOS CRITICOS:
- este workflow deve organizar a inteligencia, nao substituir evidencia.
- ele precisa evitar excesso de formalidade quando a tarefa for simples.
-->

# Workflow O.R.Q.U.E.S.T.R.A.

`O.R.Q.U.E.S.T.R.A.` significa:

- `O` Ouvir a ideia crua
- `R` Reduzir a nebulosidade
- `Q` Qualificar o tipo de problema
- `U` Unificar o contexto no C.O.R.D.A
- `E` Escolher o prompt-base correto
- `S` Selecionar modo, checklist e metricas
- `T` Transformar em prompt final
- `R` Revisar lacunas e riscos
- `A` Acionar a execucao

Pense nele como um maestro de engenharia:

- a sua ideia e a melodia bruta
- o `C.O.R.D.A` vira a partitura
- o prompt-base vira a secao certa da orquestra
- o checklist garante que ninguem entrou fora do tempo

## Quando usar

Use este workflow quando:

- sua ideia ainda esta crua
- voce nao sabe se o problema e debug, refactor, architecture, frontend, review ou research
- voce quer sair de pensamento solto para prompt de alta qualidade
- voce quer que a IA organize tudo em uma passada

## Mapa mental do fluxo

1. `Entrada crua`
   voce fala de forma natural
2. `Diagnostico`
   separar problema real, sintoma e solucao prematura
3. `Classificacao`
   escolher o tipo de prompt
4. `Estruturacao`
   montar o C.O.R.D.A
5. `Especializacao`
   encaixar debug, refactor, frontend, architecture, review ou research
6. `Aprofundamento opcional`
   se for eficiencia, performance ou sistema, aplicar `G.E.N.I.O.`
7. `Validacao`
   escolher checklist, metricas e definition of done
8. `Execucao`
   devolver o prompt final pronto para colar

## Como usar

Voce so precisa preencher isto:

```md
Ideia crua:

Fluxo afetado:

Arquivos suspeitos ou relevantes:

Nao pode quebrar:

Observacoes:
```

E colar o prompt abaixo.

## Prompt pronto para colar

```md
Voce vai atuar como orquestrador de prompts do OctoBOX.

Sua funcao e pegar a minha ideia crua e transformar isso no melhor trilho de execucao possivel dentro do sistema de prompts do projeto.

Voce deve usar como referencia logica:
- `prompts/corda-diagnostico.md`
- `prompts/corda-fast.md`
- `prompts/corda.md`
- `prompts/workflows/genio-sistemas.md`
- `prompts/architecture.md`
- `prompts/debug.md`
- `prompts/refactor.md`
- `prompts/frontend.md`
- `prompts/review.md`
- `prompts/research.md`
- checklists em `prompts/checklists/`

Regras:
- responda em Portugues do Brasil
- pense no contexto real do OctoBOX
- respeite a filosofia do projeto: corredor oficial, center layer, signal mesh, comportamento antes de cosmetica, evidencia antes de chute
- se eu estiver confundindo problema com solucao, aponte isso
- se faltarem dados, marque `Lacuna`
- nao invente certeza
- se a tarefa for de eficiencia, performance, banco, cache, fila, snapshot ou Celery, aplique tambem o raciocinio do workflow G.E.N.I.O.
- ajuste o nivel de profundidade ao tamanho da tarefa: simples fica simples, complexo fica estruturado

Entregue a resposta exatamente nesta ordem:

1. `Leitura da ideia`
2. `Problema real mais provavel`
3. `Solucoes prematuras ou apostas perigosas`
4. `Tipo recomendado`
   - debug, refactor, frontend, architecture, review ou research
5. `Modo recomendado`
   - Fast ou Planning
6. `Checklist recomendado`
7. `Se precisa do workflow G.E.N.I.O.`
8. `Rascunho de C.O.R.D.A`
9. `Prompt-base recomendado`
10. `Prompt final pronto para execucao`
11. `Metricas ou validacoes que vao provar que deu certo`
12. `Versao curta reutilizavel`

No item `Rascunho de C.O.R.D.A`, use exatamente esta estrutura:

Contexto:
- Projeto: OctoBOX
- Fase atual:
- Fluxo afetado:
- Arquivos relevantes:
- Docs obrigatorios:
- Skills de apoio:
- Restricoes reais:
- Assuncao:

Objetivo:
- Resolver exatamente:

Restricoes:
- Nao pode quebrar:
- Nao pode reescrever:
- Escopo maximo:
- Forma de resposta esperada:

Definition of done:
- O trabalho estara pronto quando:
- Validacao minima:

Auditoria:
- Cite arquivos e linhas quando houver.
- Separe fato, hipotese e inferencia.
- Diga riscos e impacto.
- Diga o que falta para fechar a confianca.

No item `Prompt final pronto para execucao`, monte um prompt completo, ja fundindo:
- o C.O.R.D.A
- o prompt-base escolhido
- e o workflow G.E.N.I.O., se aplicavel

Minha entrada:

Ideia crua:
[cole aqui]

Fluxo afetado:
[cole aqui]

Arquivos suspeitos ou relevantes:
[cole aqui]

Nao pode quebrar:
[cole aqui]

Observacoes:
[cole aqui]
```

## Como o workflow decide o tipo

Use esta heuristica:

- `debug`: erro, falha, regressao, comportamento estranho
- `refactor`: estrutura ruim, acoplamento, ownership confuso
- `frontend`: UI, UX, template, CSS, JS, assets
- `architecture`: fronteira, camada, escalabilidade, ownership sistêmico
- `review`: revisar risco, diff, PR, mudanca pronta
- `research`: comparar caminhos, decidir prioridade ou estrategia

Se aparecer:

- banco
- cache
- Celery
- fila
- snapshot
- latencia
- gargalo

Entao avalie tambem `G.E.N.I.O.`.

## Como o workflow escolhe o modo

- `Fast`: tarefa local, simples, de 1 arquivo ou ajuste pontual
- `Planning`: tarefa estrutural, risco alto, varios arquivos ou necessidade de raciocinio profundo

## Como o workflow escolhe o checklist

- `debug` -> `prompts/checklists/debug-checklist.md`
- `refactor` -> `prompts/checklists/refactor-checklist.md`
- `frontend` -> `prompts/checklists/frontend-checklist.md`
- `review` -> `prompts/checklists/review-checklist.md`
- `architecture` e `research` -> escolher o checklist mais proximo do risco dominante e declarar isso

## Exemplo curto

Entrada:

```md
Ideia crua:
Quero mexer no Celery porque acho que o cache e o banco podem responder mais rapido.

Fluxo afetado:
Dashboard e jobs de auditoria.

Arquivos suspeitos ou relevantes:
- auditing/tasks.py
- dashboard/dashboard_snapshot_queries.py
- shared_support/redis_snapshots.py

Nao pode quebrar:
- dashboard
- auditoria
- leitura financeira

Observacoes:
Nao sei se o problema e banco, fila, cache ou arquitetura.
```

O workflow deve perceber:

- isso pode ser mais `research` ou `architecture` do que `refactor` de cara
- Celery pode ser solucao prematura
- primeiro precisa modelar gargalo e escolher alavanca dominante
- `Planning` e mais apropriado
- `G.E.N.I.O.` provavelmente entra

## Regra final

Se a ideia estiver nebulosa, nao pule direto para execucao.
Use o O.R.Q.U.E.S.T.R.A. para sair do caos para o trilho.

Engenharia forte nao e pensar bonito.
E transformar intuicao em decisao auditavel.
