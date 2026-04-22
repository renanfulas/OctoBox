<!--
ARQUIVO: checklist de debug do OctoBOX.

POR QUE ELE EXISTE:
- evita encerrar investigacao cedo demais.

O QUE ESTE ARQUIVO FAZ:
1. lista as verificacoes minimas antes de aceitar um debug como resolvido.
2. ajuda a separar sintoma, causa raiz e prevencao.

PONTOS CRITICOS:
- se este checklist for pulado, a chance de remendo cosmetico sobe muito.
-->

# Debug Checklist

Marque cada item antes de fechar um debug:

- o sintoma foi definido em uma frase objetiva?
- o comportamento esperado e o comportamento atual foram comparados?
- existe reproducao ou trilha de evidencia suficiente?
- fato, hipotese e inferencia foram separados?
- a primeira camada realmente errada foi localizada?
- a causa raiz foi explicada de modo causal e nao superficial?
- a correcao proposta e a menor correcao segura?
- o risco de mexer nesse ponto foi nomeado?
- a validacao prova que o fluxo voltou a funcionar?
- existe prevencao de recorrencia: teste, guardrail, log ou checklist?

Se voce responder `nao` para dois itens ou mais, o debug ainda esta cru.
