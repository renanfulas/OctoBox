<!--
ARQUIVO: indice da trilha guiada de arquitetura viva do OctoBox.

TIPO DE DOCUMENTO:
- guia de entrada
- indice de navegacao

AUTORIDADE:
- media para onboarding arquitetural
- baixa para substituir docs canonicos de architecture, plans e reference

DOCUMENTO PAI:
- [../reference/documentation-authority-map.md](../reference/documentation-authority-map.md)

QUANDO USAR:
- quando a duvida for "por onde eu comeco?"
- quando voce quiser uma leitura mais pratica e menos espalhada da arquitetura atual
- quando voce precisar explicar o projeto para alguem novo sem jogar a pessoa em 20 docs profundos de uma vez

POR QUE ELE EXISTE:
- cria uma camada de orientacao acima dos docs profundos ja existentes
- separa "guia de entendimento" de "documento de tese" e de "plano de execucao"
- resume o estado vivo do projeto sem apagar a riqueza da documentacao anterior

PONTOS CRITICOS:
- este indice nao substitui o codigo real
- se os docs profundos mudarem, este indice precisa apontar para os novos corredores oficiais
-->

# Guias de arquitetura viva

Esta pasta existe para resolver um problema simples:

1. o OctoBox tem muita documentacao boa
2. mas boa parte dela esta em profundidade, por frente, por plano ou por camada
3. quem chega agora pode entender o predio melhor se primeiro enxergar o mapa geral

Pense nesta pasta como a recepcao do predio:

1. aqui voce entende como a obra ficou mais madura
2. aqui voce ve o que virou padrao de verdade
3. aqui voce descobre qual documento profundo abrir depois

## Ordem recomendada de leitura

1. [governance-reading-index.md](./governance-reading-index.md)
2. [general-architecture-guide.md](./general-architecture-guide.md)
3. [methodology-and-organization-guide.md](./methodology-and-organization-guide.md)
4. [backend-architecture-guide.md](./backend-architecture-guide.md)
5. [frontend-architecture-guide.md](./frontend-architecture-guide.md)
6. [css-architecture-guide.md](./css-architecture-guide.md)
7. [performance-architecture-guide.md](./performance-architecture-guide.md)
8. [security-architecture-guide.md](./security-architecture-guide.md)

## O que esta trilha faz

Ela resume:

1. o que o projeto usa hoje de forma recorrente
2. o que ficou mais eficiente em relacao ao inicio
3. o que ja e regra viva e o que ainda e transicao
4. quais riscos de divida tecnica precisam continuar no radar

## O que esta trilha nao faz

Ela nao tenta:

1. reescrever os docs profundos de `docs/architecture`
2. competir com os planos de `docs/plans`
3. substituir o mapa de ownership de `docs/reference`
4. vencer o runtime real quando o codigo disser outra coisa

## Atalho rapido por pergunta

Se a pergunta for "como o sistema esta organizado hoje?", comece por [general-architecture-guide.md](./general-architecture-guide.md).

Se a pergunta for "qual caminho de leitura eu devo seguir pelo meu perfil?", comece por [governance-reading-index.md](./governance-reading-index.md).

Se a pergunta for "como o time esta trabalhando melhor do que no comeco?", use [methodology-and-organization-guide.md](./methodology-and-organization-guide.md).

Se a pergunta for "onde deve nascer regra de negocio nova?", use [backend-architecture-guide.md](./backend-architecture-guide.md).

Se a pergunta for "como a fachada visual conversa com o backend?", use [frontend-architecture-guide.md](./frontend-architecture-guide.md).

Se a pergunta for "onde entra CSS novo sem virar remendo?", use [css-architecture-guide.md](./css-architecture-guide.md).

Se a pergunta for "o que ficou mais rapido e como preservar isso?", use [performance-architecture-guide.md](./performance-architecture-guide.md).

Se a pergunta for "qual e a linha atual de endurecimento e seguranca?", use [security-architecture-guide.md](./security-architecture-guide.md).

## Trilhas por perfil

Para leitura guiada por papel no time:

1. [governance-reading-index.md](./governance-reading-index.md)
2. [profiles/dev-junior-reading-path.md](./profiles/dev-junior-reading-path.md)
3. [profiles/dev-senior-reading-path.md](./profiles/dev-senior-reading-path.md)
4. [profiles/frontend-reading-path.md](./profiles/frontend-reading-path.md)
5. [profiles/backend-reading-path.md](./profiles/backend-reading-path.md)
6. [profiles/deploy-reading-path.md](./profiles/deploy-reading-path.md)
