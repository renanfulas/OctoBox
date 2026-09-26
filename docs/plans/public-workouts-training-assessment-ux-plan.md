# Plano técnico — Treino e avaliação física do aluno

**Status:** implementação aplicada; validação final de viewport e PWA instalada continua pendente
**Escopo:** `/renan/<slug>` no template unificado `workout.html`
**Direção visual:** Luxo Futurista 2050, com hierarquia e clareza antes de efeitos
**Plano relacionado:** [Evolução de carga](public-workouts-load-progress-ux-technical-plan.md)

## 1. Objetivo

Facilitar duas tarefas do aluno:

1. saber qual treino deve fazer hoje, entender a prescrição e registrar o que executou;
2. iniciar uma avaliação física, entender quais medidas são úteis e acompanhar mudanças sem confundir estimativas com diagnóstico.

O trabalho evolui a fachada existente. Não troca as regras de prescrição, cálculo de carga, persistência de treinos ou fórmulas de avaliação por decisões de interface.

## 2. Auditoria e riscos confirmados

### P1 — treino abre no primeiro dia, mesmo quando não é o treino de hoje

Na tela real consultada em 26/09/2026, sábado, a aba Treino abriu em `TER`, apesar de existir um dia `SÁB` no programa. O template marca `forloop.first` como dia selecionado e define o primeiro dia como painel padrão. Entrar diretamente pela navegação inferior, portanto, pode levar o aluno ao treino errado para aquele dia.

**Direção:** determinar o dia inicial pela data local da página e pelo calendário do programa. Se hoje for descanso, mostrar esse estado e o próximo dia prescrito, sem selecionar silenciosamente um treino diferente. Continuar permitindo escolha manual e acesso pelos atalhos de “Sua semana”.

### P1 — card de exercício reúne controles interativos aninhados

O `article` do exercício tem `role="button"` e contém links e outros controles de variação/glossário. O snapshot de acessibilidade confirma esses controles como descendentes do botão. Isso torna o modelo de teclado e leitor de tela ambíguo e obriga handlers a filtrar cliques propagados.

**Direção:** deixar o card como conteúdo sem papel de botão; criar um botão próprio “Registrar série/carga” com estado `aria-expanded` e associação explícita ao formulário. Links de referência, glossário e variações permanecem controles independentes.

### P1 — fase global e prescrição por exercício parecem contraditórias

Na sessão observada, o banner mostrava alvo de 3–6 reps e RIR 0,5, enquanto os exercícios exibiam, por exemplo, Top 6–8 com RIR 1–2, e faixas de 8–15 em outros movimentos. Pode ser uma diferença legítima entre fase e prescrição individual; a interface não a explica.

**Direção:** antes de mudar qualquer cálculo, confirmar com a fonte da prescrição qual regra vale por exercício. Depois, nomear o banner como foco geral da semana ou exibir a meta específica de cada exercício. Se os valores realmente divergirem, corrigir o contrato de dados junto com a regra de domínio.

### P2 — ação e estado da carga não ficam inequívocos

O resumo lateral “Livre” pode ser lido como tipo de equipamento ou como falta de carga definida. A instrução para registrar aparece pequena, em itálico e espremida ao lado do conteúdo. O aluno precisa perceber que pode abrir o registro e o que vai encontrar ali.

**Direção:** usar rótulos semanticamente distintos, por exemplo “Sem carga sugerida” quando não há valor calculado, “Carga sugerida” quando há prescrição e “Última sessão” quando existe histórico. Dar à ação um controle visível.

### P2 — formulário de carga cresce como uma fila de controles

Ao expandir um exercício, escolha de variação, carga, salvar, aquecimento, reps, RIR e calculadora convivem no mesmo grupo flexível. A informação útil para a série fica sem agrupamento visual claro.

**Direção:** organizar o conteúdo em três grupos: exercício/carga e reps; classificação da série; esforço e ferramentas opcionais. Deixar RIR e calculadora recolhidos por padrão. Variações devem ser nomeadas como substituição do exercício, sem parecer uma opção da mesma série.

### P2 — primeiro uso da avaliação não explica o resultado

O estado vazio atual é uma frase isolada após o formulário. Ele não explica quais entradas geram quais indicadores nem prepara o aluno para a próxima medição. O relatório só desenha a curva de peso com pelo menos dois pontos.

**Direção:** integrar a ausência de histórico ao formulário de primeira avaliação, explicar os dados necessários para cada indicador e indicar que a primeira entrada cria a linha de base. Após o primeiro registro, não mostrar um gráfico vazio; explicar que uma segunda avaliação permitirá comparar a tendência.

### P2 — escalas tipográficas e acentos não seguem uma única hierarquia

Na tela atual, há rótulos de 10–11,5 px em `assessments.css`, e o botão principal de Avaliação aparece verde enquanto a navegação e Treinos usam azul/ciano. O tema OctoBox reserva as cores semânticas para estados; o verde de sucesso não deve substituir a cor da ação principal.

**Direção:** levar texto de interface e dados a pelo menos 13 px quando legibilidade permitir; alinhar CTA e foco aos tokens de marca e reservar verde/âmbar/vermelho aos estados. Manter contraste equivalente nos modos claro e escuro.

## 3. Inventário técnico e ownership

O caminho observado é:

1. `student_app/views/public_workout_views.py` resolve o programa e os assets do corredor;
2. `templates/public_workouts/workout.html` monta navegação, dias, movimentos e o host da avaliação;
3. `static/css/public_workouts/workout-shell.css` concentra estilos do template unificado;
4. `static/css/public_workouts/assessments.css` é compartilhado com os templates legados;
5. um script inline em `workout.html` implementa tabs/ciclo, atalhos, abertura de registro, variações, glossário e saída da conta;
6. `load_tracker.js` controla entrada, validação, correção, RIR, ferramentas de anilha, substituições, rascunhos, outbox offline e compartilhamento;
7. `assessments.js` monta formulário e relatório, lê o endpoint JSON e envia avaliações;
8. `public_workouts.services` e endpoints mantêm a verdade de prescrição, carga e avaliação.

Os componentes partem de `student-card`, `card-decor-topstripe` e tokens temáticos. Mudanças locais devem continuar no domínio `public_workouts`; não repintar o card global nem criar uma segunda paleta.

## 4. Decisão de split CSS e JavaScript

### CSS: fazer split planejado, em uma etapa mecânica separada do redesign

`workout-shell.css` tem aproximadamente 1.768 linhas e hoje reúne navegação, treino, formulários, curva de cargas, cardio, periodização e perfil. O arquivo é local ao template novo e já tem seções, mas a largura de responsabilidade vai dificultar revisão da próxima evolução.

Arquivos-alvo:

- `workout-shell.css`: topo, estrutura dos painéis, navegação e componentes gerais do shell;
- `workout-training.css`: banner da fase, dias, movimentos, registro de série, glossário e ferramentas do treino;
- `workout-progress.css`: curva, registros, recordes e elementos de progresso reaproveitados entre os painéis;
- `assessments.css`: manter como base compartilhada do relatório legado;
- `workout-assessment.css`: somente refinamentos do template unificado, sempre sob um wrapper de página/classe semântica própria.

Regras de migração:

1. primeiro mover regras existentes sem redesenhar; evitar que um diff visual grande esconda uma quebra de cascata;
2. manter a ordem efetiva de declaração dos seletores. Regras hoje distribuídas entre base e `@media` não podem ser copiadas ao fim sem conferir quem vence;
3. não duplicar seletores em arquivo antigo e novo para “testar” uma versão: isso cria duas autoridades e resultados dependentes da ordem dos `<link>`;
4. manter ajustes de `prefers-reduced-motion`, breakpoints e foco junto do componente a que pertencem;
5. incluir novos arquivos depois dos estilos base e verificar os estilos efetivamente servidos pela rota.

O CSS de avaliações é pequeno (cerca de 198 linhas), mas é carregado por páginas legadas. Não mover nem renomear sua base nesta frente; adicionar estilos da nova experiência em `workout-assessment.css`, carregar apenas no template unificado e usar seletores com escopo explícito. Assim, a evolução não altera clientes ainda servidos pelo HTML antigo.

### JavaScript: extrair o script inline; não dividir `load_tracker.js` neste ciclo

O script inline no template tem cerca de 270 linhas e mistura navegação, interações locais e saída da conta com o markup. Ele deve virar `static/js/public_workouts/workout-shell.js`, inicializado como asset `defer`. A extração será um movimento de código antes do redesenho.

`load_tracker.js` tem cerca de 1.328 linhas, mas seus recursos compartilham estado e contratos do registro — validação, RIR, chaves de idempotência, correção por tipo de série, drafts, outbox offline e chamadas de API. Dividi-lo junto com a mudança visual elevaria bastante o risco. Mantê-lo inteiro na primeira entrega; decidir um split próprio após inventário de funções, com API de inicialização explícita e sem estado global duplicado.

`assessments.js` tem cerca de 820 linhas e atende a avaliação unificada e páginas legadas. Preservar sua responsabilidade de carregar/salvar dados e produzir o relatório. Alterar apenas os pontos de composição necessários e manter um único dono de fetch, validação e submissão. Não criar um segundo formulário nem um segundo POST no novo script.

## 5. Contratos frágeis que precisam de proteção

### Registro de carga

- O card e o elemento `[data-workout-load-input]` são irmãos adjacentes; `workout.html`/JS usam `card.nextElementSibling`. Ao extrair o card para include, não inserir wrapper ou separador entre eles sem trocar o contrato do JS.
- As chaves e valores do dia são separados para `top_set` e `warmup`. Alternar o tipo deve continuar hidratando o registro correto; jamais sobrescrever o aquecimento com carga/reps/RIR da série principal.
- Salvar mantém idempotência e a semântica de correção do servidor. Não gerar uma nova chave durante retry offline nem marcar registro local como confirmado antes do POST aceitar.
- Rascunhos, IndexedDB/outbox, retorno online, resposta 401/409 e bloqueio de duplo clique são comportamento de produto, não detalhes visuais descartáveis.
- A navegação de exercício, teclado numérico e esconder a barra inferior não podem engolir foco nem deixar a tela sem ação de retorno.

### Navegação

- Tabs superiores e dias do programa são níveis aninhados. O estado selecionado deve ser escopado ao respectivo `data-workout-tab-nav`; alterar o ciclo Treino/Cardio/Periodização não deve apagar o dia selecionado.
- Atalhos “Sua semana” precisam abrir Treino e o dia correspondente, não avançar o ciclo para Cardio ou Periodização.
- Seleção por data depende do fuso/data local coerente com `week_overview`; tratar programa sem treino hoje, programa sem dias e mudança de semana.
- Novo botão “Registrar” deve anunciar estado expandido/recolhido e controlar o painel correto sem depender da classe visual.

### Avaliação

- Preservar autenticação, escopo por `plan_slug`, validações da API e a captura de erros 401/rede/servidor.
- Manter métodos e fonte do percentual de gordura explícitos. Medidas estimadas continuam descritas como estimativas; a interface não deve rotular dados como diagnóstico.
- Não alterar as fórmulas, critérios de liberação de dobras ou dados pessoais como parte de um ajuste de UI.
- Formulário e relatório são montados dinamicamente. Evitar `id` duplicado quando navegação ou renderização reaproveita os slots; manter estados distintos de carregando, vazio e erro.

### PWA e cache

Os assets da página unificada são separados de `PUBLIC_WORKOUT_STYLESHEETS`/`PUBLIC_WORKOUT_SCRIPTS` para não vazar CSS e JS às páginas legadas. Qualquer novo asset unificado precisa entrar em:

1. `<link>`/`<script>` do `workout.html`;
2. `PUBLIC_WORKOUT_UNIFIED_TEMPLATE_STYLESHEETS` ou `_SCRIPTS` em `public_workout_views.py`;
3. composição de `static_asset_urls` do service worker;
4. contrato de testes de asset e incremento de `PUBLIC_WORKOUT_CACHE_EPOCH` quando o cliente instalado precisar atualizar.

Risco identificado: `public_workout_asset_version()` calcula a versão usando as listas legadas, não as listas `UNIFIED_TEMPLATE_*`. Não confiar nesse valor sozinho para invalidar um novo asset unificado. A etapa de release deve provar que aparelho já instalado baixa a nova versão e mantém o acesso offline; se a estratégia de versão mudar, incluir isso como correção explícita, com teste, não como detalhe implícito do split.

## 6. Achados de forense CSS e tratamento

Uma varredura direcionada dos arquivos de Treino/Avaliação encontrou:

- zero declarações `!important` nesses estilos;
- zero blocos `<style>` no template;
- sete atributos `style` no template, todos dirigidos por dados do gráfico de periodização ou por gradientes SVG. A posição do tooltip de glossário também é calculada em runtime no JS. São estilos dinâmicos/geométricos conhecidos, não licença para adicionar decoração inline;
- seletores repetidos que coincidem com `@media`, `prefers-reduced-motion` e ajustes para telas pequenas. São candidatos a manter até provar o contrário, não duplicações para apagar automaticamente;
- candidatos de seletor “não usado” e overrides em volume alto. A heurística não interpreta classes dinâmicas (`phase`/estado), strings montadas por JS, `{% include %}` e outros templates legados que não estavam no recorte. Não remover nada com base nesse relatório isolado.

Antes de mover CSS, classificar cada bloco como base, breakpoint, estado reduzido, regra de compatibilidade ou override. Comparar o resultado calculado e capturas da tela nos dois temas. Nenhum seletor de `assessments.css` será aposentado sem procurar seus consumidores nos templates legados.

## 7. Plano de implementação por ondas

### Onda 0 — baseline e contratos

1. Capturar tela inicial, treino de hoje, expansão do formulário, avaliação vazia e avaliação com histórico em tema claro/escuro.
2. Criar casos de fixture: treino hoje, descanso hoje, primeiro e último dia, carga sugerida, carga livre, registro top-set/aquecimento e avaliação com zero, um e múltiplos registros.
3. Fixar a cadeia template → assets → view/cache → endpoints e anotar as páginas legadas que compartilham `assessments.css` e `assessments.js`.

**Pronto quando:** a captura e os contratos conhecidos tornam uma regressão comparável, sem mudar o comportamento ainda.

### Onda 1 — correções de navegação, hierarquia sem mudança de cálculo

1. Pré-selecionar o dia de hoje quando houver treino; definir o estado para descanso e fallback.
2. Clarificar fase geral e prescrição por exercício depois da verificação com a fonte do programa.
3. Separar card semântico da ação Registrar; atualizar controles, teclado, foco e atributos ARIA.
4. Clarificar ausência de sugestão de carga e remover o texto lateral estreito como CTA.

**Pronto quando:** Treino direto e atalhos semanais levam ao mesmo dia correto; exercícios não têm controles interativos aninhados; teclado e leitor de tela identificam a ação e seu estado.

### Onda 2 — extração mecânica do front-end

1. Extrair o IIFE inline para `workout-shell.js`, sem reescrever seus handlers.
2. Mover o markup repetido de dia/movimento/formulário para includes Django sem mudar ordem dos irmãos necessários ao tracker.
3. Extrair regras de Treinos de `workout-shell.css` para `workout-training.css` como alteração separada, sem redefinir valores no mesmo diff.
4. Criar um wrapper estável para avaliação unificada; adicionar `workout-assessment.css` para regras exclusivas dessa versão.
5. Atualizar assets do template, cache/precache, versão offline e testes de integração de assets.

**Pronto quando:** a aparência e o comportamento antes/depois da extração são equivalentes nos estados cobertos e nenhum asset é enviado às páginas legadas sem intenção.

### Onda 3 — experiência de treino

1. Compor o cabeçalho do treino do dia com dia/foco/fase e orientação curta.
2. Reorganizar seletor de dias com estado “hoje”, conclusão e rolagem acessível.
3. Atualizar cada movimento para nome e prescrição primeiro, carga/última sessão depois e ação principal visível.
4. Agrupar o registro em execução, classificação da série e opções; manter aquecimento, reps, RIR e substituição associados corretamente.
5. Integrar “Ver evolução” à curva/sessões da iniciativa de cargas sem colocar um gráfico por exercício na lista principal.
6. Usar variantes de intensidade para superfície de decisão, contexto e apoio; reservar o acento forte ao estado/ação que guia o próximo passo.

**Pronto quando:** o aluno consegue identificar em poucos segundos o dia, exercício, meta e ação; conteúdo permanece legível com curva/histórico vazio e cheio.

### Onda 4 — experiência de avaliação

1. Primeiro uso: estado guiado integrado ao início do formulário, passos mínimos e explicação do que cada dado gera.
2. Histórico: resumo e tendência primeiro; “Nova avaliação” acessível sem manter um formulário longo no topo.
3. Tornar rótulos, unidades, data e grupos de medidas legíveis em telas estreitas.
4. Curva vazia/uma entrada: explicar linha de base e quando a comparação aparecerá.
5. Rotular fonte e incerteza dos indicadores junto ao valor que depende dela.
6. Manter paleta, componentes e CTA na família OctoBox, sem semântica de saúde baseada só em cor.

**Pronto quando:** primeiro registro é compreensível sem histórico; histórico existente continua navegável; estimativas e observações têm origem e contexto explícitos.

### Onda 5 — validação e liberação

1. Testes de renderização/payload para dias e fases; testes de interação do HTML/JS para dias, expandir/recolher, variações e tab aninhada.
2. Testes do contrato de carga para top-set, aquecimento, correção, duplo toque, drafts/offline e retorno de rede.
3. Testes de avaliação vazia, baseline, múltiplos registros, erros HTTP e preservação dos consumidores legados.
4. Verificação visual em 360, 390, 768 e 1280 px, em claro/escuro, com zoom de texto e `prefers-reduced-motion`.
5. Smoke do service worker em instalação nova e instalação já ativa, online e offline.
6. Conferir foco visível, leitura de unidade/estado, contraste e ausência de overflow horizontal.

**Pronto quando:** todos os fluxos passam; comparações visuais não mostram regressão; a página e assets atualizados chegam também ao cliente PWA instalado.

## 8. Critérios visuais e funcionais de aceite

- conteúdo e próxima ação vencem os filetes, chips e brilho nos primeiros segundos;
- cards não usam o mesmo nível de acento para prescrição, apoio e ação;
- texto funcional e dados não ficam abaixo de 13 px sem justificativa para elementos vetoriais;
- uma única ação primária por região; variação, glossário e RIR não concorrem com ela;
- painel Treino informa descanso/treino do dia e não depende de lembrar que o primeiro item da lista é o correto;
- `aria-expanded`, `aria-controls`, `role=tab`, foco e elementos interativos correspondem ao estado visível;
- gráfico de avaliação só comunica comparação quando existem observações suficientes;
- HTML de páginas legadas, fórmulas de avaliação, autorização, idempotência, outbox e contrato de dados continuam intactos.

## 9. Decisões aplicadas e validações restantes

1. A faixa da fase passou a se chamar **Foco geral da semana** e explica que a prescrição de cada exercício continua sendo a referência principal. Cálculos e valores do domínio não foram alterados.
2. Em dia de descanso, a tela informa o próximo dia prescrito e o deixa selecionado como prévia. Em dia com treino, seleciona o dia local correspondente.
3. A avaliação não recomenda uma cadência fixa; a mensagem de primeira medição explica a linha de base sem sugerir intervalo.
4. A época do cache PWA foi incrementada e os novos CSS/JS entraram no precache. Confirmar uma instalação existente, incluindo abertura offline, após o deploy.
5. O render e os assets locais foram verificados; falta conferir visualmente 360, 390, 768 e 1280 px, claro/escuro e `prefers-reduced-motion` num navegador autenticado.

## 10. Referências de implementação

- template principal: `templates/public_workouts/workout.html`
- view/assets/PWA: `student_app/views/public_workout_views.py`
- CSS unificado atual: `static/css/public_workouts/workout-shell.css`
- CSS compartilhado da avaliação: `static/css/public_workouts/assessments.css`
- tracker de carga/offline: `static/js/public_workouts/load_tracker.js`
- renderização e escrita da avaliação: `static/js/public_workouts/assessments.js`
- verdade de cálculos e relatórios: `public_workouts/services.py`
- regras atuais de direção: `docs/architecture/themeOctoBox.md`, `docs/experience/css-guide.md` e `docs/reference/front-end-ownership-map.md`

## 11. Implementação aplicada em 26/09/2026

- A seleção de dia usa `timezone.localdate()` compartilhada com o resumo semanal, evitando divergência na virada do dia. A função pura cobre treino hoje, descanso com próximo treino e programa vazio.
- O `article` do exercício deixou de agir como botão. “Registrar carga” é um botão nativo ligado ao widget por `aria-controls`; variação continua em seu controle próprio. O vínculo explícito substitui a dependência de `nextElementSibling`.
- “Livre” foi substituído por “Sem carga prescrita”, com texto de ação mais claro. A faixa global foi contextualizada sem tocar na periodização.
- `workout-training.css`, `workout-progress.css` e `workout-assessment.css` separam as responsabilidades do fluxo unificado. A avaliação permanece isolada dos 10 templates legados.
- O JavaScript inline de navegação e microinterações foi extraído para `workout-shell.js`. O tracker de carga foi mantido; o widget ainda preserva sua posição no DOM e os contratos de registro.
- A avaliação agora explica o primeiro uso, diferencia linha de base de histórico e ordena relatório antes do formulário quando já existem dados. “Nova avaliação” leva o foco ao formulário.
- CSS/JS unificados receberam versão de asset, entraram no precache do service worker e elevaram a época do cache.
- Validação executada: 245 testes direcionados passaram em banco PostgreSQL temporário e isolado, cobrindo dashboard, template, clientes reais, snapshots de progresso e versão de assets. Também passaram `node --check` nos três scripts alterados, `py_compile` nos módulos Python e `git diff --check`. Continua pendente a conferência visual autenticada nos viewports e temas da matriz acima e a validação offline numa instalação PWA já ativa.
