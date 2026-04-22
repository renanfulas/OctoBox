# Context

## Problema

As paginas principais do OctoBox ja estao mais coesas, mas o bloco de hero ainda varia demais por tela.

Hoje o owner representa o melhor padrao visual desejado:

- mesma caixa
- alinhamento claro
- hierarquia forte
- botoes organizados em trilho consistente

O problema e que esse padrao ainda nao virou contrato universal.

## Risco atual

Se tentarmos "deixar tudo com cara do owner" por copia local de HTML e CSS:

- teremos heros parecidos, mas nao iguais
- cada tela carregara pequenas excecoes
- ajustes futuros vao gerar regressao silenciosa

## Tese

Transformar o hero do owner em um padrao canonico do sistema:

- texto em espinha dorsal fixa
- action rail fora do corpo principal
- mesma estrutura de espacamento, alinhamento e tipografia
- variacoes controladas por contrato, nao por improviso local
