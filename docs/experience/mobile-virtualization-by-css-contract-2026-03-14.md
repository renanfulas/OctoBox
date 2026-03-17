<!--
ARQUIVO: leitura virtual mobile por contrato CSS para superficies alem da rodada 1.

TIPO DE DOCUMENTO:
- analise tecnica de aproximacao

AUTORIDADE:
- apoio tecnico, nao validacao fisica final

DOCUMENTO PAI:
- [mobile-real-validation-checklist.md](mobile-real-validation-checklist.md)

QUANDO USAR:
- quando a emulacao fisica do browser integrado falhar e ainda for util estimar o comportamento mobile pelas regras reais de CSS

POR QUE ELE EXISTE:
- transforma breakpoints, larguras minimas e overflow em leitura operacional.
- evita fingir uma emulacao fisica que o ambiente nao entregou.
- ajuda a priorizar onde a validacao externa real precisa olhar primeiro.

O QUE ESTE ARQUIVO FAZ:
1. estima o comportamento de recepcao, ficha leve, financeiro e grade em largura parecida com iPhone 13 retrato.
2. separa o que parece ok do que permanece toleravel ou sensivel.
3. registra watchpoints para a rodada externa real.

PONTOS CRITICOS:
- isto nao substitui navegador externo nem aparelho fisico.
- o resultado aqui e inferencia tecnica baseada no CSS efetivo da aplicacao.
-->

# Virtualizacao mobile por contrato CSS

## Base da simulacao

Referencia adotada:

1. iPhone 13 em retrato como largura estreita perto de 390px

Metodo:

1. leitura de breakpoints reais
2. leitura de min-width e overflow
3. leitura de empilhamento de grids e acoes

## Recepcao

Leitura virtual:

1. provavel ok com vigilancia moderada

Evidencias estruturais:

1. em [../../static/css/design-system/operations.css](../../static/css/design-system/operations.css), abaixo de 1280px o trilho de suporte cai para 1 coluna
2. abaixo de 960px o hero operacional vira coluna unica
3. abaixo de 720px os grids de pagamento e de grade da recepcao viram 1 coluna
4. metas e stats internos tambem viram 1 coluna abaixo de 720px

Watchpoints:

1. tabelas que usam .operation-table-wrap ainda podem exigir scroll horizontal
2. em [static/css/design-system/operations.css](static/css/design-system/operations.css), tabelas dentro desse wrap chegam a min-width de 560px abaixo de 720px

Conclusao curta:

1. cards, formularios e grids principais parecem bem preparados
2. o risco residual continua concentrado em leitura tabular, nao em colapso geral da pagina

## Ficha leve do aluno

Leitura virtual:

1. provavel ok com vigilancia leve

Evidencias estruturais:

1. em [../../static/css/catalog/shared.css](../../static/css/catalog/shared.css), field-grid-200, 220 e 240 usam auto-fit com minmax de 200px, 220px e 240px
2. em 390px esses grids tendem a empilhar em 1 coluna naturalmente quando nao couberem duas
3. o formulario foi montado por passos e disclosures, o que ajuda a leitura vertical em tela estreita

Watchpoints:

1. densidade vertical de alguns passos pode aumentar bastante
2. o resumo financeiro na mesma tela ainda merece confirmacao fisica para toque e leitura longa

Conclusao curta:

1. a ficha leve tende a sobreviver bem em mobile
2. o risco parece mais de fadiga vertical do que de quebra estrutural

## Financeiro

Leitura virtual:

1. provavel ok com vigilancia moderada

Evidencias estruturais:

1. em [static/css/catalog/finance.css](static/css/catalog/finance.css), abaixo de 960px os layouts principais caem para 1 coluna
2. abaixo de 960px clusters de fila, regua, summary e listas passam para 1 coluna
3. abaixo de 720px metric strip e plan grid passam para 1 coluna
4. acoes compactas passam a esticar e seus botoes vao para largura total

Watchpoints:

1. alguns grids usam minmax de 300px e 340px antes de colapsar, então o limiar de conforto em 390px precisa ser confirmado fisicamente
2. o financeiro e uma tela densa e pode ficar longa demais mesmo sem quebrar

Conclusao curta:

1. o contrato CSS parece maduro para evitar colapso grosseiro
2. a principal vigilancia e conforto de leitura e densidade, nao overflow estrutural grave

## Grade de aulas

Leitura virtual:

1. provavel ok com vigilancia moderada

Evidencias estruturais:

1. em [../../static/css/catalog/class-grid.css](../../static/css/catalog/class-grid.css), abaixo de 960px varios paineis e headers caem para coluna unica
2. a visao semanal cai para 2 colunas abaixo de 960px e para 1 coluna abaixo de 640px
3. o preview mensal tambem cai para 1 coluna abaixo de 640px
4. acoes de chip e botoes internos passam para largura total em largura menor

Watchpoints:

1. o componente de ocupacao ainda usa min-width de 200px em um ponto e merece observacao fisica
2. a grade pode ficar muito longa em retrato, mesmo sem quebrar

Conclusao curta:

1. a grade parece melhor preparada para empilhar do que para manter miniaturas densas
2. isso tende a favorecer legibilidade em 390px, com custo de altura e scroll

## Resumo geral desta virtualizacao

1. recepcao: provavel ok
2. ficha leve do aluno: provavel ok
3. financeiro: provavel ok
4. grade de aulas: provavel ok
5. principal toleravel conhecido continua sendo o diretorio de alunos por causa da tabela com largura minima

## Regra de interpretacao

Leia este documento assim:

1. ele ajuda a priorizar o olhar da rodada externa real
2. ele nao encerra validacao mobile fisica
3. ele existe para evitar conclusao fraca baseada numa emulacao que o ambiente nao respeitou