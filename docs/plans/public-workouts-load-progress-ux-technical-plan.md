# Plano técnico — evolução de carga no treino do aluno

**Status:** implementação aplicada; validação automatizada concluída, QA visual responsivo e PWA instalada pendentes
**Escopo:** experiência de evolução de carga na tela pública de treino do aluno
**Referência visual:** Luxo Futurista 2050, aplicado com contenção e prioridade à leitura
**Não inclui:** mudanças de regra de elegibilidade, migração de dados ou reescrita da experiência de treino

## 1. Resultado esperado

Ao abrir a área de cargas, o aluno deve conseguir responder rapidamente:

1. Qual foi minha última carga válida neste exercício?
2. Estou progredindo, mantendo ou reduzindo a carga?
3. Como foram minhas sessões anteriores?
4. O que devo registrar agora?

A interface deve apresentar esses dados em uma hierarquia curta. A curva é evidência da evolução, não um gráfico decorativo. O fluxo de registrar carga permanece acessível sem obrigar o aluno a abrir detalhes.

## 2. Situação técnica atual

O caminho de renderização a preservar é:

```text
PublicWorkoutDetailView / _render_public_workout_html
  -> build_progress_snapshots (lote por conta)
  -> template tags em public_workouts_extras.py
  -> templates/public_workouts/workout.html
  -> static/css/public_workouts/workout-shell.css
  -> static/js/public_workouts/load_tracker.js
```

Pontos atuais relevantes:

- A seção de cargas está no template principal. Ela contém revisão semanal, recordes, resumo do ciclo e evolução por movimento.
- `build_progress_snapshots` já agrega os snapshots em lote. Não adicionar consulta ORM dentro do loop de movimentos.
- `progress_eligibility.py` é a regra de quais registros contam como top set; `progress_snapshot.py` constrói a série e tendência. A camada visual deve consumir essas regras, sem recalculá-las.
- A curva atual usa uma janela de 90 dias. Histórico legado é apresentado separado e não deve ser conectado visualmente à série comparável.
- Um único ponto não comprova tendência. Usar o `trend_signal` existente e manter o estado sem tendência quando não houver pontos suficientes.
- O payload de ponto passado ao template hoje é resumido. Para a lista de sessões, será necessário expor reps, RIR, programa e semana a partir do snapshot existente, sem nova consulta.
- O domínio atual modela um top set efetivo por exercício e por dia. Correções no mesmo dia atualizam o registro ativo. Não representa sessões distintas múltiplas no mesmo dia.
- O formulário de registro já suporta série de aquecimento, top set, reps, RIR, placa/carga e confirmação. A UI deve preservar serialização, idempotência e correção atuais.
- A navegação inferior fixa pode cobrir controles do formulário em telas baixas. Resolver em conjunto com safe area, foco e teclado virtual.

### Arquivos de implementação previstos

- `student_app/views/public_workout_views.py` — manter a montagem do snapshot em lote; alterar apenas se o contrato do contexto precisar de ajuste.
- `public_workouts/templatetags/public_workouts_extras.py` — ampliar a representação dos pontos da curva para a lista detalhada.
- `templates/public_workouts/workout.html` — semântica, estados e composição da seção de cargas.
- `static/css/public_workouts/workout-shell.css` — estilos locais, responsividade, safe area e remoção controlada de duplicação.
- `static/js/public_workouts/load_tracker.js` — somente interações acessíveis e feedback do fluxo de registro, preservando o contrato atual.
- `public_workouts/test_workout_template.py`, `public_workouts/test_workout_template_real_clients.py`, `public_workouts/test_progress_snapshot.py` e testes de endpoint existentes — cobertura funcional na implementação.

Não criar endpoint novo, biblioteca de gráfico ou migration para esta entrega.

## 3. Contrato de dados para a interface

### 3.1 DTO de movimento

Cada movimento exibido na lista deve continuar derivado do snapshot atual. O helper/template tag pode compor um DTO de apresentação semelhante a:

```text
movement_progress = {
  movement_id,
  movement_name,
  latest_top_set: { date, weight, reps, rir },
  trend: { signal, delta, window_label },
  chart: { available, points, legacy_points, y_scale },
  records: { current_record, has_record },
  history_state,
  sessions: [ { date, weight, reps, rir, program_id, week_in_program } ]
}
```

É uma estrutura semântica de apresentação, não uma nova fonte de verdade. Usar as classes/estruturas já existentes se o projeto já definir um tipo apropriado; evitar duplicar DTO desnecessariamente.

### 3.2 Regras do contrato

- `sessions` deve usar os `curve_points` já filtrados e ordenados pelo snapshot. Não reconstruir série a partir de `load_history` bruto.
- Incluir em cada ponto `reps`, `rir`, `program_id` e `week_in_program` se estiverem disponíveis no `ProgressPoint`.
- Se algum campo histórico estiver ausente, omitir a métrica em vez de exibir zero ou inventar um valor.
- A curva deve usar o mesmo peso e mesma série de pontos que o estado de tendência e o resumo. Não calcular “último” de modo diferente no template.
- `legacy_points` permanece visualmente neutro, com legenda explícita de histórico anterior sem comparabilidade. Não usar como ponto de início da linha atual.
- Preservar janelas, frescor, desempate e critérios de elegibilidade já definidos nos planos de domínio.
- Dados de série ficam num único snapshot em lote por conta. Nenhuma busca por movimento, no helper ou no template.

### 3.3 Definição de “sessão” nesta entrega

Na primeira versão, “Ver sessões” significa ver os registros elegíveis ordenados por data, com no máximo o top set efetivo daquele exercício em cada dia conforme o modelo atual. O produto não deve sugerir que distingue dois treinos do mesmo exercício no mesmo dia.

Para curvas realmente por sessão, com múltiplas sessões no mesmo dia, o domínio precisará de uma evolução separada: identificador de sessão de treino, captura temporal e revisão de idempotência/edição. Essa mudança exige proposta de dados própria e não é pré-requisito para melhorar a experiência atual.

## 4. Arquitetura de interação e estados

### 4.1 Resumo compacto por movimento

Cada linha/cartão prioriza:

1. nome do exercício e contexto curto;
2. última carga válida, com reps e RIR quando conhecidos;
3. sinal de evolução e janela usada, quando sustentados pelos dados;
4. mini curva apenas quando houver pelo menos dois pontos comparáveis;
5. ação “Ver sessões” quando existir histórico detalhável;
6. affordance de registro já existente, sem criar CTA concorrente.

Evitar colocar recorde, estimativa de 1RM, variação, ciclo e curva simultaneamente no cabeçalho do card. Informações secundárias devem ficar em detalhe ou na área já dedicada a resumo de ciclo/recorde.

### 4.2 Estados de histórico

| Estado | Critério | Apresentação |
|---|---|---|
| Sem histórico | Sem pontos atuais nem legado | Texto acolhedor e instrução curta para registrar a primeira carga; sem gráfico vazio |
| Apenas histórico legado | Existe histórico, sem top set comparável | Valor histórico identificado como legado; explicar que novos registros iniciam a curva comparável |
| Um ponto atual | Há último top set, mas ainda não há curva | Mostrar última carga e “registre novamente para começar a comparar”; sem seta de tendência |
| Curva disponível | Dois ou mais pontos atuais elegíveis | Mini curva, sinal existente e ação de detalhes |
| Estado de recorde | Regra existente identifica PR | Destaque acessível e breve; não substituir o resumo de carga nem repetir celebração persistentemente |
| Sem recorde disponível | Nenhum recorde calculável | Estado explícito e compacto; não deixar uma seção aparentemente quebrada/vazia |

“Melhorou”, “manteve” e “reduziu” só podem vir da classificação atual do snapshot. Não inferir estado a partir da cor ou da comparação manual do template.

### 4.3 Detalhe “Ver sessões”

- Preferir `<details>/<summary>` se funcionar no padrão do projeto e não interferir com navegação/accordion existente; caso contrário, usar botão com `aria-expanded` e região identificada.
- Lista cronológica acessível com data, carga, reps e RIR disponível.
- A curva detalhada e a lista devem referir a mesma série. Tooltip não deve ser o único local dos valores.
- Em mobile, detalhes em fluxo vertical; sem modal obrigatório ou scroll horizontal.
- Se não houver curva (zero/um ponto), a ação não deve prometer gráfico; pode abrir uma lista quando existir ponto/histórico.

### 4.4 Hierarquia da seção

Sequência proposta:

1. cabeçalho “Evolução de carga” com resumo curto;
2. lista de exercícios e seu progresso;
3. estados vazios/legado no contexto do exercício;
4. “Seus recordes” e resumo do ciclo como blocos secundários já existentes;
5. revisão semanal abaixo da evolução ou recolhida, dependendo do comportamento atual e dos dados disponíveis.

Antes de mover blocos, verificar eventos, âncoras, testes de template e uso por leitores de tela. Evitar apresentar dois resumos concorrentes no topo.

## 5. Formulário de registro e feedback

### 5.1 Agrupamento visual

- Dar nome inequívoco ao formulário: “Registrar carga de hoje”.
- Agrupar controles em ordem de execução: carga, repetições, RIR opcional, tipo de série (aquecimento/top set) e observações se já existirem.
- Deixar claro que o toggle de aquecimento altera `set_role`; não tratar aquecimento como um segundo top set.
- Reduzir o espaço visual entre checkbox e rótulo, sem reduzir área clicável. Controles de toque devem ter alvo confortável e rótulos associados.
- Manter sugestão/unidade e calculadora de anilhas existentes; não reimplementar matemática na UI.

### 5.2 Feedback de estado

- Salvo: confirmação junto ao formulário e atualização do resumo/curva, sem depender apenas de toast.
- Salvamento em andamento: desabilitar submissão duplicada de forma temporária, mantendo a página utilizável.
- Offline/pendente: comunicar claramente que o registro será sincronizado e preservar o comportamento de fila atual.
- Erro de validação/rede: mensagem ligada ao campo ou formulário, com tentativa de novo envio sem apagar valores.
- Correção do dia: informar que o registro atual daquele exercício/dia foi atualizado, se esse já for o comportamento do endpoint.
- Usar região `aria-live="polite"` para feedback assíncrono e foco previsível após erro.

Não alterar chave idempotente, política de uma linha ativa por exercício/dia, serialização de `set_role` ou comportamento de outbox nesta tarefa.

## 6. Direção visual e CSS

- Aplicar o tema oficial OctoBox: base escura profunda, superfícies em camadas, tipografia legível e acento neon contido para estado ativo. O destaque não deve competir com o número da carga.
- Usar tokens existentes para cor, raio, sombra, espaçamento e foco. Não criar uma paleta local paralela.
- Diferenciar informação por hierarquia tipográfica, espaço e rótulos, além de cor.
- Garantir contraste nos estados positivo, neutro, redução, legado, carregamento e erro; testar modo claro/escuro se suportado por esta tela.
- Gráfico SVG atual deve continuar leve e sem dependência. Melhorar escala, contraste e legibilidade dos rótulos; evitar labels de eixo minúsculos e grades dominantes.
- Respeitar `prefers-reduced-motion`; microanimações devem ser curtas, funcionais e opcionais.
- Corrigir a sobreposição da navegação fixa: reservar espaço inferior suficiente no conteúdo, incorporando `safe-area-inset-bottom`; verificar teclado virtual e foco. Não esconder campos atrás da barra.
- O CSS de gráfico tem seletores repetidos em blocos distintos. Consolidar somente depois de comparar a cascata efetiva e regras mobile/dark; nenhuma remoção baseada apenas em busca textual.
- Manter regras da tela em `workout-shell.css`; promover token/primitiva global apenas se for realmente compartilhada.

## 7. Plano de implementação por fases

### Fase 0 — Preparação e baseline

1. Confirmar o branch e registrar o diff existente antes de editar.
2. Preservar as alterações de billing portal atualmente presentes em `workout.html`, `workout-shell.css`, `public_workout_views.py` e testes. Revisar o diff antes de integrar mudanças na mesma área.
3. Fazer captura de referência da seção em desktop e larguras móveis, incluindo formulário aberto, navegação inferior e estados reais dos dados.
4. Confirmar pontos de entrada de CSS/JS e hooks DOM efetivamente usados no template.

**Saída:** baseline com screenshots e mapa dos hooks que não podem ser renomeados sem atualizar JS/testes.

### Fase 1 — Corrigir o fluxo de registro no mobile

1. Reservar padding inferior ao conteúdo conforme altura real da navegação e safe area.
2. Verificar formulário aberto com teclado numérico visível, último campo e botão salvar.
3. Ajustar agrupamento, espaçamento e rótulos do toggle de aquecimento.
4. Adicionar/ajustar feedback acessível dos estados de envio sem alterar contrato de rede.

**Saída:** fluxo de carga operável sem campos cobertos ou perda de contexto.

### Fase 2 — Estabelecer hierarquia e estados de evolução

1. Revisar os blocos já presentes e sua ordem com base em testes e uso real.
2. Implementar cabeçalho enxuto e resumo por exercício.
3. Tratar explicitamente sem histórico, legado, um ponto e curva disponível.
4. Tratar estado vazio de recordes e resumo de ciclo para não parecer erro de renderização.
5. Manter `trend_signal` como fonte única do estado de tendência.

**Saída:** todo exercício comunica o que se sabe e o que ainda não é possível concluir.

### Fase 3 — Curva e sessões detalhadas

1. Ampliar a tag/helper para incluir reps, RIR e contexto de programa/semanas disponíveis no snapshot.
2. Criar mini curva SVG somente para série comparável com dados suficientes.
3. Adicionar detalhe “Ver sessões” acessível com valores explícitos e ordenação consistente.
4. Manter histórico legado separado e documentar que a série é por data/top set efetivo, não por múltiplos treinos no mesmo dia.
5. Garantir que mini gráfico, lista, último valor e tendência consumam a mesma estrutura.

**Saída:** curva legível e auditável, com detalhe sem endpoint/consulta nova.

### Fase 4 — Polimento visual e responsivo

1. Refinar hierarquia tipográfica, cores, superfícies, foco e estados visuais com tokens do design system.
2. Ajustar SVG, legendas e escalas em cards estreitos.
3. Consolidar duplicações comprovadas no CSS, preservando media queries e modos de tema.
4. Revisar movimento reduzido e ausência de dependência gráfica adicional.

**Saída:** visual coerente com o produto e com leitura rápida em telas pequenas.

### Fase 5 — Verificação e rollout

1. Executar testes direcionados de template, snapshots e endpoint/fluxo de registro.
2. Revisar o diff completo para confirmar preservação dos arquivos de billing em andamento.
3. Fazer QA visual nas dimensões e estados da matriz abaixo.
4. Caso bundles/PWA estejam versionados para esta tela, seguir o mecanismo atual de cache/versionamento e confirmar que usuários recebem CSS/JS novos.

**Saída:** PR com screenshots antes/depois, notas de estado de dados e testes executados.

## 8. Critérios de aceite

- O aluno consegue distinguir carga mais recente, reps/RIR disponíveis e tendência sem abrir detalhe.
- Nenhuma seta ou estado de melhora aparece com um único ponto ou dados insuficientes.
- A série comparável e o legado nunca se conectam como se fossem uma curva contínua.
- “Ver sessões” lista exatamente os pontos usados no gráfico e não faz consulta por exercício.
- Sem histórico, legado, um ponto e recorde indisponível têm mensagens coerentes e não deixam cards vazios sem explicação.
- Registro, correção do dia, aquecimento e top set mantêm os contratos existentes.
- O formulário não fica coberto pela navegação em nenhuma viewport móvel suportada.
- Feedback de envio pode ser percebido por teclado/leitor de tela e mantém os dados digitados em caso de falha.
- Não há regressão nas rotas públicas de treino, no resumo do ciclo ou na captura/compartilhamento já implementados.
- Não se adiciona consulta ORM por card, migration ou biblioteca de gráficos.

## 9. Matriz de validação

### Dados e estados

- sem logs;
- somente logs legados;
- um top set atual;
- dois ou mais pontos comparáveis;
- tendência crescente, estável, decrescente e sem sinal;
- recorde calculável e indisponível;
- registro novo, correção no mesmo dia, série de aquecimento;
- envio online, erro de rede e sincronização pendente, se suportada pelo fluxo atual.

### Interface

- 320/360/390 px, tablet e desktop;
- formulário aberto com teclado numérico;
- safe area inferior em dispositivo iOS;
- navegação inferior com rolagem até o último controle;
- tema claro/escuro suportado;
- foco visível, navegação só por teclado e leitor de tela;
- movimento reduzido.

### Regressão funcional

- `public_workouts/test_workout_template.py`;
- `public_workouts/test_workout_template_real_clients.py`;
- `public_workouts/test_progress_snapshot.py`;
- testes existentes do endpoint de registro/correção e jornadas E2E pertinentes.

## 10. Riscos e decisões explícitas

1. **“Sessão” pode induzir uma promessa maior que os dados atuais.** A interface deve chamar a lista de sessões por data/registro ou explicar seu agrupamento; separar multi-sessão no mesmo dia para uma evolução de domínio futura.
2. **Vários blocos já existem na tela.** A implementação deve reorganizar com cuidado, sem apagar métricas que outras jornadas usam. A lista por movimento é o primeiro nível; detalhe e blocos secundários carregam o restante.
3. **Legado não é comparável ao histórico tipado.** A separação visual é requisito de honestidade dos dados, não uma preferência estética.
4. **O snapshot é a fronteira de performance e consistência.** Alterar somente sua representação de saída; não replicar agregação em template/JS.
5. **Há trabalho de billing não relacionado no worktree.** O plano exige preservar e reconciliar esse diff antes de editar os mesmos arquivos; não descartar, sobrescrever ou misturar sem revisão.
6. **Escopo não inclui multi-sessão real.** Se o produto precisar distinguir sessões no mesmo dia, abrir plano separado para `training_session_id`, timestamps, edição e idempotência antes de alterar semântica ou persistência.

## 11. Sequência sugerida de PRs

Para revisão e rollback simples, dividir em:

1. **PR A — Mobile e acessibilidade do registro:** safe area, agrupamento do formulário e feedback.
2. **PR B — Hierarquia e estados de carga:** cards compactos e estados de histórico/recorde/ciclo.
3. **PR C — Curva e lista de sessões:** extensão do payload do snapshot, detalhe acessível e SVG.
4. **PR D — Polimento/limpeza CSS:** consolidação baseada em evidência e QA visual final.

Se o diff ficar pequeno e os mesmos arquivos precisarem de coordenação, B e C podem ser combinados, desde que payload e apresentação sejam revistos no mesmo PR. O fluxo de registro deve poder ser revisado isoladamente.

## 12. Referências internas

- `docs/plans/curva-grafico-hierarquia-e-set-role.md` — contrato de elegibilidade e comparabilidade da curva.
- `docs/plans/curva-grafico-hierarquia-e-set-role-overview.md` — estado implementado e decisões relacionadas.
- `docs/plans/curva-carga-completa-reps-rir-recorde-plan.md` — reps, RIR, recorde e contexto do ciclo.
- `docs/plans/front-end-restructuring-guide.md` — ownership e organização de front-end.
- `docs/reference/front-end-ownership-map.md` — caminho de ownership dos arquivos.
- `docs/reference/design-system-contract.md` — tokens e contratos visuais.

## 13. Implementação e validação

- O cartão de carga mantém o último registro, sinal/tendência do snapshot, curva comparável e detalhes da lista de pontos; histórico legado continua separado.
- Os pontos expõem reps e RIR já disponíveis no snapshot, sem consulta por exercício. Recordes inválidos/ausentes e histórico só de aquecimento têm estados explícitos.
- O formulário conserva os contratos de correção por `set_role`, top set e aquecimento; seleção de carga não muda a idempotência nem a fila offline.
- A suite direcionada executou 245 testes com PostgreSQL temporário limpo: template, clientes reais, dashboard, snapshots e versão de assets. Sintaxe dos scripts e Python, além de `git diff --check`, também passaram.
- QA visual autenticado nos tamanhos/temas da matriz e smoke offline numa instalação PWA existente continuam pendentes.
