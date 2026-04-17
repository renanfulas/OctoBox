<!--
ARQUIVO: plano C.O.R.D.A. do pipeline de importacao de leads.

TIPO DE DOCUMENTO:
- plano estrutural de execucao e contrato operacional

AUTORIDADE:
- alta para a frente de importacao de leads

DOCUMENTO PAI:
- [../../README.md](../../README.md)

DOCUMENTOS IRMAOS:
- [../reference/documentation-authority-map.md](../reference/documentation-authority-map.md)
- [../reference/reading-guide.md](../reference/reading-guide.md)
- [../architecture/django-core-strategy.md](../architecture/django-core-strategy.md)

QUANDO USAR:
- quando a duvida for como implementar, evoluir ou validar o pipeline de importacao de leads sem travar a operacao e sem criar debito tecnico

POR QUE ELE EXISTE:
- transforma uma decisao de produto e operacao em contrato tecnico executavel
- evita que limites, trilhos de processamento e logica de duplicatas fiquem espalhados em view, service e template
- cria uma fonte unica para jobs, UX, policy e deduplicacao

O QUE ESTE ARQUIVO FAZ:
1. define a tese do pipeline de importacao de leads
2. registra a regra de negocio oficial
3. estabelece o contrato de UX e status
4. organiza a implementacao por commits em ordem segura

PONTOS CRITICOS:
- a selecao do usuario ajuda a acelerar, mas nao pode ser a verdade final
- arquivos medios e grandes nao devem ser lidos integralmente em memoria para tomada de decisao
- deduplicacao por telefone deve usar indice deterministico, nao busca ingenua em campo criptografado
- duplicata e warning operacional, nao erro tecnico puro
-->

# Pipeline de importacao de leads

## Regra de autoridade deste documento

1. este documento define a verdade ativa da frente de importacao de leads
2. o runtime real e os testes continuam vencendo se houver divergencia
3. qualquer ajuste de UX, policy, jobs ou duplicatas nesta frente deve se alinhar aqui primeiro

## Tese central

O pipeline de importacao de leads do OctoBox nao deve ser apenas um upload de arquivo com parse e insert.

Ele deve funcionar como um sistema operacional de ingestao:

1. rapido no caso comum
2. seguro no caso medio
3. economico no caso pesado
4. transparente para o owner
5. governado por limites claros

Traducao pratica:

1. box medio com cerca de 150 alunos deve conseguir importar sem friccao
2. volume moderado nao pode travar a navegacao do usuario
3. volume maior deve sair do horario comercial e ir para a janela economica
4. duplicatas nao podem sumir em silencio
5. o sistema precisa decidir por trilho com base no volume real do arquivo

## C.O.R.D.A.

### C - Contexto

Hoje o projeto ja possui:

1. importacao de CSV e VCF em [operations/services/contact_importer.py](../../operations/services/contact_importer.py)
2. tela operacional em [guide/views.py](../../guide/views.py)
3. task assina existente em [operations/tasks.py](../../operations/tasks.py)
4. infraestrutura de blind index e `phone_lookup_index`

Hoje o projeto ainda nao possui:

1. politica formal de trilhos por volume
2. limite diario e mensal por tipo de importacao
3. job persistido com status visivel para owner
4. relatorio operacional rico de duplicatas
5. deduplicacao orientada por `phone_lookup_index` no importador
6. agendamento noturno como trilho oficial do volume pesado

### O - Objetivo

Entregar um pipeline de importacao com estes trilhos oficiais:

1. ate 200 leads: `sync`
2. de 201 a 500 leads: `async_now`
3. de 501 a 2000 leads: `async_night`
4. acima de 2000 leads: `reject`

Com estas regras adicionais:

1. 1 upload por dia por tipo de importacao
2. 3 uploads por mes por tipo de importacao
3. a faixa escolhida pelo usuario acelera a decisao, mas nao substitui a validacao do backend
4. duplicatas devem gerar log operacional com motivo
5. owner deve conseguir agir manualmente sobre os duplicados

Definicao de sucesso:

1. o request web fica curto no caso medio e grande
2. o usuario continua navegando em `async_now`
3. o volume pesado vai para o trilho noturno automaticamente
4. duplicatas e erros ficam rastreaveis por job
5. os testes cobrem trilhos, limites e duplicatas

### R - Riscos

Riscos tecnicos:

1. continuar lendo arquivo inteiro em memoria para qualquer decisao
2. manter deduplicacao baseada em campo criptografado como se fosse campo de igualdade comum
3. espalhar regra de negocio entre view, service e task
4. nao ter status persistido de job

Riscos operacionais:

1. owner nao entender por que um arquivo foi para background ou noite
2. duplicatas serem descartadas sem visibilidade
3. mesma lista ser reenviada repetidamente sem bloqueio
4. fila noturna virar caixa-preta sem criterio

Riscos de debito tecnico:

1. confiar na selecao manual do usuario como verdade
2. implementar primeiro na tela e depois descobrir a regra no backend
3. misturar parsing, policy, deduplicacao e persistencia no mesmo arquivo

### D - Direcao

Direcao principal:

1. policy central para limites e roteamento
2. inspeção leve do arquivo para contar leads validos e parar cedo
3. job persistido para rastrear ciclo completo
4. execucao separada entre sync, background imediato e janela noturna
5. deduplicacao robusta por telefone com `phone_lookup_index`
6. relatorio operacional de duplicatas e erros

Frase guia:

o usuario sinaliza a pista, o backend decide o trilho.

### A - Acoes

1. criar o model de job e seus enums
2. criar a policy de importacao
3. criar o inspetor leve de arquivos
4. criar o orquestrador do fluxo
5. conectar a tela operacional ao novo pipeline
6. endurecer a deduplicacao
7. persistir relatorio operacional
8. ligar background imediato
9. ligar agendamento noturno
10. fechar observabilidade e UX

## Regra de negocio oficial

### Tipos de importacao

1. `whatsapp_list`
2. `tecnofit_export`
3. `nextfit_export`
4. `iphone_vcf`

### Faixas declaradas pelo usuario

1. `up_to_200`
2. `from_201_to_500`
3. `from_501_to_2000`

### Trilhos oficiais

1. `<= 200` leads validos: processa na hora
2. `201..500` leads validos: background imediato
3. `501..2000` leads validos: agendamento noturno
4. `> 2000` leads validos: rejeitado

### Limites de frequencia

Por `source_type`:

1. 1 upload por dia
2. 3 uploads por mes

### Regra de contagem

1. o backend conta leads validos, nao apenas linhas brutas
2. linha vazia nao conta
3. cabecalho nao conta
4. item sem telefone valido nao deve inflar a faixa
5. a selecao do usuario define o limite inicial de verificacao, nao a verdade final

## Contrato de UX

### Campos na tela

1. tipo de importacao
2. faixa declarada
3. upload de arquivo
4. envio da lista

### Textos de apoio

1. `Ate 200 leads sao processados imediatamente.`
2. `De 201 a 500 leads, sua importacao sera processada em background.`
3. `Acima de 500 leads, sua importacao sera agendada para processamento noturno.`
4. `Limite maximo por arquivo: 2000 leads.`
5. `Cada tipo permite 1 upload por dia e ate 3 por mes.`

### Mensagens de bloqueio

1. `Voce so pode fazer upload 1x por dia para este tipo de importacao.`
2. `Voce atingiu o limite de 3 uploads no mes para este tipo de importacao.`
3. `Este arquivo excede o limite de 2000 leads para importacao.`

### Mensagens de destino

1. `Importacao concluida com sucesso.`
2. `Sua importacao foi enviada para processamento em background. Voce pode continuar navegando normalmente.`
3. `Sua importacao foi agendada para processamento economico noturno.`

## Modelo de job e status

### Entidade alvo

Nome sugerido:

`LeadImportJob`

### Campos minimos

1. `created_by`
2. `source_type`
3. `declared_range`
4. `detected_lead_count`
5. `processing_mode`
6. `status`
7. `original_filename`
8. `file_path`
9. `scheduled_for`
10. `success_count`
11. `duplicate_count`
12. `error_count`
13. `duplicate_details`
14. `error_details`
15. `started_at`
16. `finished_at`

### Enums

`processing_mode`

1. `sync`
2. `async_now`
3. `async_night`

`status`

1. `received`
2. `validating`
3. `queued`
4. `scheduled`
5. `running`
6. `completed`
7. `completed_with_warnings`
8. `rejected`
9. `failed`

## Politica de deduplicacao

### Tese

Duplicata nao deve ser tratada como erro tecnico puro.

Ela deve ser tratada como warning operacional com trilha de auditoria manual para o owner.

### Regras

1. telefone: usar `phone_lookup_index` como criterio principal
2. email: usar valor normalizado de forma consistente
3. detectar duplicata dentro do proprio arquivo
4. detectar duplicata ja existente no banco

### Motivos padronizados

1. `duplicate_in_file_phone`
2. `duplicate_in_file_email`
3. `duplicate_in_database_phone`
4. `duplicate_in_database_email`

### Campos do relatorio de duplicatas

1. `name`
2. `phone`
3. `normalized_phone`
4. `email`
5. `reason`

## Estrategia de implementacao sem debito tecnico

### Camadas alvo

1. `lead_import_policy.py`
2. `lead_import_inspector.py`
3. `lead_import_orchestrator.py`
4. `contact_importer.py` refatorado para execucao real
5. `tasks.py` para async imediato e noturno

### Guardrails

1. nao confiar na faixa declarada como verdade final
2. nao usar `list(reader)` na inspecao de arquivos medios e grandes
3. nao fazer busca ingenua em campo criptografado para telefone
4. nao espalhar regra de negocio na view
5. nao esconder duplicatas do owner

## Plano por commits

### Commit 1

`feat(operations): add lead import job model and enums`

Objetivo:

1. criar a fundacao persistente do pipeline

Entregas:

1. model `LeadImportJob`
2. enums de tipo, faixa, modo e status
3. migration

### Commit 2

`feat(operations): add lead import policy for limits and routing`

Objetivo:

1. centralizar limites e trilhos

Entregas:

1. `lead_import_policy.py`
2. regras de limite diario e mensal
3. decisao de `sync`, `async_now`, `async_night` e `reject`

### Commit 3

`feat(operations): add lightweight lead import inspector`

Objetivo:

1. contar leads validos de forma barata

Entregas:

1. `lead_import_inspector.py`
2. leitura em streaming
3. stop-early por faixa declarada

### Commit 4

`feat(operations): add import orchestration service`

Objetivo:

1. criar um ponto unico de coordenacao

Entregas:

1. `lead_import_orchestrator.py`
2. criacao de job
3. escolha do trilho

### Commit 5

`refactor(guide): wire operational settings to lead import orchestrator`

Objetivo:

1. conectar a tela atual ao novo pipeline

Entregas:

1. adaptacao de `guide/views.py`
2. adaptacao do template
3. mensagens de UX corretas

### Commit 6

`refactor(operations): harden duplicate detection with phone lookup index`

Objetivo:

1. endurecer a deduplicacao por telefone

Entregas:

1. refatoracao de `contact_importer.py`
2. uso de `phone_lookup_index`
3. motivos padronizados

### Commit 7

`feat(operations): persist duplicate and error reports for lead imports`

Objetivo:

1. transformar duplicatas e erros em relatorio operacional

Entregas:

1. `duplicate_details`
2. `error_details`
3. contadores persistidos no job

### Commit 8

`feat(operations): add background lead import execution`

Objetivo:

1. habilitar o trilho `201..500`

Entregas:

1. task de execucao imediata
2. atualizacao de status do job

### Commit 9

`feat(operations): add nightly scheduling for large lead imports`

Objetivo:

1. habilitar o trilho `501..2000`

Entregas:

1. scheduler noturno
2. jobs `scheduled`
3. dispatcher da janela `00h` a `04h`

### Commit 10

`feat(guide): show import status and duplicate preview in operational settings`

Objetivo:

1. fechar o circuito de feedback operacional

Entregas:

1. status na interface
2. resumo do job
3. previa de duplicatas

### Commit 11

`test(operations): add end-to-end coverage for lead import pipeline`

Objetivo:

1. blindar a evolucao da feature

Entregas:

1. testes de trilhos
2. testes de limites
3. testes de duplicatas
4. testes de mensagens

## Ordem segura de execucao

1. model
2. policy
3. inspector
4. orchestrator
5. view
6. deduplicacao robusta
7. relatorio
8. background imediato
9. agendamento noturno
10. UX final
11. cobertura completa

## Criterio de pronto

1. `<=200` conclui no request
2. `201..500` cria job de background imediato
3. `501..2000` cria job agendado
4. `>2000` rejeita
5. duplicatas ficam visiveis com motivo
6. limites diario e mensal por tipo sao respeitados
7. owner entende o destino da importacao sem abrir log tecnico
8. testes cobrem os contratos centrais da frente
