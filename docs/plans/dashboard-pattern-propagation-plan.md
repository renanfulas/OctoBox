<!--
ARQUIVO: plano oficial para propagar por ondas os padroes validados no dashboard.

TIPO DE DOCUMENTO:
- plano operacional de rollout visual e estrutural

AUTORIDADE:
- alta para a frente de replicacao segura do dashboard nas outras paginas

DOCUMENTO PAI:
- [theme-implementation-final.md](theme-implementation-final.md)

QUANDO USAR:
- quando a duvida for como replicar o que funcionou no dashboard sem copiar tudo no impulso
- quando precisarmos decidir a ordem de ondas, paginas ancora e criterios de pronto
- quando a equipe quiser manter shared first e local second como regra de execucao

POR QUE ELE EXISTE:
- transforma uma boa intuicao visual em plano rastreavel
- impede que a expansao do dashboard vire debito tecnico distribuido
- fixa os skills obrigatorios para a frente nao se perder

O QUE ESTE ARQUIVO FAZ:
1. define a estrategia oficial de propagacao por ondas
2. aplica C.O.R.D.A. para alinhar contexto, risco, direcao e acoes
3. separa shared de adaptacao local
4. registra checklist, prompt operacional e criterios de validacao

PONTOS CRITICOS:
- este plano nao autoriza copiar CSS local do dashboard como padrao universal
- cada onda deve promover primeiro o que e compartilhado e so depois ajustar a superficie local
- os skills [../../.agents/skills/octobox-design/SKILL.md](../../.agents/skills/octobox-design/SKILL.md) e [../../.agents/skills/css_front_end_architect/SKILL.md](../../.agents/skills/css_front_end_architect/SKILL.md) sao obrigatorios nesta frente
-->

# Dashboard Pattern Propagation Plan

## Resumo

Este plano abre a frente oficial para replicar nas outras paginas o que ficou forte no dashboard sem transformar o repositorio em uma colecao de excecoes locais.

Em linguagem simples:

1. nao vamos tirar xerox do dashboard
2. vamos descobrir quais pecas dele viraram molde oficial
3. primeiro colocamos essas pecas no design system
4. depois vestimos cada pagina com esse molde do jeito certo

Documentos que governam esta frente:

1. [../architecture/themeOctoBox.md](../architecture/themeOctoBox.md)
2. [theme-implementation-final.md](theme-implementation-final.md)
3. [../experience/css-guide.md](../experience/css-guide.md)
4. [../map/design-system-contract.md](../map/design-system-contract.md)
5. [../map/front-end-ownership-map.md](../map/front-end-ownership-map.md)

Skills obrigatorios desta frente:

1. [../../.agents/skills/octobox-design/SKILL.md](../../.agents/skills/octobox-design/SKILL.md)
2. [../../.agents/skills/css_front_end_architect/SKILL.md](../../.agents/skills/css_front_end_architect/SKILL.md)

## C.O.R.D.A.

## C - Contexto

O dashboard virou a superficie-laboratorio onde o OctoBox validou:

1. hero mais premium e mais claro
2. shell com mais atmosfera e menos ruido
3. command workspace melhor definido
4. cards com presenca mais forte e mais controlada

Ao mesmo tempo, a branch mostrou uma verdade importante:

1. parte dessas melhorias ja subiu para shared
2. parte ainda e composicao local do dashboard

Problema real:

1. se copiarmos tudo em massa, espalhamos CSS local como se fosse design system
2. se formos devagar demais sem plano, a frente fica so na memoria oral

## O - Objetivo

Propagar o padrao validado no dashboard para o resto do produto por ondas, de forma:

1. rastreavel
2. segura
3. modular
4. alinhada ao tema Luxo Futurista 2050

Definicao de sucesso:

1. o que e shared entra primeiro no design system
2. as paginas recebem o novo padrao por familias
3. cada tela adapta apenas a propria composicao local
4. o produto fica mais coeso sem virar copia do dashboard

## R - Riscos

### Risco medio

Copiar CSS local do dashboard diretamente para outras paginas.

Traducao infantil:
e como usar uma chave que abre uma porta e forcar essa mesma chave em todas as portas da casa.

### Risco medio

Misturar redesign com refatoracao estrutural na mesma passada.

Isso tende a esconder bug visual dentro de mudanca grande demais.

### Risco medio a alto

Tocar muitas paginas diferentes na mesma onda.

Resultado comum:

1. regressao difusa
2. excecoes rapidas
3. mais override
4. menos confianca no shared

### Risco alto

Promover uma tela a escopo premium antes de sua hierarquia estar madura.

Se a estrutura nao estiver pronta, o brilho vira maquiagem em vez de composicao.

## D - Direcao

Direcao oficial desta frente:

1. shared first
2. family rollout second
3. local polish last

Regra de ouro:

**Toda onda deve responder primeiro o que vira componente compartilhado e so depois o que fica como adaptacao local.**

Regras operacionais:

1. comecar por uma pagina ancora dentro de cada familia
2. validar a ancora
3. replicar para as paginas irmas
4. so entao fazer o polimento fino

## A - Acoes

### Onda 1: Foundation Shared

Objetivo:

1. promover para o shared tudo que o dashboard provou como reutilizavel

Escopo:

1. `hero`
2. `card` e `table-card`
3. `topbar`
4. `sidebar`
5. shell e atmosfera base

Criterio de pronto:

1. o que e reutilizavel deixa de morar apenas no dashboard
2. o host canonico fica mais forte do que a pagina local

### Onda 2: Catalog Core

Objetivo:

1. aplicar os padroes compartilhados nas paginas do catalogo

Paginas:

1. `students`
2. `finance`
3. `finance-plan-form`
4. `class-grid`

Pagina ancora sugerida:

1. `finance`

Criterio de pronto:

1. o catalogo parece parte do mesmo predio visual
2. nenhuma tela perde sua hierarquia propria

### Onda 3: Operations Roles

Objetivo:

1. aplicar o padrao nas superficies operacionais por papel

Paginas:

1. `manager`
2. `reception`
3. `coach`
4. `dev`

Pagina ancora sugerida:

1. `manager`

Criterio de pronto:

1. as roles compartilham familia visual
2. cada papel continua legivel e funcionalmente distinto

### Onda 4: Special Cases

Objetivo:

1. tratar superficies especiais, hibridas ou mais sensiveis

Paginas candidatas:

1. placeholders
2. telas com markup proprio forte
3. fluxos utilitarios com assinatura parcial

Criterio de pronto:

1. os casos residuais nao obrigam criar um segundo design system escondido

### Onda 5: Polish and Validation

Objetivo:

1. fechar consistencia dark/light, mobile e limpeza residual

Criterio de pronto:

1. dark e light continuam da mesma familia
2. o produto nao parece um mosaico de ondas diferentes
3. o que sobrou de excecao local foi minimizado

## Regra de skills obrigatorios

Em toda tarefa desta frente:

1. usar `octobox-design` para decidir assinatura visual, escopo premium, glow, atmosfera e hierarquia
2. usar `CSS Front end architect` para decidir ownership, modularidade, CSS hygiene, naming e eliminacao de remendos

Se houver conflito:

1. `octobox-design` governa a linguagem visual
2. `CSS Front end architect` governa onde e como essa linguagem deve morar tecnicamente

## Checklist por onda

Antes de iniciar uma onda:

1. a familia de paginas esta clara?
2. a pagina ancora esta escolhida?
3. sabemos o que e shared e o que e local?
4. o risco de regressao esta visivel?

Antes de editar:

1. ler `README.md`
2. ler `docs/map/documentation-authority-map.md`
3. ler `docs/architecture/themeOctoBox.md`
4. ler `docs/map/design-system-contract.md`
5. ler `docs/experience/css-guide.md`

Antes de fechar a onda:

1. a tela continua clara em ate 3 segundos?
2. o glow continua subordinado ao conteudo?
3. o shared ficou mais forte do que o local?
4. dark e light seguem da mesma familia?
5. desktop e mobile continuam previsiveis?

## Prompt operacional da frente

Use este prompt sempre que for executar uma nova onda:

```text
Voce esta executando uma onda da frente Dashboard Pattern Propagation Plan no OctoBox.

Objetivo:
Propagar para outras paginas os padroes validados no dashboard sem copiar CSS local de forma cega e sem criar debito tecnico.

Regras obrigatorias:
1. Ler os docs canonicos do projeto antes de editar
2. Usar os skills octobox-design e CSS Front end architect
3. Promover primeiro o que virou componente compartilhado
4. Adaptar a superficie local apenas depois
5. Nao copiar markup ou CSS do dashboard como padrao universal
6. Preservar clareza operacional acima de brilho ou efeito

Saida obrigatoria:
1. o que foi promovido para shared
2. o que ficou como adaptacao local
3. os riscos encontrados
4. a pagina ancora validada
5. o proximo passo recomendado
```

## Proxima entrega esperada

Depois deste plano, a proxima entrega correta e:

1. seguir com a Onda 2 do Catalog Core
2. usar `finance` como pagina ancora
3. validar o shared antes de espalhar para `students`, `finance-plan-form` e `class-grid`
