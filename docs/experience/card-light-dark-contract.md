<!--
ARQUIVO: contrato minimo para criar cards que nascem corretos em light e dark mode.

POR QUE ELE EXISTE:
- transforma os achados recorrentes em checklist de fabrica.
- evita criar card bonito no light e quebrado no dark.
- reduz a necessidade de cirurgias futuras de contraste, ownership e cascata.

O QUE ESTE ARQUIVO FAZ:
1. define quem manda na casca, no miolo e nos estados do card.
2. lista a anatomia minima esperada para qualquer card novo.
3. cria uma checklist de entrega para light mode e dark mode.

PONTOS CRITICOS:
- este contrato nao substitui screenshot nem runtime.
- se o card usar controle nativo, o limite do navegador deve ser assumido cedo.
- se o card falhar neste contrato, a chance de debito tecnico e alta.
-->

# Contrato de Card: Light + Dark

Este documento responde:

1. "quando formos criar um card novo, como ele ja nasce certo nos dois temas?"

Em linguagem simples:

1. e a planta da casa antes de subir a parede
2. se a planta ja nasce boa, a reforma do futuro fica muito menor

## Regra de ouro

Antes de criar o card, responda:

1. quem manda na casca?
2. quem manda no texto?
3. quem manda nos controles?

Se a resposta for "todo mundo um pouco", o card ja nasceu com risco.

## 1. Ownership minimo

Ao criar um card novo:

1. `cards.css` ou shell canonico manda em surface, border, shadow e radius base
2. o modulo local manda apenas no contexto, sotaque, layout interno e variacoes reais
3. dark mode local nao deve reinventar o host inteiro se o host ja existe no shared

Regra pratica:

1. host grande manda na casca
2. primitivo compartilhado manda na anatomia
3. pagina manda no sotaque

## 2. Anatomia minima obrigatoria

Todo card novo deve pensar nestas pecas:

1. `head`
2. `title`
3. `copy`
4. `meta` ou `label`
5. `body`
6. `footer` ou `actions`
7. `empty/error/loading` quando existirem

Se qualquer uma existir no HTML, ela precisa ter:

1. light mode legivel
2. dark mode legivel
3. contraste suficiente sem depender de heranca acidental

## 3. Checklist de template

Antes de mexer no CSS, validar o HTML:

1. `title` deve conter titulo curto, nao paragrafo
2. resumo longo deve ir em `copy`, nao em `title`
3. `label` deve continuar `label`
4. `field-label` nao deve ser usado para texto decorativo
5. controles nativos devem continuar semanticamente reais, mesmo quando estilizados

Heuristica:

1. se o titulo parece um mini-artigo, o problema nao e de cor; e de anatomia

## 4. Checklist de light mode

O card so pode ser considerado pronto se:

1. title e copy leem bem sem zoom
2. border, shadow e surface nao parecem caixa dupla
3. meta, eyebrow, badge e pill conversam com o host
4. inputs, selects e textareas nao parecem colados por cima
5. CTA principal e CTA secundario pertencem a mesma familia visual

## 5. Checklist de dark mode

O card so pode ser considerado pronto se:

1. `title` usa tinta de manchete e nao glow lavado
2. `copy` e `label` continuam legiveis sem parecerem cinza morto
3. `field-label` nao fala baixo demais
4. texto digitado em `input`, `select`, `textarea` continua legivel
5. `placeholder` fica mais fraco que o valor real, mas nao some
6. `option`, `option:checked` e `option:hover` recebem tratamento minimo quando houver `select`
7. nenhum subcard cria segunda moldura dentro do host

## 6. Contrato de controles nativos

Sempre que um card trouxer `input`, `select` ou `textarea`, fechar no contexto local:

1. `color`
2. `caret-color`
3. `-webkit-text-fill-color` quando houver risco de texto escuro no dark
4. `background`
5. `border-color`
6. `::placeholder`
7. `:focus`
8. `color-scheme` quando fizer sentido
9. `option` e `option:checked` para `select`

Regra honesta:

1. popup nativo de `select` pode continuar parcialmente dependente do navegador
2. so usar `custom select` se o ganho visual for real e a manutencao compensar

## 7. Sequencia de implementacao com menor arrependimento

Quando um card novo nascer:

1. confirmar anatomia do template
2. encaixar o host na familia canonica
3. aplicar light mode completo
4. aplicar dark mode completo
5. revisar controles nativos
6. revisar subcards internos
7. validar screenshot mental: titulo, copy, labels, CTA, estados

## 8. Sinais de que o card nasceu torto

Se qualquer um destes aparecer, pare cedo:

1. glow no titulo melhora "estilo" mas piora leitura
2. `field-label` so fica bom com cor muito especifica em um ponto isolado
3. o card precisa de muito `body[data-theme="dark"]` para sobreviver
4. o `select` fechado fica bom, mas o aberto continua desastre e ninguem registrou esse limite
5. a tela começa a corrigir pill por pill, texto por texto, sem definir owner

## 9. Definicao de pronto

Um card novo esta pronto quando:

1. parece da mesma familia no light
2. parece da mesma familia no dark
3. o titulo nao pede tradutor
4. o texto digitado nao desaparece
5. o proximo ajuste nao exige detetive para descobrir quem manda

Em resumo:

1. card bom nasce com ownership claro
2. card premium nasce com anatomia correta
3. card sustentavel nasce com light e dark pensados juntos
