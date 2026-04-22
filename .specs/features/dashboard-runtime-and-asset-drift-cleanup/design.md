# Design

## Decisao 1

### Fonte de verdade da abertura

A abertura viva do dashboard passa a ser declarada explicitamente como:

1. `page_reading_list` em variante propria do dashboard

E nao:

1. `priority_strip`
2. `dashboard_glance_card`

## Decisao 2

### Separacao de variante

Se o dashboard precisa de:

1. semaforo por severidade
2. numero real em vez de ordinal
3. comportamento `is_tranquil`
4. nao clicavel quando nao ha pendencia

entao isso deve viver em uma variante propria:

1. template proprio
ou
2. include pequeno especifico do dashboard

Nao em ramificacoes longas dentro de `page_reading_list.html`.

## Decisao 3

### Asset drift

`staticfiles/` nao pode continuar sendo uma surpresa.

Precisamos de um contrato:

1. ou o desenvolvimento le de `static/` como unica fonte de verdade
2. ou a regeneracao de `staticfiles/` fica automatica e inevitavel

## Decisao 4

### Regra fantasma

Tudo que continuar no projeto precisa ter uma resposta clara:

1. runtime vivo
2. legado controlado
3. artefato morto a remover

Sem essa classificacao, o dashboard continua parecendo duas fachadas sobrepostas.
