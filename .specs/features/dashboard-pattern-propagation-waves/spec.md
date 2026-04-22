# Spec

## Objetivo

Criar uma frente oficial para propagar os padroes visuais e estruturais validados no dashboard para as outras paginas do OctoBox sem copiar CSS local de forma cega e sem criar debito tecnico.

## Resultado esperado

- os ganhos do dashboard passam primeiro por promocao para componente compartilhado
- as paginas irmas recebem a nova linguagem por ondas controladas
- cada tela adapta apenas sua composicao local, sem reinventar `hero`, `card`, `table-card`, `topbar` ou `sidebar`
- a evolucao visual fica rastreavel tanto em `.specs/features` quanto em `docs/plans`
- os skills `octobox-design` e `CSS Front end architect` viram obrigatorios nessa frente

## Pergunta central que esta spec responde

Como replicar nas outras paginas o que funcionou no dashboard sem transformar a base em uma colcha de remendos visuais?

