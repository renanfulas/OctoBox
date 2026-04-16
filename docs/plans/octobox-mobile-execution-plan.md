<!--
ARQUIVO: plano de execucao do OctoBox Mobile em fases tecnicas.

TIPO DE DOCUMENTO:
- execucao ativa de arquitetura

AUTORIDADE:
- alta

DOCUMENTO PAI:
- [../architecture/octobox-mobile-architecture.md](../architecture/octobox-mobile-architecture.md)

QUANDO USAR:
- quando a duvida for qual ordem tecnica seguir para implementar o mobile do OctoBox sem misturar PWA, autenticacao, grade e publicacao consolidada

POR QUE ELE EXISTE:
- transforma a arquitetura mobile em ordem de entrega executavel.
- evita que o time implemente partes chamativas fora da sequencia correta e crie divida tecnica prematura.

O QUE ESTE ARQUIVO FAZ:
1. quebra o mobile em quatro trilhas de execucao.
2. define dependencias, criterio de pronto, risco e entregas por fase.
3. estabelece a ordem oficial de rollout.
4. registra o que nao deve entrar antes da hora.

PONTOS CRITICOS:
- auth social nao deve entrar antes da base de sessao mobile persistente estar correta.
- a Grade de Aulas mobile nao deve nascer acoplada ao HTML desktop atual.
- o pipeline draft/publish nao deve ser implementado antes de existir snapshot published confiavel.
-->

# Plano de execucao do OctoBox Mobile

## Tese de execucao

O mobile do OctoBox deve ser implementado em quatro trilhas principais:

1. PWA + sessao persistente
2. autenticacao social
3. snapshot engine da Grade de Aulas
4. draft/publish pipeline de 5 minutos

A ordem importa.

Se o time pular fases, o resultado tende a ser um PWA bonito com sessao ruim, ou uma grade rapida em teoria, mas sem consistencia real.

## Regra oficial de ordem

### Ordem obrigatoria

1. PWA + sessao persistente
2. auth social
3. snapshot engine da Grade de Aulas
4. draft/publish pipeline de 5 minutos

### Motivo

1. o PWA sem sessao persistente continua parecendo navegador travestido.
2. auth social em cima de sessao ruim so esconde o problema em vez de resolve-lo.
3. o pipeline de draft nao pode existir antes de published snapshot confiavel.
4. a grade mobile precisa provar leitura leve antes de ganhar escrita consolidada.

## Mapa de dependencias

### Trilha 1 depende de

nenhuma das outras trilhas

### Trilha 2 depende de

1. sessao mobile persistente bem definida
2. politicas de cookie e dispositivo confiavel revisadas

### Trilha 3 depende de

1. PWA funcional
2. sessao persistente pronta
3. contrato de API/payload mobile definido para a grade

### Trilha 4 depende de

1. snapshot published implementado
2. sync por versao/hash funcionando
3. fronteira entre draft e published definida

## Trilha 1: PWA + sessao persistente

### Objetivo

Fazer o OctoBox abrir como app e parar de expulsar o usuario do celular.

### Entregas tecnicas

1. `manifest.webmanifest`
2. icones PWA oficiais
3. meta tags mobile no `base.html`
4. service worker minimo para shell e instalacao
5. revisao da politica de sessao mobile
6. revisao da expiracao por fechamento do navegador
7. politica de dispositivo confiavel

### Mudancas de configuracao esperadas

1. revisar `SESSION_COOKIE_AGE`
2. revisar `SESSION_EXPIRE_AT_BROWSER_CLOSE`
3. manter cookies `Secure` e `HttpOnly`
4. manter sessao em cache quente

### Criterio de pronto

1. o app pode ser instalado em Android e iPhone.
2. o usuario abre por icone e retorna a uma sessao valida sem login recorrente agressivo.
3. o shell principal abre em modo standalone.
4. nao existe credencial crua salva no client.

### Riscos

1. afrouxar sessao alem do seguro.
2. tratar PWA como se fosse offline app.
3. quebrar logout, fingerprint ou seguranca por cookie ao alongar a sessao.

### Fora de escopo nesta fase

1. login Google
2. login Apple
3. otimizar Grade de Aulas
4. draft/publish

## Trilha 2: auth social

### Objetivo

Reduzir o atrito de entrada no celular sem criar autenticacao artesanal insegura.

### Entregas tecnicas

1. `Entrar com Google`
2. `Entrar com Apple`
3. mapeamento de usuario social para papel interno do OctoBox
4. regras de onboarding para conta sem papel
5. tratamento de colisao entre identidade social e identidade interna

### Regras

1. auth social nao substitui sessao persistente; ele a alimenta.
2. auth social nao deve criar usuario com papel automatico sem regra de negocio.
3. auth social precisa cair no mesmo contrato de seguranca da sessao Django.

### Criterio de pronto

1. usuario Android entra com Google.
2. usuario iPhone entra com Apple.
3. a sessao permanece viva no PWA.
4. o papel interno continua governando o acesso do produto.

### Riscos

1. login social sem mapeamento de papel.
2. criar contas soltas sem ownership operacional.
3. quebrar o modelo atual de acesso por papel do produto.

### Fora de escopo nesta fase

1. Passkey
2. biometria dedicada
3. refresh token proprio no client

## Trilha 3: snapshot engine da Grade de Aulas

### Objetivo

Fazer a Grade de Aulas mobile parecer instantanea e escalar por snapshot compartilhado em vez de refresh individual pesado.

### Entregas tecnicas

1. contrato de payload mobile da grade
2. endpoint de leitura published
3. snapshot `today`
4. snapshot `week`
5. metadata `version`, `generated_at`, `hash`
6. Ghost Resume local
7. sync por versao/hash
8. cooldown de refresh manual
9. invalidacao por eventos importantes

### Regra de arquitetura

Nesta fase ainda nao existe draft/publish completo.

Existe apenas leitura published confiavel, rapida e barata.

### Criterio de pronto

1. a grade mobile abre instantaneamente com ultimo snapshot local.
2. a sincronizacao nao recompõe tudo por refresh individual.
3. o servidor consegue responder `sem mudancas` quando a versao bate.
4. leitura em massa usa cache quente compartilhado.

### Metricas esperadas

1. forte reducao de carga por refresh repetitivo.
2. queda grande da latencia percebida de abertura da grade.
3. reducao real do custo por leitura comparado ao HTML desktop montado toda vez.

### Riscos

1. payload mobile gordo demais.
2. snapshot acoplado demais ao template desktop.
3. comparacao de hash mal definida e sujeita a falso positivo.

### Fora de escopo nesta fase

1. draft view
2. ticket de 5 minutos
3. resumo de mudancas
4. emergency handoff

## Trilha 4: draft/publish pipeline de 5 minutos

### Objetivo

Fazer a escrita da grade escalar por publicacao consolidada e nao por microalteracao.

### Entregas tecnicas

1. ticket de mudancas da grade
2. janela fixa de 5 minutos
3. draft view para o editor
4. resumo consolidado de mudancas
5. fechamento do ticket em estado final
6. comparacao por delta material
7. regeneracao apenas dos recortes afetados
8. publicacao da nova versao
9. atalho humano de urgencia via WhatsApp

### Regras

1. o editor ve draft.
2. os demais usuarios veem apenas published.
3. urgencia nao publica por automacao especial; ela sai para a mao humana.

### Criterio de pronto

1. um editor consegue alterar varias aulas dentro da janela.
2. ele ve as mudancas imediatamente no proprio editor.
3. o sistema mostra resumo do que mudou.
4. o ticket publica o estado final consolidado.
5. a grade published muda uma vez por lote, nao a cada clique.

### Metricas esperadas

1. reducao brutal de recomputacao por microedicao.
2. maior previsibilidade de carga durante picos operacionais.
3. manutencao de custo baixo em escala.

### Riscos

1. confusao entre draft e published.
2. falta de auditoria clara do que entrou no ticket.
3. fechamento de janela sem UX suficiente para o editor confiar.

### Fora de escopo nesta fase

1. publicacao instantanea por "publicar agora"
2. automacao de WhatsApp para cada ticket
3. urgencia automatica sem intervencao humana

## API e contratos necessarios

### Contratos minimos da trilha mobile

1. endpoint de bootstrap do PWA
2. endpoint de identidade de sessao atual
3. endpoint de snapshot published da grade
4. endpoint de sync por versao/hash
5. endpoint de estado do ticket de grade
6. endpoint de resumo de mudancas do ticket

### Regra

Os contratos mobile devem ser pensados como contratos de API, nao como reaproveitamento acidental de HTML.

## Ordem de rollout recomendada

### Sprint 0: readiness

1. decidir nomes de contratos
2. decidir storage local do Ghost Resume
3. decidir modelo de sessao mobile
4. decidir stack de auth social

### Sprint 1: PWA + sessao

1. manifest
2. icones
3. shell standalone
4. sessao persistente

### Sprint 2: auth social

1. Google
2. Apple
3. mapeamento de identidade

### Sprint 3: published snapshot

1. payload mobile da grade
2. endpoint published
3. Ghost Resume
4. sync por hash

### Sprint 4: hardening do snapshot

1. invalidacao por evento
2. cooldown de refresh
3. metricas de custo

### Sprint 5: draft/publish

1. ticket de 5 minutos
2. draft view
3. resumo de mudancas
4. publish consolidado

### Sprint 6: emergency handoff

1. CTA de urgencia
2. integracao com API do WhatsApp
3. texto livre na mao humana

## O que nao deve acontecer

1. construir auth social antes de resolver sessao.
2. construir draft antes de published.
3. usar a grade desktop como API improvisada do mobile.
4. tentar fazer tudo em uma unica release.
5. misturar OctoPASS com esta entrega.

## Definicao de sucesso por camada

### Acesso

O usuario abre o icone e nao sente que esta num navegador.

### Entrada

O usuario entra uma vez e esquece o problema de login repetido.

### Leitura

A Grade de Aulas abre como leitura pronta, nao como tela esperando montar.

### Escrita

O editor sente controle imediato no draft sem derrubar custo global de publicacao.

## Decisao final de execucao

O plano oficial do OctoBox Mobile e:

1. primeiro garantir acesso e sessao
2. depois reduzir atrito de autenticacao
3. depois tornar a Grade de Aulas instantanea em leitura
4. por fim tornar a escrita consolidada e barata em escala

Essa e a ordem que preserva produto, seguranca e performance ao mesmo tempo.
