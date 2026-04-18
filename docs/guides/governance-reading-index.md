<!--
ARQUIVO: indice de governanca de leitura por perfil do OctoBox.

TIPO DE DOCUMENTO:
- indice de governanca
- guia de onboarding por perfil

AUTORIDADE:
- media para orientar ordem de leitura
- baixa para substituir guias tecnicos e docs canonicos

DOCUMENTO PAI:
- [README.md](./README.md)

DOCUMENTOS IRMAOS:
- [../reference/documentation-authority-map.md](../reference/documentation-authority-map.md)
- [../reference/reading-guide.md](../reference/reading-guide.md)

QUANDO USAR:
- quando alguem novo entrar no projeto
- quando a duvida for "o que eu leio primeiro pelo meu papel?"
- quando for organizar onboarding sem sobrecarregar a pessoa com o predio inteiro

POR QUE ELE EXISTE:
- reduz sobrecarga cognitiva no onboarding
- cria trilhas de leitura por responsabilidade real
- separa orientacao por perfil de leitura tecnica profunda

PONTOS CRITICOS:
- este indice orienta leitura, nao substitui ownership real do codigo
- se os docs de destino mudarem, este indice deve ser atualizado
-->

# Indice de governanca de leitura

## Ideia central

Nem toda pessoa deve entrar no projeto pela mesma porta.

Em um predio grande, a recepcao nao manda todo mundo primeiro para a sala de maquinas.

Ela pergunta:

1. voce veio consertar encanamento?
2. veio cuidar da fachada?
3. veio operar o predio?
4. veio revisar a planta inteira?

Este documento faz exatamente isso para o OctoBox.

## Regra de uso

1. primeiro identifique o perfil principal da pessoa
2. depois siga a trilha curta sugerida
3. so entao aprofunde nos docs tecnicos e no codigo real

## Perfis oficiais desta trilha

1. [Dev Junior](./profiles/dev-junior-reading-path.md)
2. [Dev Senior](./profiles/dev-senior-reading-path.md)
3. [Frontend](./profiles/frontend-reading-path.md)
4. [Backend](./profiles/backend-reading-path.md)
5. [Deploy e Operacao](./profiles/deploy-reading-path.md)

## Regra de prioridade de leitura

### Camada 1. Orientacao

Objetivo:

1. entender o produto e a forma geral do predio

Docs-base:

1. [../../README.md](../../README.md)
2. [README.md](./README.md)
3. [general-architecture-guide.md](./general-architecture-guide.md)

### Camada 2. Metodo

Objetivo:

1. entender como o projeto pensa, organiza e decide

Docs-base:

1. [methodology-and-organization-guide.md](./methodology-and-organization-guide.md)
2. [../reference/documentation-authority-map.md](../reference/documentation-authority-map.md)

### Camada 3. Especialidade

Objetivo:

1. entrar no corredor certo por area de responsabilidade

Docs-base:

1. frontend, backend, CSS, performance, seguranca ou deploy

### Camada 4. Navegacao tecnica

Objetivo:

1. localizar arquivos, ownership e fluxo real do runtime

Docs-base:

1. [../reference/reading-guide.md](../reference/reading-guide.md)
2. mapas de ownership da area

## Quando usar cada trilha

Use a trilha `Dev Junior` quando a pessoa ainda precisa entender o terreno sem se afogar em detalhe tecnico cedo demais.

Use a trilha `Dev Senior` quando a pessoa vai revisar arquitetura, criar corredor novo ou tomar decisao com efeito estrutural.

Use a trilha `Frontend` quando a pessoa vai tocar interface, contratos de tela, layout, CSS ou experiencia.

Use a trilha `Backend` quando a pessoa vai tocar regra de negocio, leitura, mutacao, integracao ou organizacao de dominio.

Use a trilha `Deploy e Operacao` quando a pessoa vai publicar, restaurar, medir, endurecer ou operar ambiente.

## Regra contra sobrecarga

Se a pessoa abrir mais de 3 docs profundos sem ainda conseguir responder:

1. o que o produto faz
2. onde sua area mora
3. qual doc manda na sua frente

entao ela entrou no predio pela porta errada.

Volte para:

1. [general-architecture-guide.md](./general-architecture-guide.md)
2. o guia de perfil correspondente
