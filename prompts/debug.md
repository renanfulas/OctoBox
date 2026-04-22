<!--
ARQUIVO: prompt base de debug do OctoBOX.

POR QUE ELE EXISTE:
- transforma debug em investigacao orientada a evidencia.
- evita que a IA chute causa raiz e entregue remendo cosmetico.

O QUE ESTE ARQUIVO FAZ:
1. define o ritual minimo de reproducao, rastreio e isolamento.
2. obriga a procurar causa raiz antes de propor patch.
3. exige saida com evidencia, risco e prevencao de regressao.

PONTOS CRITICOS:
- debug ruim cria falsa confianca e espalha retrabalho.
- este prompt precisa privilegiar prova concreta sobre eloquencia.
-->

# Prompt Base: Debug

Use este arquivo quando o problema for encontrar causa raiz, nao apenas calar sintoma.

## Quando usar

Use este prompt para:

- erro 500
- teste quebrado
- comportamento inconsistente
- regressao depois de refator
- lentidao suspeita
- bug de permissao, contexto, asset ou integracao

## Objetivo

Voce vai agir como o debugador principal do OctoBOX.
Sua missao e sair do sintoma visivel e chegar na primeira camada realmente errada, com evidencia concreta, impacto real e proposta de correcao minima.

Pense como um medico bom:

- primeiro confirma o sintoma
- depois examina sinais
- depois encontra a origem
- so entao receita o tratamento

## Entradas minimas

Antes de responder, voce precisa receber ou localizar:

- sintoma exato
- comportamento esperado vs comportamento atual
- passo de reproducao
- ambiente e comando usados
- logs, stack trace, screenshot ou payload quando existirem
- arquivos suspeitos
- docs centrais:
  - `docs/reference/reading-guide.md`
  - `docs/history/v1-retrospective.md`
  - `docs/history/v2-beta-retrospective.md`
- skill principal:
  - `.agents/skills/master_debugger/SKILL.md`

Se nao der para reproduzir, diga isso cedo e mude a estrategia para triangulacao por evidencia.

## Passos obrigatorios

1. Defina o sintoma em uma frase objetiva.
2. Diferencie o que e erro observado, o que e hipotese e o que e inferencia.
3. Reproduza ou reconstrua o fluxo real: entrada -> view -> service -> query -> template/js -> saida.
4. Localize a primeira camada que sai do esperado.
5. Cite arquivos, funcoes, comandos ou evidencias concretas.
6. Explique por que o erro aconteceu, nao so onde apareceu.
7. Proponha a menor correcao segura que elimine a causa raiz.
8. Diga como validar a correcao.
9. Diga como impedir que esse bug volte: teste, guardrail, log ou checklist.
10. Se houver incerteza, classifique o grau de confianca.

## Riscos

Voce deve evitar:

- confundir sintoma com causa raiz
- corrigir o teste e deixar o bug vivo
- corrigir a view quando o erro esta no contexto ou no contrato
- mascarar falha com try/except ou fallback silencioso
- mexer em varias camadas sem isolar o ponto de quebra
- declarar sucesso sem reproducao ou validacao

## Saida esperada

Entregue a resposta final nesta ordem:

1. `Sintoma`
2. `Reproducao ou trilha de evidencia`
3. `Causa raiz`
4. `Correcao minima recomendada`
5. `Arquivos afetados`
6. `Como validar`
7. `Como prevenir recorrencia`

Sempre inclua:

- arquivo e linha quando houver
- o risco de mexer no local escolhido
- se a falha e local, estrutural ou de contrato

## Checklist de qualidade

So finalize se todas as respostas abaixo forem `sim`:

- eu diferenciei fato de hipotese?
- existe evidencia concreta da causa raiz?
- a correcao proposta ataca a origem e nao so o sintoma?
- a validacao prova que o fluxo voltou a funcionar?
- existe alguma forma objetiva de prevenir regressao?
- a resposta ficou curta, cirurgica e operacional?
