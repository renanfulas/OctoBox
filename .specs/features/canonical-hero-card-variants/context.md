# Context

## Locked Decisions

1. `hero`, `card` e `table-card` precisam virar familias realmente canonicas.
2. CSS local nao pode continuar repintando superficie, borda e sombra como se cada pagina tivesse seu proprio tema.
3. Variantes oficiais sao o caminho certo para escala, previsibilidade e manutencao.

## Why This Mountain Exists

O trabalho recente de dark mode mostrou um padrao repetido:

1. os hosts canonicos existem
2. varias telas ainda colocam outro acabamento estrutural por cima
3. qualquer ajuste global vira perseguicao tela por tela

Em linguagem simples:

- hoje temos um mesmo carro com varios volantes improvisados
- a meta agora e voltar a ter uma direcao unica com ajustes oficiais de banco e espelho

## Boundaries

Esta feature nao deve virar:

1. redesign completo do produto
2. migracao total de todos os CSS em uma unica rodada
3. troca de markup em massa sem necessidade

O escopo e:

1. contrato canonico das familias `hero`, `card` e `table-card`
2. sistema oficial de variantes
3. regras de ownership para impedir repaint local
4. migracao inicial das superficies mais importantes
