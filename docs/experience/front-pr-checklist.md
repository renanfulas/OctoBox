<!--
ARQUIVO: checklist curto de PR para front-end.

TIPO DE DOCUMENTO:
- checklist operacional

AUTORIDADE:
- media

DOCUMENTO PAI:
- [front-display-wall.md](front-display-wall.md)

QUANDO USAR:
- quando a duvida for como revisar uma alteracao de front antes de considerar a entrega pronta

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

Se a duvida for como pensar ou montar a tela desde o inicio, use [layout-decision-guide.md](layout-decision-guide.md).

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
4. alvos de toque tem tamanho adequado em mobile

## Acessibilidade

1. elementos interativos tem estado de foco visivel
2. contraste de texto contra fundo esta aceitavel
3. cor nao e o unico indicador de estado
4. labels estao vinculados aos campos de formulario

## Estados e leitura

1. estado vazio orienta proxima acao
2. alerta, confirmacao e erro seguem o mesmo padrao visual da base
3. a acao principal continua clara em ate poucos segundos de leitura
4. prioridade, pendencia e proxima acao continuam evidentes na composicao da pagina
5. toda acao do usuario tem feedback visivel

## Formularios

1. campos tem type e inputmode corretos para o dado esperado
2. placeholder nao esta substituindo label
3. erro aparece perto do campo e diz como corrigir
4. acao irreversivel pede confirmacao explicita

## Higiene

1. nao ficou classe usada no template sem seletor correspondente no CSS relevante
2. nao foi deixado CSS morto ou seletor legado sem uso claro
3. editor ficou sem erros nos arquivos alterados
4. testes da area afetada foram executados quando a mudanca mexe em tela relevante

## Gate de beta

1. a mudanca melhora uma superficie central do beta ou reduz risco real dela
2. a tela ficou mais clara e nao apenas mais diferente
3. a triagem futura consegue localizar melhor pagina, painel, acao ou estado
4. hooks estruturais relevantes continuam estaveis ou ficaram melhores
5. a mudanca nao reabriu estrutura consolidada sem justificativa forte
