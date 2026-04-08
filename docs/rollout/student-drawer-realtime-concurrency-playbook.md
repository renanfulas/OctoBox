<!--
ARQUIVO: roteiro de observabilidade e guerra controlada do drawer realtime de alunos.

TIPO DE DOCUMENTO:
- playbook operacional de validacao

AUTORIDADE:
- alta para validar SSE, locks, conflitos e drawer parcial antes de ampliar o realtime

QUANDO USAR:
- antes de promover o circuito realtime para beta mais largo
- quando houver mudancas em lock, SSE, snapshot_version ou concorrencia do drawer

POR QUE ELE EXISTE:
- evita teste "parece bom" sem prova operacional
- padroniza os cenarios de concorrencia e os checks de observabilidade
- acelera triagem entre bug visual, bug de dominio e bug de tempo real
-->

# Playbook de concorrencia realtime do drawer de alunos

## Objetivo

Validar que o drawer de alunos reage em tempo real a:

1. lock adquirido, liberado e tomado por hierarquia maior
2. pagamento alterado em outra aba
3. matricula alterada em outra aba
4. conflito de save por versao

E validar que isso acontece com:

1. fallback seguro para polling
2. preservacao de rascunho local quando apropriado
3. observabilidade minima via Prometheus e telemetria local do browser

## Preparacao

Abrir duas janelas normais e uma anonima, por exemplo:

1. janela A: `owner_morumbi`
2. janela B: usuario manager
3. janela C: usuario recepcao

Usar o mesmo aluno durante toda a rodada.

Se possivel, escolher um aluno com:

1. pagamento pendente ou atrasado
2. matricula ativa
3. dados de perfil faceis de alterar

## Observabilidade que deve estar ligada

### Metrics backend

Checar `GET /metrics/` localmente e observar:

1. `octobox_student_sse_events_published_total`
2. `octobox_student_sse_stream_connections_total`
3. `octobox_student_sse_active_streams`
4. `octobox_student_save_conflicts_total`

### Telemetria do browser

Na janela com o drawer aberto, usar no console:

```js
window.__octoboxStudentRealtimeTelemetry
```

Esperado:

1. `duplicateEventsIgnored`
2. `staleEventsIgnored`
3. `profileEventsDeferred`
4. `conflictResponses`

## Cenario 1: lock tomado por hierarquia maior

1. Recepcao abre o drawer e entra em `Editar leitura`.
2. Confirmar que o drawer mostra edicao ativa.
3. Manager abre o mesmo aluno e entra em edicao.

Esperado:

1. Recepcao perde a edicao sem reload completo.
2. O drawer da recepcao volta para leitura.
3. O feedback informa quem assumiu a caneta.
4. Prometheus incrementa `octobox_student_sse_events_published_total{event_type="student.lock.preempted"}`.

## Cenario 2: pagamento alterado em outra aba

1. Janela A abre o drawer do aluno na tab `Financeiro`.
2. Janela B registra um pagamento ou atualiza uma cobranca do mesmo aluno.

Esperado:

1. Janela A recebe refresh em tempo real.
2. Header e linha do aluno sincronizam.
3. Financeiro do drawer atualiza sem exigir reload completo da pagina.
4. Prometheus incrementa `event_type="student.payment.updated"`.

## Cenario 3: matricula alterada em outra aba

1. Janela A deixa o drawer aberto no mesmo aluno.
2. Janela B cancela, reativa ou ajusta a matricula.

Esperado:

1. Drawer da janela A atualiza o bloco financeiro/vinculo.
2. Linha do aluno permanece coerente com plano/status recentes.
3. Prometheus incrementa `event_type="student.enrollment.updated"`.

## Cenario 4: rascunho preservado durante mudanca externa

1. Janela A entra em edicao do perfil e altera telefone, email ou observacao, sem salvar.
2. Janela B altera o perfil do mesmo aluno e salva.

Esperado:

1. Janela A nao perde o texto digitado.
2. O drawer mostra aviso de mudanca externa.
3. `window.__octoboxStudentRealtimeTelemetry.profileEventsDeferred` sobe.

## Cenario 5: conflito de save por versao

1. Repetir o cenario 4.
2. Depois da mudanca na janela B, tentar salvar o rascunho da janela A.

Esperado:

1. Backend responde conflito.
2. O drawer volta para leitura segura.
3. O usuario nao sobrescreve dado mais novo.
4. Prometheus incrementa `octobox_student_save_conflicts_total`.
5. `window.__octoboxStudentRealtimeTelemetry.conflictResponses` sobe.

## Cenario 6: evento velho ou duplicado

Este cenario pode ser observado em ambiente de uso real ou em testes com reconexao.

Esperado:

1. Eventos duplicados nao causam refresh repetido.
2. Eventos antigos nao repintam a UI com versao velha.
3. `duplicateEventsIgnored` e `staleEventsIgnored` sobem quando aplicavel.

## Checklist de aprovacao

Marcar como aprovado apenas se:

1. nenhum lock for mantido de forma fantasma
2. nenhum save sobrescrever dado mais novo
3. drawer nao apagar rascunho indevidamente
4. linha, header e financeiro permanecerem coerentes
5. `/metrics/` refletir o comportamento esperado

## Falhas que bloqueiam promocao

Bloqueador imediato:

1. SSE causar overwrite de dado novo por evento velho
2. lock tomado e UI continuar editavel
3. save conflitante passar como sucesso
4. drawer travar sem fallback para polling

## Leitura simples

Pense neste teste como tres pessoas mexendo no mesmo fichario ao mesmo tempo.

O objetivo nao e provar que nunca ha disputa.
O objetivo e provar que, quando ha disputa, o sistema nao mente, nao engole informacao e nao faz uma pessoa apagar o trabalho da outra sem aviso.
