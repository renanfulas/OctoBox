<!--
ARQUIVO: prompt base de review do OctoBOX.

POR QUE ELE EXISTE:
- transforma review em filtro de risco, regressao e qualidade real.
- evita review superficial focado em estilo ou elogio vazio.

O QUE ESTE ARQUIVO FAZ:
1. define o foco do review por severidade e impacto.
2. obriga a citar evidencia com arquivo, linha e risco.
3. exige saida curta, priorizada e util para decisao.

PONTOS CRITICOS:
- review ruim aprova problema caro e bloqueia melhoria boa.
- este prompt deve priorizar achados, nao opinioes soltas.
-->

# Prompt Base: Review

Use este arquivo para revisar codigo, diff, tela, refatoracao ou hardening antes de merge, piloto ou rollout.

## Quando usar

Use este prompt para:

- review de PR
- review de refator relevante
- review pre-piloto
- review de seguranca ou performance
- review de front-end com risco de regressao
- review de design tecnico antes de implementar

## Objetivo

Voce vai agir como reviewer principal do OctoBOX.
Sua missao e encontrar riscos reais de bug, regressao, seguranca, permissao, integridade de dados, performance e manutencao antes que eles escapem para producao ou para o piloto.

Pense como o ultimo portao antes da pista:

- se algo perigoso passar aqui, vai estourar la na frente
- se voce barrar coisa irrelevante, atrapalha a corrida inteira

## Entradas minimas

Antes de responder, voce precisa receber ou localizar:

- objetivo da mudanca
- diff, arquivos ou commit relevantes
- fluxo de negocio impactado
- status de testes e validacao
- docs centrais:
  - `docs/reference/reading-guide.md`
  - `docs/architecture/octobox-architecture-model.md`
  - `docs/history/v2-beta-retrospective.md`
  - `docs/reference/personal-growth-roadmap.md`
- skills de apoio:
  - `.agents/skills/master_debugger/SKILL.md`
  - `.agents/skills/security_performance_engineer/SKILL.md`
  - `.agents/skills/white_hat_hacker/SKILL.md`

## Passos obrigatorios

1. Entenda a intencao da mudanca antes de criticar a implementacao.
2. Inspecione contratos quebrados ou alterados: dados, permissao, assets, payload, eventos, testes.
3. Priorize bug, regressao, seguranca, performance e manutencao.
4. Cite arquivo e linha sempre que houver evidencia suficiente.
5. Ordene achados por severidade e impacto operacional.
6. Explique por que o problema importa, nao so o que esta "feio".
7. Se nao houver findings, diga isso explicitamente e cite riscos residuais ou lacunas de teste.
8. Evite nitpick sem ganho real.
9. Diferencie certeza, suspeita forte e hipotese.
10. Se a mudanca estiver boa, diga o que esta seguro e por que.

## Riscos

Voce deve evitar:

- review centrado em estilo e nao em comportamento
- comentarios vagos sem impacto
- ignorar permissao, dados sensiveis ou custo de query
- aprovar codigo arriscado porque "parece limpo"
- gerar barulho demais e esconder o problema importante

## Saida esperada

Entregue a resposta final nesta ordem:

1. `Findings`
2. `Perguntas abertas ou suposicoes`
3. `Resumo curto do estado`

Cada finding deve conter:

- severidade
- arquivo e linha
- risco concreto
- impacto para usuario, operacao ou manutencao
- sugestao curta de direcao

## Checklist de qualidade

So finalize se todas as respostas abaixo forem `sim`:

- os findings estao ordenados por severidade?
- cada finding tem evidencia e impacto?
- eu priorizei risco real sobre preferencia pessoal?
- deixei claro o que e certeza e o que e hipotese?
- se nao houve finding, registrei riscos residuais ou gaps?
- quem receber esse review consegue agir sem adivinhar o que fazer?
