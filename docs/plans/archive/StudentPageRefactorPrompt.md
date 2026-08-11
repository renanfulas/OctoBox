<!--
ARQUIVO: prompt mestre para auditoria e planejamento por ondas do refactor da pagina do aluno inspirado no Figma.

POR QUE ELE EXISTE:
- transforma a direcao visual aprovada no Figma em um prompt tecnico reutilizavel.
- organiza a analise da pagina do aluno em ondas progressivas de convergencia.
- reduz o risco de respostas vagas ou refactors sem contrato claro.

O QUE ESTE ARQUIVO FAZ:
1. define o objetivo do prompt e seu uso principal.
2. entrega o prompt completo para IA analisar e planejar o refactor.
3. separa a convergencia em ondas de 60%, 80%, 90% e 95%+.
4. fixa o contrato de resposta para evitar ambiguidades.

PONTOS CRITICOS:
- o Figma deve ser tratado como contrato visual.
- o codigo atual deve ser tratado como contrato comportamental.
- o prompt prioriza analise + plano antes de implementacao.
-->

# Student Page Refactor Prompt

## Resumo

Este prompt foi desenhado para uso hibrido com prioridade em `analise + plano primeiro`, inspirado no Figma aprovado da pagina do aluno.

Ele obriga a IA a trabalhar em 4 ondas progressivas:

1. `Onda A = 60%`
2. `Onda B = 80%`
3. `Onda C = 90%`
4. `Onda D = 95%+`

A ideia e simples:

1. primeiro organizar a casa
2. depois trocar os moveis
3. so no final alinhar os quadros na parede

Em termos tecnicos:

1. primeiro arrumar arquitetura
2. depois convergir para o Figma
3. por ultimo lapidar acabamento fino

## Uso principal

Este prompt e ideal para:

1. Codex
2. ChatGPT
3. outro agente tecnico forte

quando a tarefa for:

1. auditar a pagina atual
2. propor arquitetura alvo
3. montar um plano por ondas
4. preparar um refactor seguro e rastreavel

## Prompt final

```md
Você é uma força-tarefa combinada com 4 especialidades:

1. Product UI/UX Architect
2. Front-end Architect especialista em Django + CSS
3. Debugador de causa raiz orientado a evidências
4. Planejador técnico de refactor por ondas

Sua missão é analisar e planejar a reprogramação da página do aluno no OctoBOX para convergir ao design aprovado no Figma, sem quebrar a lógica já existente e sem aumentar o débito técnico.

Contexto:
- O OctoBOX já possui uma página funcional do aluno, mas ela está visualmente e estruturalmente distante do design final.
- O Figma aprovado representa a direção correta.
- O estado atual da página tem sinais de:
  - overrides invisíveis
  - CSS com muitas responsabilidades misturadas
  - templates grandes demais
  - múltiplos donos para navegação/estado
  - custo alto para ajustes simples
- O objetivo não é “maquiar” o layout.
- O objetivo é reorganizar a página para que ela fique:
  - visualmente próxima do Figma
  - simples de manter
  - segura de evoluir

Página-alvo:
- detalhe do aluno com 3 tabs:
  - Pagamentos
  - Plano
  - Perfil

Missão principal:
- montar um plano de refactor em ondas progressivas
- deixar explícito o que entra em cada onda
- deixar explícito o que NÃO entra em cada onda
- reduzir risco e custo de manutenção
- dar direção suficiente para que um agente implemente depois sem se perder

Princípios obrigatórios:
- causa raiz vence sintoma
- simplicidade vence remendo
- autoridade clara vence lógica duplicada
- componente não pode depender de override invisível
- arquitetura da página deve ser mais importante que micro-ajustes cosméticos
- primeiro organizar estrutura, depois buscar fidelidade visual
- não esconder complexidade atrás de nomes bonitos
- não sugerir rewrite total sem justificar
- toda onda precisa ter ganho claro e critério de pronto

Restrições absolutas:
- não fazer redesign vazio
- não sugerir empilhar mais overrides
- não sugerir “fazer tudo de uma vez”
- não tratar CSS, template e JS como problemas separados se eles fazem parte do mesmo fluxo
- não deixar decisões em aberto para o implementador

Quero que você trate o Figma como referência visual principal
e o código atual como referência comportamental principal.

Você deve responder em 4 ondas:

- Onda A = 60%
- Onda B = 80%
- Onda C = 90%
- Onda D = 95%+

Cada onda deve representar um estágio realista de convergência com o Figma.

## O que você deve analisar

1. Estrutura de template
- o que precisa ser quebrado em partials
- o que está acumulando responsabilidades demais

2. CSS e cascata
- onde existem overrides invisíveis
- onde a especificidade está cara demais
- o que deveria ser base
- o que deveria ser contexto
- o que deveria ser modifier

3. JavaScript e estado
- quem controla hash
- quem controla tabs
- quem controla drawers
- quem controla expansão/minimização
- onde há duplicidade de autoridade

4. Composição visual
- header do aluno
- tabs
- painéis
- cards
- tabelas
- alertas
- CTAs
- spacing e densidade
- responsividade

5. Estratégia de convergência com o Figma
- o que gera salto visual rápido
- o que exige refactor estrutural
- o que é acabamento fino

## Formato obrigatório da resposta

Responda exatamente nesta ordem.

### 1. Leitura do estado atual
Explique por que a página atual está cara de mexer.
Aponte a causa raiz do desalinhamento com o Figma.

### 2. Arquitetura alvo
Explique como a página deveria ser organizada para suportar o design do Figma com baixo custo de manutenção.
Separe entre:
- shell da página
- header
- tabs
- painéis
- CSS base
- CSS contextual
- JS de navegação
- JS de estado
- partials

### 3. Onda A — 60%
Formato:
- Objetivo da onda:
- O que entra:
- O que não entra:
- Ganho visual esperado:
- Ganho estrutural esperado:
- Risco:
- Prevenção:
- Critério de pronto:

Regra:
- A Onda A deve gerar o maior salto de clareza e estrutura com o menor risco possível.

### 4. Onda B — 80%
Formato:
- Objetivo da onda:
- O que entra:
- O que não entra:
- Ganho visual esperado:
- Ganho estrutural esperado:
- Risco:
- Prevenção:
- Critério de pronto:

Regra:
- A Onda B deve fazer a página realmente parecer com o Figma, sem ainda exigir obsessão de acabamento.

### 5. Onda C — 90%
Formato:
- Objetivo da onda:
- O que entra:
- O que não entra:
- Ganho visual esperado:
- Ganho estrutural esperado:
- Risco:
- Prevenção:
- Critério de pronto:

Regra:
- A Onda C deve consolidar os componentes, responsividade, estados e consistência visual.

### 6. Onda D — 95%+
Formato:
- Objetivo da onda:
- O que entra:
- O que não entra:
- Ganho visual esperado:
- Ganho estrutural esperado:
- Risco:
- Prevenção:
- Critério de pronto:

Regra:
- A Onda D deve cobrir refinamento fino, micro-hierarquia, polish e remoção do legado que restar.

### 7. Tabela de esforço x impacto
Monte uma leitura comparativa entre as ondas.
Formato:
- Onda
- Impacto visual
- Impacto estrutural
- Risco
- Custo
- Quando vale fazer

### 8. Quick wins
Liste o que pode ser feito cedo sem esperar ondas mais profundas.

### 9. Débito técnico que não deve mais receber remendo
Liste o que precisa obrigatoriamente entrar em refactor estrutural e por quê.

### 10. Critério de pronto final
Defina como saber que a página ficou:
- simples de ajustar
- visualmente próxima do Figma
- com baixo custo de manutenção

## Qualidade esperada
- menos opinião vaga
- mais arquitetura clara
- mais mapa de execução
- menos “ficaria legal”
- mais “isso precisa ser organizado assim”
- pense como alguém que vai manter a página por muito tempo
- se houver conflito entre velocidade e saúde estrutural, explique claramente

## Filtro final antes de responder
Só entregue se conseguir afirmar:
- identifiquei o salto de 60%, 80%, 90% e 95%+ de forma realista
- separei ganho visual de ganho estrutural
- deixei claro o que entra e o que não entra em cada onda
- reduzi ambiguidades para o implementador
- propus uma jornada que evita novos remendos
```

## Instrucoes de uso

Use este prompt com:

1. screenshots do Figma
2. contexto do codigo atual
3. resumo dos arquivos principais da pagina

Idealmente cole junto:

1. a tela de `Pagamentos`
2. a tela de `Plano`
3. a tela de `Perfil`

Se quiser uma resposta ainda mais forte, adicione:

1. `trate o Figma como contrato visual`
2. `trate o codigo atual como contrato comportamental`
3. `nao misture implementacao com opiniao`

## Assumptions e defaults

1. uso principal definido: `analise + plano primeiro`
2. o alvo e a pagina completa do aluno com 3 tabs
3. o objetivo estrategico e chegar em `80%` como meta inteligente de producao
4. `90%` e `95%+` entram como ondas de consolidacao e polish, nao como ponto de partida
5. este prompt foi escrito para funcionar bem com agentes tecnicos fortes sem deixar decisoes abertas
