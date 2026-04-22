<!--
ARQUIVO: checklist de refatoracao do OctoBOX.

POR QUE ELE EXISTE:
- reduz a chance de uma refatoracao piorar comportamento enquanto melhora a estetica interna.

O QUE ESTE ARQUIVO FAZ:
1. lista o minimo para refatorar com seguranca.
2. ajuda a medir se o corte realmente melhorou ownership e acoplamento.

PONTOS CRITICOS:
- refator sem este checklist vira cirurgia sem exame pre-operatorio.
-->

# Refactor Checklist

Marque cada item antes de encerrar uma refatoracao:

- a dor estrutural foi nomeada de forma concreta?
- o comportamento que precisa ser preservado esta claro?
- contratos publicos e imports sensiveis foram mapeados?
- o corte escolhido e pequeno o bastante para validar rapido?
- a refatoracao reduz acoplamento de verdade?
- ownership ficou mais claro depois da mudanca?
- qualquer estado transicional foi documentado como debito tecnico?
- a validacao cobre comportamento, nao so formato interno?
- a documentacao relevante foi atualizada?
- existe um proximo corte recomendado, e nao um "depois a gente ve" vazio?

Se voce nao consegue explicar qual dor foi removida, provavelmente voce so moveu moveis de lugar.
