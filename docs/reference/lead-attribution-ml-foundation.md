<!--
ARQUIVO: fundacao de atribuicao comercial, qualificacao e preparo para ML.

POR QUE ELE EXISTE:
- registra o contrato minimo para captacao, verificacao e leitura analitica de origem dos alunos.
- evita que o produto trate "origem" como um campo solto e perca valor futuro para analytics e modelos.

O QUE ESTE ARQUIVO FAZ:
1. separa origem operacional de origem comercial.
2. define a camada de qualificacao posterior via mensagem ou Google Forms.
3. registra quais metricas devem ficar separadas para ML.
-->

# Fundacao de atribuicao comercial e preparo para ML

## Tese

No OctoBox, uma entrada pode nascer por um caminho operacional e por um motivo comercial diferente.

Exemplo simples:

1. a recepcao digita o lead manualmente
2. mas a pessoa veio por Instagram

Se gravarmos isso como uma coisa so, o dado fica torto.

Por isso a fundacao correta separa:

1. `operational_source`: como o registro entrou no sistema
2. `acquisition_channel`: de onde a pessoa diz que veio
3. `qualification`: confirmacao posterior da origem por resposta adicional

## Onde isso mora hoje

Entrada do funil:

1. [../../onboarding/model_definitions.py](../../onboarding/model_definitions.py)
2. [../../onboarding/forms.py](../../onboarding/forms.py)
3. [../../onboarding/views.py](../../onboarding/views.py)
4. [../../onboarding/queries.py](../../onboarding/queries.py)
5. [../../onboarding/attribution.py](../../onboarding/attribution.py)

Observabilidade:

1. [../../monitoring/lead_attribution_metrics.py](../../monitoring/lead_attribution_metrics.py)

## Contrato salvo no intake

O `raw_payload` do `StudentIntake` passa a comportar esta estrutura:

```json
{
  "entry_kind": "lead",
  "attribution": {
    "schema_version": 1,
    "operational_source": "manual",
    "captured_via": "intake-center",
    "captured_at": "2026-04-09T10:30:00",
    "captured_by_actor_id": 9,
    "acquisition": {
      "declared_channel": "instagram",
      "declared_detail": "story da unidade",
      "is_declared": true
    },
    "qualification": {
      "status": "pending",
      "confirmed_channel": "",
      "confirmed_detail": "",
      "response_channel": "",
      "respondent_kind": "",
      "responded_at": null
    },
    "ml_features": {
      "has_declared_channel": true,
      "has_declared_detail": true,
      "needs_additional_qualification": false
    }
  }
}
```

## Por que isso prepara bem o ML

Pense assim:

1. `operational_source` e a porta por onde o papel entrou no predio
2. `acquisition_channel` e a rua de onde a pessoa veio
3. `qualification` e uma segunda confirmacao de testemunha

Para modelos futuros, isso ajuda a separar:

1. qualidade de dado
2. atribuicao comercial
3. performance de canal
4. taxa de conversao por origem
5. diferenca entre origem declarada e origem confirmada

## Metricas que devem ficar separadas

Nao misturar tudo em um so numero.

Separar pelo menos:

1. volume de entrada por `operational_source`
2. volume de captacao por `acquisition_channel`
3. total sem origem declarada
4. total com origem confirmada depois
5. taxa de conversao `lead -> aluno` por canal
6. taxa de matricula e pagamento por canal
7. tempo entre captura e conversao por canal

## Camada futura de Google Forms

Quando entrar o Google Forms ou mensagem automatica, a regra ideal e:

1. nunca sobrescrever silenciosamente a origem declarada inicial
2. preencher `qualification.confirmed_channel`
3. registrar `qualification.response_channel`
4. marcar diferenca entre declarado e confirmado para auditoria analitica

## Guardrails

1. nao colocar tudo no model `Student` cedo demais
2. nao transformar origem comercial em unico campo do dominio
3. nao prender a arquitetura a uma integracao especifica antes da hora
4. nao alimentar ML com dado sem separar declarado, confirmado e ausente
