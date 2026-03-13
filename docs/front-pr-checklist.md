<!--
ARQUIVO: checklist curto de PR para front-end.

POR QUE ELE EXISTE:
- reduz regressao visual e obriga uma checagem minima antes de subir mudancas de front.

O QUE ESTE ARQUIVO FAZ:
1. resume as validacoes mais importantes para CSS, templates e comportamento visual.
2. transforma o guide de CSS em uma rotina curta de revisao.
3. ajuda a detectar classe sem contrato, layout fragil e responsividade quebrada.

PONTOS CRITICOS:
- este checklist precisa continuar curto para ser realmente usado em PR.
- qualquer item aqui deve apontar para risco real da base, nao para burocracia.
-->

# Checklist curto de PR para front

Use este checklist antes de aprovar ou subir alteracoes de front.

## Estrutura

1. cada classe nova esta no arquivo CSS certo
2. nomes de classe descrevem papel, nao apenas aparencia
3. blocos importantes da tela tem contrato explicito no CSS local da area
4. nao foi criada dependencia fragil de heranca ou utilitario por coincidencia

## Layout

1. o grid principal deixa claro quem ocupa largura total, coluna principal e trilho lateral
2. cards que precisam alinhar entre si continuam com altura e CTA consistentes
3. nenhum bloco ficou apertado, solto ou competindo por causa de largura errada
4. anchors continuam pousando bem quando a tela usa topbar sticky

## Responsividade

1. desktop, tablet e mobile continuam legiveis
2. grids quebram antes de virar mosaico apertado
3. botoes continuam clicaveis e legiveis em largura menor

## Estados e leitura

1. estado vazio orienta proxima acao
2. alerta, confirmacao e erro seguem o mesmo padrao visual da base
3. a acao principal continua clara em ate poucos segundos de leitura

## Higiene

1. nao ficou classe usada no template sem seletor correspondente no CSS relevante
2. nao foi deixado CSS morto ou seletor legado sem uso claro
3. editor ficou sem erros nos arquivos alterados
4. testes da area afetada foram executados quando a mudanca mexe em tela relevante
