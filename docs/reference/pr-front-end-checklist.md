<!--
ARQUIVO: checklist curto de PR para mudancas de front-end no OctoBox.

TIPO DE DOCUMENTO:
- referencia operacional de revisao
- checklist de validacao curta

AUTORIDADE:
- alta para revisao de PRs de front-end e mudancas visuais/estruturais

DOCUMENTOS PAIS:
- [front-end-octobox-organization-standard.md](front-end-octobox-organization-standard.md)
- [front-end-city-map.md](front-end-city-map.md)
- [front-end-card-architecture.md](front-end-card-architecture.md)

QUANDO USAR:
- antes de abrir PR com mudanca de CSS, template ou JS de interface
- antes de aprovar PR de front-end
- quando houver duvida se a mudanca esta saudavel ou virando divida

POR QUE ELE EXISTE:
- transforma o padrao arquitetural em uma rotina simples de revisao
- evita tanto puxadinho quanto overengineering
- reduz risco de subir CSS novo no lugar errado

O QUE ESTE ARQUIVO FAZ:
1. cria uma triagem curta para PRs de front-end
2. aponta os erros mais comuns a evitar
3. conecta revisao tecnica com a organizacao oficial do OctoBox

PONTOS CRITICOS:
- este checklist nao substitui julgamento tecnico
- ele existe para reduzir esquecimento, nao para travar entrega
- se a mudanca e excepcional, o PR deve explicar por que saiu do trilho padrao
-->

# Checklist curto de PR para front-end

Use este checklist antes de subir ou aprovar qualquer PR que toque:

1. CSS
2. templates
3. page payloads de interface
4. JS de comportamento visual
5. estrutura de uma superficie do produto

## Regra de uso

Se a maioria das respostas for `nao`, o PR provavelmente esta nascendo fora do padrao OctoBox.

Se um item falhar por motivo bom, o PR deve explicar isso de forma direta.

## Checklist principal

### 1. Superficie certa

1. a feature entrou na superficie correta do produto?
2. ela nasceu no corredor certo, em vez de cair num arquivo generico ou aleatorio?

Exemplo:

1. feature do coach nasce em `operations/dev-coach/`
2. nao em CSS global por conveniencia

### 2. Reuso antes de criacao

1. a mudanca tentou reutilizar tokens, componentes e shells existentes antes de criar CSS novo?

Regra pratica:

1. reutilizar primeiro
2. criar depois, se realmente precisar

### 3. Menor lugar util possivel

1. o CSS novo entrou no menor lugar util possivel?

Arvore curta:

1. global so se for global
2. shared so se o reuso for real
3. local se ainda for uma necessidade local

### 4. Sem inline e sem hooks frageis

1. o template evitou `style=""`, `<style>` local e gambiarra de markup?
2. os elementos importantes usam hooks estruturais (`data-*`, ids semanticos, classes contextuais) e nao classe puramente visual para JS?

### 5. CSS coeso

1. o arquivo alterado continua coeso ou ja esta virando armario de tudo?
2. o split foi feito apenas se havia densidade real?

Regra:

1. nao splitar cedo demais
2. nao empilhar ate virar monolito local

### 6. Sem briga com o design system

1. a mudanca local nao reescreve o host compartilhado sem necessidade?
2. ela conversa com tokens e componentes existentes?
3. nao apareceu `!important` ou seletor profundo demais para ganhar no grito?

### 7. Ownership claro

1. ficou claro quem e dono do template?
2. ficou claro quem e dono do CSS?
3. ficou claro quem e dono do comportamento JS, se houver?

Se a resposta for confusa, a proxima manutencao vai custar caro.

### 8. Custo futuro sob controle

1. a mudanca evita tanto gambiarra quanto overengineering?
2. ela deixa o proximo passo mais facil, e nao mais nebuloso?

## Sinais rapidos de alerta

Se aparecer qualquer item abaixo, vale pausar e revisar:

1. arquivo local crescendo sem ownership claro
2. CSS novo em pasta global para resolver caso local
3. classe visual usada como contrato de comportamento
4. repeticao de mesmo padrao em duas ou tres superficies sem promocao consciente
5. necessidade de explicar demais a estrutura para uma mudanca simples
6. `!important` visual
7. seletor profundo demais

## Quando o PR precisa explicacao extra

O PR deve justificar explicitamente quando:

1. promove algo local para shared
2. cria novo manifesto
3. cria novo arquivo CSS sem seguir a arvore de decisao padrao
4. altera estrutura de componente compartilhado
5. mexe em token global para resolver problema que parecia local

## Modelo curto de nota no PR

Se quiser documentar rapido no corpo do PR, use algo assim:

```md
## Front-end check

- Superficie correta: sim
- Reuso antes de criacao: sim
- Menor lugar util: sim
- Hooks estaveis: sim
- Split saudavel: sim
- Sem briga com design system: sim
- Ownership claro: sim
- Custo futuro sob controle: sim

Observacoes:
- O CSS ficou local em `operations/dev-coach/` porque ainda nao ha reuso real fora do coach.
```

## Leitura simples

Este checklist existe para responder:

1. colocamos a nova peca no lugar certo?
2. usamos o que ja existia antes de inventar coisa nova?
3. resolvemos o problema sem puxadinho e sem foguete?

Se a resposta for sim, o PR esta no trilho certo.
