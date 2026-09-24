<!--
ARQUIVO: plano de produto, UI/UX e implementação do registro de carga da Curva.
STATUS: Revisão 2 — proposta revisada em 24/09/2026; ainda não implementada.
ESCOPO: registro rápido no corredor /renan/<slug>, endpoint /carga.
DEPENDÊNCIA: celebração exige set_role e políticas do plano de hierarquia em produção.
FRONTEIRA: evoluir PublicWorkoutLoadLog e consumidores existentes; sem app paralelo.
ENTREGA DESTA REVISÃO: documento; não altera o aplicativo em produção.
-->

# Curva — registrar com facilidade, continuar o treino com confiança

## 0. Decisão de produto

**O registro deve ocupar poucos segundos do intervalo e deixar três coisas claras: o que fiz, se ficou guardado e como corrigir.** A qualidade percebida vem da precisão da interação, da legibilidade e da confiança nos dados.

A perspectiva adotada é a de uma liderança de design de produto inspirada na Apple: reduzir decisões, revelar detalhes quando necessários, responder a cada ação e manter continuidade visual. A identidade continua sendo OctoBox, com o tema **Luxo Futurista 2050**. Não se trata de reproduzir telas de iOS ou adicionar vidro por aparência.

O plano original acertava ao aproveitar modelo, endpoint e outbox existentes e ao bloquear recordes até a classificação de séries. Esta revisão muda as decisões que atrapalhariam a experiência durante o treino:

| Antes | Decisão desta revisão | Benefício |
|---|---|---|
| Acrescentar campos ao formulário | Carga/reps dominantes e detalhes progressivos | Menos procura e ruído |
| RIR padrão 2 ou copiado da última vez | Esforço opcional e inicialmente sem resposta | Não inventar a percepção do aluno |
| Botão 4+ gravando 4 | Atalhos exatos 0–4 e entrada de outro valor | Preservar significado e precisão |
| Reps sem validação no serviço | Validação de cliente e servidor | Evitar erro de digitação no histórico |
| Editar e apagar tela pode enviar o dado | Rascunho separado de registro confirmado | Trocar de app não significa concluir |
| Salvar sem correção explícita | Recibo e correção rastreável | Recuperação de erro confiável |
| Calculadora descrita como taxonomia | Barra, estoque e montagem especificados | Resolver a conta da academia |
| Troféu quando peso aumenta | Recorde específico, confirmado e corrigível | Celebrar algo verdadeiro |

**Ampliação deliberada de escopo:** Fase 1 deixa de ser “backend zero”: inclui validação e correções na persistência. Fase 2 acrescenta correção rastreável ao modelo existente. Essas mudanças sustentam a promessa de UX; não devem ser estimadas como simples inclusão de campos.

### 0.1 Estado atual rechecado em 24/09/2026

São fatos do checkout local, não verificação do deploy. As referências usam símbolos para não depender das linhas da auditoria de 23/09.

| Camada | Estado real | Fonte |
|---|---|---|
| Modelo | Peso, reps e RIR opcionais; RIR com uma casa decimal; sem set_role ou vínculo de correção | [models.py — PublicWorkoutLoadLog](../../public_workouts/models.py) |
| Serviço | Persiste reps/RIR; valida faixa de peso e RIR não negativo; não valida reps explicitamente | [services.py — record_load / _validate_load_values](../../public_workouts/services.py) |
| HTTP | Recebe reps/RIR; resposta é o dict serializado diretamente, sem envelope entry | [PublicWorkoutRecordLoadView](../../student_app/views/public_workout_views.py) |
| Cliente | Envia só peso; impede registro somente com reps; paintHints copia peso por toque | [load_tracker.js](../../static/js/public_workouts/load_tracker.js) |
| Persistência | saveDirtyDrafts põe edição na mesma outbox de registros; drainOutbox descarta HTTP 400 e não devolve resultado por item | [load_tracker.js](../../static/js/public_workouts/load_tracker.js) |
| Feedback | Ausência do item na fila vira sucesso, inclusive quando descartado por 400 | [load_tracker.js — saveWidget](../../static/js/public_workouts/load_tracker.js) |
| Interface | Widget colapsável irmão do card; handler inline usa nextElementSibling; card contém links e ações secundárias | [workout.html](../../templates/public_workouts/workout.html) |
| Histórico | personal_record pega maior peso bruto e já devolve reps; todays_logged_weight retorna eco do registro de hoje | [public_workouts_extras.py](../../public_workouts/templatetags/public_workouts_extras.py) |
| Equipamento | Sem classificação no catálogo; substituições já trocam o slug do widget | [models.py](../../public_workouts/models.py), [load_tracker.js](../../static/js/public_workouts/load_tracker.js) |
| Estimativa | estimate_one_rep_max trata RIR ausente como zero no cálculo | [one_rep_max.py](../../public_workouts/one_rep_max.py) |
| Testes | Testes Python existentes; package.json tem lint/format, sem runner JS | [package.json](../../package.json) |

**Duas correções técnicas à Revisão 1:** saveWidget não recebe hoje o JSON do POST; precisa mudar o contrato da drenagem. O snapshot proposto no plano irmão também não contém personal_best, e a curva não cobre toda a política de recordes. Não basta ler um máximo daquele DTO.

### 0.2 Autoridade e integração

- [Plano de hierarquia e set_role, Revisão 8](curva-grafico-hierarquia-e-set-role.md): preserva separação de aquecimento/principal/máximo, legado e regras de curva. Nunca inferir tipo de série a partir de RIR.
- [Tema oficial](../architecture/themeOctoBox.md), [contrato visual](../map/design-system-contract.md) e [guia de CSS](../experience/css-guide.md) governam aparência e ownership.
- A correção de registros proposta aqui acrescenta um filtro de registros ativos antes da elegibilidade do plano irmão. Integrar os contratos no PR correspondente; não criar cálculos concorrentes.
- O guia de CSS contém marcadores de conflito preexistentes. Para este recorte, seguir tema, contrato e ownership confirmado no código; saneamento daquele documento é separado.

## 1. Experiência — registrar e seguir

### 1.1 Superfície e hierarquia

O aluno pode estar cansado, com uma mão disponível e conexão instável. O caminho comum deve funcionar sem teclado quando os últimos valores ainda servirem.

**Manter a grade e expandir o widget junto ao exercício.** Um editor aberto por vez; fechar preserva rascunho. A prescrição permanece por perto. Não adicionar modal ou tela cheia à primeira entrega.

Adicionar botão nativo **Registrar**, com aria-expanded e aria-controls. Remover a semântica de botão do article que contém links/controles; a execução do exercício continua acessível separadamente. Ao abrir, rolar somente se necessário e não ativar o teclado automaticamente.

Wireframe ilustrativo após a calculadora; valores não são recomendações. O tipo de série aparece somente com set_role ativo:

```text
┌──────────────────────────────────────┐
│ Supino com barra                     │
│ Prescrito: 8–10 reps · RIR 2          │
│ Último registro · 22 set              │
│ 60 kg × 8 reps     [Usar carga e reps]│
│                                      │
│ Carga total, incluindo a barra        │
│ [ − ]          62,5 kg          [ + ] │
│ Repetições                           │
│ [ − ]             8            [ + ] │
│                                      │
│ Tipo: Série principal                │
│ [ ] Foi aquecimento                  │
│                                      │
│ Esforço · opcional                [⌄]│
│ Montar anilhas                    [›]│
│ Trocar exercício                  [›]│
│                                      │
│       [ Salvar 62,5 kg × 8 ]          │
└──────────────────────────────────────┘
```

Após confirmação:

```text
✓ Registro salvo
62,5 kg × 8 reps · Série principal
Hoje                               [Corrigir]
```

**Assinatura visual:** os números que o aluno editou permanecem na confirmação, no mesmo lugar visual. O botão energizado cede espaço ao check e ao recibo; a interface reduz sua intensidade quando o trabalho termina. Não colapsar nem avançar automaticamente.

Corrigir só aparece com a Fase 2. Antes, usar **Novo registro**, sem alegar substituição do anterior. Não mostrar contagem de séries concluídas: o modelo atual não sustenta essa promessa.

### 1.2 Prescrição, referência e realizado

- Prescrição tem rótulo **Prescrito** e não preenche automaticamente o realizado.
- Referência mostra data e valores do mesmo log: **Último registro · 22 set · 60 kg × 8**. Antes de set_role, não chamar de última série principal; depois, identificar tipo conhecido/legado conforme o plano irmão.
- **Usar carga e reps** copia explicitamente esses valores e cria rascunho. Nunca copia RIR. Sem reps na referência, chamar o atalho **Usar carga**; referência só com reps recebe **Usar reps**.
- Ausência de peso é diferente de zero. Campos não respondidos permanecem vazios.
- Rascunho do movimento/data prevalece ao reabrir. Sem rascunho, o registro confirmado de hoje aparece como recibo, sem entrar silenciosamente em edição.
- Resposta tardia de pacote.json atualiza apenas a referência; não sobrescreve campos nem mantém handlers vinculados ao slug anterior.

### 1.3 Carga e repetições

Duas linhas com steppers confortáveis; carga recebe maior destaque. Sem slider, roleta ou gesto obrigatório.

- Incremento inicial de carga: 2,5 kg; opção secundária para 0,5 / 1 / 2,5 / 5 kg, lembrada por conta/movimento. O incremento não limita os valores digitáveis a seus múltiplos.
- Reps variam de uma em uma. Campo vazio não apresenta zero como resposta. Menos em campo vazio não cria dado; mais começa pelo incremento indicado.
- Teclado decimal para carga e numérico para reps; labels/unidades sempre visíveis. Aceitar vírgula ou ponto e rejeitar texto parcial, números não finitos ou truncamento de reps fracionárias.
- Peso e reps continuam individualmente opcionais; exigir ao menos um. Permitir **somente reps**, coerente com o modelo. Não inventar peso para exercício sem carga externa.
- CTA reflete dados: **Salvar 62,5 kg × 8**, **Salvar 62,5 kg** ou **Salvar 8 reps**. Nome acessível usa frase completa. Enter só confirma formulário válido sem envio em curso.

Contrato de novos registros: peso finito de 0 ao teto configurado do serviço, até duas casas decimais; reps inteiro de 1 a 999 ou null; RIR finito de 0 a 99,9, até uma casa decimal, ou null. São limites técnicos amplos, não metas de treino. Reps zero não representa série concluída nesta UI; tentativa sem repetição fica fora deste recorte. Histórico antigo permanece legível, sem normalização destrutiva.

### 1.4 Esforço em linguagem humana

Começa recolhido: **Esforço · opcional**. Ao abrir:

> **Quantas repetições ainda conseguiria fazer?**  
> Uma estimativa de quantas faltavam para chegar ao seu limite. Também chamado RIR.

Atalhos exatos 0, 1, 2, 3, 4. Seleção 2 mostra **Ainda faria 2 reps**; zero, **Não faria outra repetição**. **Outro valor** permite entrada decimal, incluindo 1,5 e valores acima de 4. **Não informar** limpa para null e recolhe.

Nenhuma seleção padrão, sem escala vermelho/verde premiando sofrimento. Valor informado aparece no resumo recolhido. Frações não são arredondadas para caber nas pílulas. Rascunho/correção preserva esforço daquela entrada; novo registro volta a null.

O cálculo atual de 1RM assume zero quando falta RIR. Na nova superfície, estimativa sem RIR deve explicitar a hipótese ou permanecer indisponível. Não apresentar isso como esforço medido ou prova de melhora; manter a distinção ao integrar sugestões do plano irmão.

### 1.5 Troca de exercício

**Trocar exercício** fica nos detalhes, sem fileira de alternativas antes da carga. A lista usa substituições existentes e não promete equivalência de peso/prescrição.

Guardar rascunho da origem, atualizar título/slug/referência/equipamento e carregar somente rascunho do destino. Sem rascunho, campos vazios. Não transportar 60 kg de barra para halteres. Identificar **Você está registrando: Supino com halteres** quando diferir da prescrição. Voltar recupera rascunho original; respostas antigas não podem atualizar o destino.

## 2. Aparência — precisão calma, identidade OctoBox

Formulário utilitário de alta frequência: acabamento refinado dentro do tema, sem hero próprio nem promoção automática a escopo premium.

| Elemento | Especificação |
|---|---|
| Material | Superfície mineral opaca o suficiente para leitura, fundo discreto, sem blur pesado atrás dos números |
| Hierarquia | Exercício → carga → reps → CTA; prescrição/referência apoiam; gráfico fora do editor |
| Tipografia | Tokens atuais --font-body/--font-display, sem outra família; números tabulares; carga 36–44 px, reps 28–32 px, labels 14–16 px, inputs pelo menos 16 px |
| Respiro | Ritmo de 8 px; grupos separados por 24 px; padding 16 px em mobile estreito e 24 px quando couber |
| Toque | Alvos mínimos 48 × 48 CSS px; CTA com altura mínima 56 px; 8 px entre ações adjacentes |
| Cor | Tokens --theme-* e acento vigente do corredor no CTA/foco; neon abaixo de aproximadamente 10% da área visível |
| Bordas | Família de superfícies existente; raios 12–20 px quando compatíveis com tokens; seleção também por texto/forma |
| Dark/light | Mesma hierarquia; light com menos glow; respeitar preferência do aluno |
| Movimento | 150–220 ms em opacity/transform; sem fundo animado, números saltando ou confete |
| Confirmação | Check, texto e valores persistentes; estado positivo como apoio; recorde ocupa a mesma região de feedback |

A ação fica no fluxo do editor; não criar barra fixa concorrendo com a bottom nav. Reservar espaço para navegação/safe area e permitir rolar até campo, erro e CTA com teclado aberto. Em 320 CSS px ou texto ampliado, detalhes quebram linha e controles empilham.

Labels reais, agrupamento semântico de esforço, seleção acessível, foco visível, erros com aria-describedby e status com aria-live polite. Ao fechar, devolver foco ao botão de abertura; ao substituir editor por recibo, não perder foco. Respeitar prefers-reduced-motion com versão estática/fade mínimo. Som desligado; vibração apenas como melhoria opcional em ambiente compatível.

Metas de contraste: 4,5:1 em texto comum; 3:1 em texto grande e componentes relevantes. Medidas e tempos são critérios web deste produto, não conversão literal de points nem promessa de APIs nativas Apple.

## 3. Fase 1 — registro rápido e persistência honesta

**P0. Frontend, validação no serviço e evolução do armazenamento local. Sem migration de servidor para reps/RIR.**

### 3.1 Estados e mensagens

| Estado | Mensagem/ação | Significado |
|---|---|---|
| Sem dados | Registre sua carga ou repetições | Nenhum dado inventado |
| Editando | Rascunho neste aparelho, após escrita local | Não enviado como realizado |
| Persistindo confirmação | Guardando… | Sem check antecipado |
| Fila offline | Guardado neste aparelho · envio pendente | Local confirmado, servidor não |
| Servidor confirmou | Registro salvo + recibo | Sucesso identificado para essa operação |
| Validação recusada | Erro junto ao campo + Corrigir dados | Conteúdo preservado, sem sucesso falso |
| Sessão expirada | Entre novamente para enviar | Fila mantida na conta original |
| Falha de armazenamento | Não foi possível guardar neste aparelho. Tente novamente. | Manter valores na tela; não prometer durabilidade |

### 3.2 Rascunho não é confirmação

1. Manter uma outbox de comandos confirmados. Criar store de rascunhos por conta autenticada, plano/programa, movimento e data. Isso exige upgrade versionado de IndexedDB; apenas adicionar reps/RIR à entrada antiga não exigiria.
2. Persistir durante edição com debounce curto e ao sair do campo. visibilitychange é tentativa adicional, não garantia ao encerrar navegador; nunca transforma edição em POST de realizado.
3. Rastrear alteração de todos os campos/tipo de série no widget, não somente data-dirty do peso. Falha de escrita mantém estado pendente.
4. Salvar valida, captura snapshot imutável, cria uma chave de idempotência e transfere rascunho para outbox atomicamente. Duplo toque/eventos concorrentes compartilham operação; retry conserva chave e valores.
5. Nova edição é uma revisão distinta: resposta atrasada não apaga dados posteriores ao snapshot enviado. Novo registro exige ação explícita.
6. Preservar data capturada ao sincronizar depois da meia-noite. Rascunho de ontem aparece como tal; continuar na data original ou iniciar hoje exige escolha explícita.
7. Drenar por ordem local de confirmação, com dependências da Fase 2; não ordenar por UUID.
8. A fila atual usa o slug da página ao reenviar. Evoluir envelope local com rota/contexto e identidade opaca fornecida pelo servidor. Dados de uma conta não são enviados ao entrar em outra; não armazenar cookies/tokens de sessão.
9. Entradas legadas sem contexto verificável não são apagadas nem atribuídas por palpite. Manter pendentes e reconciliar com contexto comprovável; recuperação não pode expor valores entre contas.

### 3.3 Resultado por operação

`drainOutbox` passa a emitir/devolver resultado por idempotency_key, incluindo estado e corpo da resposta. Salvar, reconectar e restaurar página usam a mesma transição. Persistir recibo local antes de remover pendência; falha nesse passo permite retry idempotente seguro.

HTTP 400 permanece recuperável e sai do retry automático. 401 aguarda autenticação; 403/404 exigem recuperação de acesso/contexto. Rede/5xx aguardam nova tentativa com espera progressiva; 429 respeita orientação de retry. Uma entrada inválida não bloqueia outras independentes.

Recibo, referência e histórico atualizam sem reload completo. Linha local tem Envio pendente e não participa de curva/recorde confirmado. Falha no refresh do histórico não transforma POST confirmado em falha de gravação.

### 3.4 Ownership e contrato

| Arquivo | Mudança |
|---|---|
| [workout.html](../../templates/public_workouts/workout.html) | Botão de abertura, editor, esforço, recibo, histórico com reps/RIR; atualizar handler inline que depende de nextElementSibling |
| [load_tracker.js](../../static/js/public_workouts/load_tracker.js) | Parser estrito, estado completo, cópia explícita, troca segura, rascunhos e resultados por operação |
| [workout-shell.css](../../static/css/public_workouts/workout-shell.css) | Layout/estados locais workout-load-input__*; não reestilizar globalmente workout-load-input__save, também usado em outras abas |
| [services.py](../../public_workouts/services.py) | Validação explícita de reps/RIR/peso, opcionais preservados, erros previsíveis |
| [public_workout_views.py](../../student_app/views/public_workout_views.py) | Normalização, erros por campo e contexto opaco autenticado para armazenamento local |
| [public_workouts_extras.py](../../public_workouts/templatetags/public_workouts_extras.py) | Registro completo para recibo sem quebrar todays_logged_weight; valores sempre da mesma entrada |

Reusar buildEntryFromWidget e endpoint; reps/rir seguem como número ou null. Não usar parseInt para aceitar parcialmente entrada inválida, seleção CSS como única fonte de verdade ou chave nova em cada tentativa.

Histórico mostra **62,5 kg × 8 reps · RIR 1,5**, omitindo campos ausentes sem convertê-los em zero; entradas só com reps permanecem visíveis. Card de maior carga mostra reps do mesmo log. Até elegibilidade estar ativa, não ampliar o claim com celebração nova.

## 4. Fase 2 — correção real

**P0 para experiência completa; obrigatória antes da celebração. Migration no modelo existente.**

Hoje, salvar 90 depois de digitar 900 cria dois eventos; o maior peso continua contaminado. Um segundo POST comum não pode se apresentar como edição.

### 4.1 Contrato proposto

- Acrescentar referência opcional única ao registro substituído: supersedes, autorreferência de PublicWorkoutLoadLog. Preservar original para auditoria; uma substituição direta por registro, com cadeias de correções vinculadas ao ativo.
- Mesmo endpoint recebe supersedes_idempotency_key opcional e uma nova chave da operação. Resolver alvo dentro da conta autenticada; mesma data e movimento neste primeiro recorte.
- Transação valida alvo ativo e coordena correções concorrentes. Conflito retorna 409 e caminho para recarregar versão atual; retry da mesma operação retorna resultado original.
- Criar seleção comum de registros ativos. Todos os consumidores de estado atual/progresso excluem substituídos antes de set_role, agrupamento diário e recorde. Auditoria pode mostrar ambos com indicação Corrigido.
- Atualizar juntos pacote, eco de hoje, recorde, 1RM, sugestões, curva e tendência. Deduplicação diária do plano irmão não substitui identidade de correção.

### 4.2 Interação e offline

**Corrigir** abre valores do registro, incluindo RIR exato; CTA **Salvar correção**. Cancelar preserva registro confirmado. Não reutilizar esse botão para nova série.

Se original ainda estiver pendente, criar comando dependente, preservando snapshots/chaves mesmo quando não sabemos se o primeiro POST chegou. Enviar original antes da correção. Se original for recusado definitivamente, conservar intenção editada e oferecer salvá-la como novo registro válido; não tentar corrigir alvo inexistente.

Correção pendente é identificada no recibo. Sucesso recalcula consumidores e retira selo invalidado. Desfazer/apagar definitivamente ficam fora desta fase sem contrato próprio de anulação. Integração com consumidores do plano irmão deve constar no mesmo PR que introduzir essa semântica.

## 5. Fase 3 — calculadora de anilhas

**P1. Independente de set_role; integrar após a base de registro.**

### 5.1 Equipamento e convenção

Adicionar equipment_type curado ao catálogo: barbell, dumbbell, machine, bodyweight, cable, other; default other, sem null redundante. Nunca inferir automaticamente de movement_pattern ou nome.

**Montar anilhas** aparece somente para barbell com convenção de **carga total incluindo barra** verificada. Equipment_type sozinho não prova essa convenção: registrar metadado explícito para ativação. Não reinterpretar histórico desconhecido nem multiplicar/dividir cargas antigas.

Halteres/máquinas mantêm convenção existente até curadoria específica; não chamar genericamente de por lado. Barras guiadas e exercícios assistidos exigem convenção própria e ficam fora desta calculadora.

### 5.2 Painel e resultado

- **Total: 62,5 kg, incluindo a barra**.
- Barra: atalhos 20 / 15 / 10 kg e Outro peso. Confirmar na primeira utilização; lembrar localmente, mantendo visível/editável.
- Anilhas: valores disponíveis e quantidade de pares; configuração inicial explícita. Não assumir estoque ilimitado como realidade da academia.
- Resultado textual: **De cada lado: 20 + 1,25 kg**. Esquema simétrico da barra com anilhas da maior para a menor e números legíveis.
- Conferência: **20 kg de barra + 2 × 21,25 kg = 62,5 kg**. Ilustração complementa texto.

Painel expansível no editor, sem modais empilhados. Abrir não altera carga; calcular outro alvo exige **Usar 62,5 kg** para aplicar ao rascunho. Nunca salva automaticamente.

### 5.3 Casos obrigatórios

1. Calcular em unidades inteiras de massa, respeitando pares disponíveis; minimizar número de anilhas com desempate determinístico favorecendo maiores.
2. Abaixo do peso da barra: explicar que o total precisa incluí-la e permitir editar barra/alvo.
3. Igual à barra: **Somente a barra**.
4. Impossível: explicar falta de combinação e oferecer alternativas exatas inferior/superior quando existirem. Nunca arredondar/aplicar escondido.
5. Mudar barra/estoque recalcula; não manter montagem antiga com total novo.
6. Configuração e cálculo funcionam offline, sem imagens remotas ou bibliotecas de animação.

## 6. Fase 4 — celebração específica e confiável

**P1. Depende das Fases 1 e 2 e de set_role/políticas do plano irmão em produção.**

### 6.1 Semântica

**Maior carga registrada no mesmo movimento**, entre registros ativos elegíveis top_set/max_set, estritamente acima do melhor peso anterior. Reps são contexto; não é claim de recorde de 1RM, volume ou força geral.

Primeiro elegível: **Primeiro registro salvo**, sem troféu de recorde. Empate, aquecimento, legado sem classificação e ausência de peso não disparam. Mesma carga com mais reps recebe confirmação normal nesta versão. Não incentivar bater recorde a cada treino.

### 6.2 Fonte única e resposta

Ampliar snapshot compartilhado com personal_best e seleção comum de candidatos ativos/elegíveis, usada pelo card e gravação. Abranger todo histórico elegível, inclusive max_set; janela de 90 dias da curva não limita recorde. Não tirar máximo de curve_points.

Calcular transição antes/depois na transação de gravação, com serialização consistente por conta para concorrência entre dispositivos. Correção compara estado ativo anterior e recalcula após substituição; correção para baixo não cria celebração compensatória. Render de página não deve fazer uma query por movimento.

POST mantém campos atuais e acrescenta:

```json
{
  "achievement": {
    "kind": "load_record",
    "previous_weight_kg": 60,
    "delta_kg": 2.5
  }
}
```

Sem evento, achievement é null. Persistir resultado da conquista associado ao log/operação no modelo existente para replay estável após resposta perdida. Isso pode exigir migration adicional; não é só uma flag no JSON. Cliente deduplica feedback pela chave da operação.

### 6.3 Expressão visual

Na mesma área do recibo:

> **Nova maior carga no supino**  
> 62,5 kg × 8 reps · +2,5 kg sobre seu recorde anterior.

Selo discreto, check e texto; no máximo uma transição curta. Sem confete, som automático, bloqueio, compartilhamento obrigatório ou loop. Movimento reduzido recebe estado estático.

Offline não recebe troféu otimista. Confirmação com exercício ativo atualiza seu recibo; confirmação tardia agrupa **Registros sincronizados** com detalhes, sem sequência de celebrações antigas. Correção posterior invalida selo nas leituras futuras.

## 7. Visão seguinte — modo treino convive com a grade

Direção escolhida: **convivência**. Grade para consultar/registrar; modo treino opcional para acompanhamento série a série. Não colocar uma tela Iniciar antes de todo registro.

| Feature futura | Valor | Dependência |
|---|---|---|
| Exercício em foco e próxima série | Menos navegação | Sessão e identidade/ordem real de séries |
| Descanso ajustável, +30 s e pular | Acompanhar intervalo | Estado persistido e término por timestamp; sem prometer alarme em background sem suporte |
| Retomar treino | Continuar após fechar app | Sessão e sincronização de conflitos |
| Resumo ao terminar | Fechamento sem competição em cada série | Registros confirmados e métricas comparáveis |
| Recorde de reps na mesma carga | Reconhecer progresso além do peso | Variante, convenção e série comparáveis |

Essas features pedem plano próprio com training_session_id, identidade/ordem de série e horário de captura. Data do log não é identidade de sessão. Protótipo é hipótese a testar, não evidência de validação com alunos.

## 8. Sequência e compatibilidade

```text
Fase 1 — registro e persistência ──┬── Fase 2 — correção real ───────┐
                                  └── Fase 3 — calculadora         │
Plano irmão — set_role e políticas em produção ────────────────────┤
                                                                  └── Fase 4 — recorde
Modo treino completo — plano seguinte
```

Calculadora não é pré-requisito de correção/recorde; pode ser desenvolvida separadamente e integrada após Fase 1. Ordem de valor para piloto: **1 → 2 → 3/4**, respeitando set_role para 4.

- Dividir Fase 1 em PRs revisáveis de contrato/persistência e UI, sem liberar feedback novo apoiado na drenagem antiga que confunde erro com sucesso.
- Antes de set_role, não exibir/fabricar classificação. Integrar o controle principal/aquecimento e protocolo legado do plano irmão. RIR zero nunca produz max_set.
- Clientes antigos podem continuar omitindo reps/RIR. Novas validações devolvem erro recuperável para dados fora do contrato; histórico não recebe valores inventados.
- Upgrade IndexedDB trata abas antigas, fechamento de conexões em versionchange e atualização bloqueada. Não apagar filas para atualizar.
- Campos opcionais no POST não exigem sozinhos invalidar cache. Alteração de autosave/armazenamento e integração com set_role exigem estratégia explícita de versão de assets/service worker e migração. Preservar pendências antes de ativação/reload da PWA.
- Rollback visual não remove campos do servidor nem dados locais; recursos indisponíveis ficam ocultos com dados preservados.

## 9. Verificação e critérios de aceite

### 9.1 Testes de comportamento na implementação

Reusar [test_load_log.py](../../public_workouts/test_load_log.py), [test_public_workout_record_load_endpoint.py](../../student_app/test_public_workout_record_load_endpoint.py) e [test_workout_template.py](../../public_workouts/test_workout_template.py).

| Área | Evidência exigida |
|---|---|
| Entrada | Só peso, só reps, ambos, RIR omitido/zero/1,5, vírgula, limites, reps fracionárias, números não finitos e booleanos recusados |
| Referência | Resposta tardia não sobrescreve; cópia não traz RIR; rascunho não mistura movimentos/datas |
| Offline | Editar/apagar tela não cria log; salvar/reload preserva; timeout após POST não duplica; reconexão atualiza recibo |
| Erros | 400 não desaparece nem vira sucesso; 401 preserva conta; armazenamento falho não mostra check; entrada inválida não paralisa demais |
| Correção | 900→90 remove 900 de recorde/sugestão/curva; concorrência dá conflito; retry não duplica; outra conta não corrige; dependência offline respeitada |
| Calculadora | 62,5 com barra 20 e pares 20/1,25; barra 15; barra sozinha; alvo menor que barra; estoque insuficiente; alvo não exato |
| Recorde | Primeiro, empate, aquecimento, legado, max_set, só reps, dois dispositivos, resposta perdida, replay e correção invalidante |
| Integração | Card/pacote/curva/histórico/celebração usam mesma política; sem crescimento de consultas por movimento |

Testes de template comprovam semântica/dados renderizados, não interação JS. Para fila/rascunho/correção, introduzir cobertura de comportamento em navegador compatível com o repo, ou registrar QA reproduzível enquanto essa infraestrutura é introduzida. Não declarar teste ponta a ponta apenas com assertIn de atributos HTML.

### 9.2 QA visual e uso real

Safari/iPhone e Chrome/Android, navegador e PWA, nos aparelhos disponíveis. Larguras 320/360/390 CSS px, tablet/desktop; dark/light, teclado aberto, texto 200%, VoiceOver/TalkBack, movimento reduzido e conexão intermitente.

Piloto com pelo menos cinco alunos, iniciantes e experientes: repetir carga/reps, registrar sem histórico, explicar/pular esforço, trocar exercício, salvar offline, corrigir e montar anilhas. **Metas de produto, ainda não medidas:**

- Repetir: abrir → usar valores → salvar, **3 toques sem teclado**.
- Após abrir, até **8 segundos de mediana** no registro comum, excluindo sincronização.
- **4 de 5** completam registro e distinguem pendente/confirmado sem explicação do moderador.
- **Zero** descarte silencioso, duplicação por retry ou troca de movimento nos cenários de aceite.
- Resposta visual ao toque em até **100 ms** no aparelho de referência; rede/armazenamento têm estados próprios.
- Nenhuma ação coberta por teclado/bottom nav, nenhum overflow horizontal, nenhuma escolha comunicada só por cor.

Se tempo/compreensão falharem, reduzir densidade e ajustar copy antes de acrescentar animação. Usabilidade precede celebração.

### 9.3 Definição de concluído

Aluno registra rapidamente, reencontra valores, distingue rascunho/local/servidor, corrige erro e entende por que recebeu recorde. Calculadora produz montagem possível com equipamento informado. Registrar evidências de QA e limitações por fase. **Esta revisão documental não certifica implementação, performance nem validação com usuários.**

## 10. Referências de design

Consultadas em 24/09/2026. Princípios orientam a proposta; decisões para academia, medidas web, metas e contratos de dados são desta revisão.

- [Apple HIG — Entering data](https://developer.apple.com/design/human-interface-guidelines/entering-data): reduzir entrada desnecessária e explicar o dado pedido. Aplicação: cópia explícita de carga/reps e esforço opcional.
- [Apple — UI Design Dos and Don'ts](https://developer.apple.com/design/tips/): controles confortáveis para toque e legibilidade. Aplicação: alvos amplos e hierarquia numérica; CSS px propostos não são conversão literal de points.
- [Apple HIG — Motion](https://developer.apple.com/design/human-interface-guidelines/motion) e [Testing system accessibility features](https://developer.apple.com/documentation/accessibility/testing-system-accessibility-features-in-your-app): movimento comunicativo e respeito às preferências de acessibilidade. Aplicação: feedback curto, alternativa estática e navegação por teclado.

**Critério final de design:** o aluno deve lembrar do treino que fez; o aplicativo deve deixar a sensação de que registrar foi fácil e o dado ficou certo.
