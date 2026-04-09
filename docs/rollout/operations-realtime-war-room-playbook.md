<!--
ARQUIVO: roteiro operacional completo para validar realtime cruzado entre superfícies.

TIPO DE DOCUMENTO:
- playbook de guerra controlada

POR QUE ELE EXISTE:
- junta DEV, drawer, Recepcao e Manager numa unica rodada de prova operacional
- evita testar cada ilha separadamente e deixar a concorrencia cruzada passar batida
-->

# Playbook completo de guerra realtime operacional

## Objetivo

Validar o circuito completo entre:

1. painel DEV de metricas SSE e conflitos
2. drawer de alunos
3. board de cobranca curta da Recepcao
4. boards do Manager com SSE nativo

## Contas de laboratorio

Use estas contas:

1. `dev_console / octobox123`
2. `owner_morumbi / octobox123`
3. `manager_vila_andrade / octobox123`
4. `recepcao_santo_amaro / octobox123`

## Janelas recomendadas

1. Janela A: DEV em `http://127.0.0.1:8000/operacao/dev/`
2. Janela B: Owner no diretorio de alunos
3. Janela C: Manager em `http://127.0.0.1:8000/operacao/manager/`
4. Janela D: Recepcao em `http://127.0.0.1:8000/operacao/recepcao/`

Escolha um aluno que:

1. tenha cobranca pendente ou atrasada
2. tenha matricula ativa ou historico claro
3. apareca no board do Manager ou da Recepcao

## Observabilidade minima

### Dentro do produto

Na janela A:

1. veja `Eventos realtime`
2. veja `Streams ativos`
3. veja `Conflitos de save`

### Fora do produto

Abra:

1. `http://127.0.0.1:8000/metrics/`

E filtre por:

1. `octobox_student_sse_events_published_total`
2. `octobox_student_sse_stream_connections_total`
3. `octobox_student_sse_active_streams`
4. `octobox_student_save_conflicts_total`
5. `octobox_manager_sse_events_published_total`
6. `octobox_manager_sse_stream_connections_total`
7. `octobox_manager_sse_active_streams`

### Console do navegador

Na janela B:

```js
window.__octoboxStudentRealtimeTelemetry
```

## Rodada 1: drawer + DEV

1. Na janela B, abra o drawer do aluno.
2. Entre em `Financeiro`.
3. Na janela C ou D, altere pagamento do mesmo aluno.

Esperado:

1. drawer atualiza sem reload da pagina
2. linha do aluno sincroniza
3. painel DEV sobe `student.payment.updated`

## Rodada 2: Recepcao + DEV

1. Na janela D, confirme que o aluno aparece no board de cobranca curta.
2. Na janela C, altere pagamento ou vinculo desse mesmo aluno.

Esperado:

1. board da Recepcao atualiza sozinho
2. pill do board muda para `Atualizado agora`
3. painel DEV sobe evento correspondente

## Rodada 3: Manager + DEV

1. Na janela C, deixe abertos os boards:
   - `Alertas financeiros`
   - `Pagamentos sem vinculo de matricula`
   - `Fila de entrada`
   - `Contatos de WhatsApp sem vinculo`
2. Na janela B ou D, altere pagamento ou vinculo do mesmo aluno.
3. Opcionalmente, na Central de Intake ou via entrada inbound, mude um intake ou um contato de WhatsApp.

Esperado:

1. os quatro boards do Manager reagem no mesmo stream nativo
2. financeiro e vinculo atualizam ao receber eventos do aluno
3. intake e WhatsApp sem vinculo atualizam ao receber `intake.updated` e `whatsapp_contact.updated`
4. o pill mostra `Atualizado agora` ou `Leitura conferida`

## Rodada 4: conflito real de perfil

1. Na janela B, entre em edicao do perfil do aluno no drawer e altere telefone ou email, sem salvar.
2. Na janela C, abra a ficha completa do mesmo aluno e salve uma alteracao de perfil.
3. Volte para a janela B e tente salvar.

Esperado:

1. o rascunho da janela B nao some durante a mudanca externa
2. a janela B recebe aviso de mudanca externa
3. o save da janela B falha com conflito seguro
4. painel DEV sobe `Conflitos de save`

## Rodada 5: hierarquia e lock

1. Na janela D, abra o drawer e clique em `Editar leitura`.
2. Na janela C, abra o mesmo aluno e entre em edicao.

Esperado:

1. a Recepcao perde a caneta
2. a UI volta para leitura
3. o DEV registra `student.lock.preempted`

## Checklist final

So considere aprovado se:

1. nenhuma superficie ficar com dado velho evidente
2. nenhum save sobrescrever versao nova
3. Recepcao e Manager atualizarem sem reload completo da pagina
4. drawer, DEV, Recepcao e Manager contarem a mesma historia

## Leitura simples

Pense nisso como quatro pessoas olhando o mesmo quadro de avisos.

O teste passa quando:

1. o quadro nao mente
2. ninguem apaga aviso novo com aviso velho
3. quem perde a caneta para de escrever
4. a sala inteira continua vendo a mesma verdade
