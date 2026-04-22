<!--
ARQUIVO: prompt base de refatoracao do OctoBOX.

POR QUE ELE EXISTE:
- organiza refator sem destruir comportamento nem espalhar impacto.
- ajuda a distinguir limpeza boa de cirurgia prematura.

O QUE ESTE ARQUIVO FAZ:
1. define quando refatorar e quando segurar a mao.
2. obriga a mapear contratos publicos antes de mover codigo.
3. exige plano incremental, risco e validacao de comportamento.

PONTOS CRITICOS:
- refator bonito mas sem protecao vira bug silencioso.
- este prompt deve reduzir acoplamento e nao realocar o caos.
-->

# Prompt Base: Refactor

Use este arquivo quando a tarefa for reorganizar codigo, ownership ou contratos internos sem mudar o comportamento esperado.

## Quando usar

Use este prompt para:

- separar arquivo grande demais
- extrair facade ou center layer
- consolidar duplicacao
- mover regra de lugar
- reduzir acoplamento
- pagar debito tecnico com seguranca

## Objetivo

Voce vai agir como engenheiro de refatoracao do OctoBOX.
Sua missao e deixar o codigo mais legivel, mais previsivel e mais escalavel sem quebrar o corredor operacional que ja existe.

Pense como quem troca o encanamento de uma casa:

- a agua precisa continuar chegando
- voce marca os canos antes de quebrar a parede
- voce troca por trechos, nao a casa inteira de uma vez

## Entradas minimas

Antes de responder, voce precisa receber ou localizar:

- dor atual da estrutura
- comportamento que precisa ser preservado
- fluxo principal protegido
- arquivos de origem e destino
- dependencias que nao podem quebrar
- docs centrais:
  - `docs/reference/reading-guide.md`
  - `docs/architecture/octobox-architecture-model.md`
  - `docs/architecture/center-layer.md`
  - `docs/reference/personal-architecture-framework.md`
  - `docs/history/v1-retrospective.md`
  - `docs/history/v2-beta-retrospective.md`
- skills de apoio:
  - `.agents/skills/master_debugger/SKILL.md`
  - `.agents/skills/performance_architect/SKILL.md`

## Passos obrigatorios

1. Nomeie a dor estrutural real. Nao aceite justificativa vaga como "ficar mais bonito".
2. Mapeie contratos publicos, imports sensiveis, payloads, templates, comandos e testes que dependem do trecho.
3. Identifique o menor corte que melhora a estrutura sem ampliar demais a superficie de risco.
4. Preserve interfaces estaveis sempre que possivel.
5. Se precisar de estado transicional, declare o debito tecnico explicitamente.
6. Diga o que muda agora, o que fica para depois e por que.
7. Explique impacto em testes, logs, assets, permissoes e performance quando relevante.
8. Prefira refator por fatias: extrair, adaptar, validar, podar.
9. Atualize documentacao se o ownership ou o corredor oficial mudarem.
10. Mostre como saber que a refatoracao melhorou o sistema de verdade.

## Riscos

Voce deve evitar:

- refator cosmetico sem ganho operacional
- troca de nome sem reducao real de acoplamento
- mover codigo e manter dependencia circular
- misturar refator estrutural com redesign comportamental
- apagar rastros uteis sem criar novo corredor claro
- usar "depois a gente limpa" sem dono, prazo ou fronteira

## Saida esperada

Entregue a resposta final nesta ordem:

1. `Dor estrutural atual`
2. `Contrato que precisa ser preservado`
3. `Corte minimo de refatoracao`
4. `Sequencia de mudancas`
5. `Riscos e debitos tecnicos`
6. `Validacao`
7. `Proximo corte recomendado`

Sempre inclua:

- quais arquivos entram
- qual ownership fica melhor depois
- o que a refatoracao explicitamente nao deve tentar resolver agora

## Checklist de qualidade

So finalize se todas as respostas abaixo forem `sim`:

- a refatoracao resolve uma dor real e nomeada?
- o comportamento protegido ficou claro?
- o corte e pequeno o bastante para executar sem loteria?
- o debito tecnico transicional ficou explicito?
- existe forma objetiva de validar que o sistema melhorou?
- a proposta evita reescrever o que ainda nao precisa ser reescrito?
