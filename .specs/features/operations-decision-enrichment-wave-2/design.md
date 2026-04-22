## Design

- `entry_surface`
- `entry_href`
- `entry_href_label`
- `entry_reason`
- `secondary_surface`
- `secondary_href`

Primeira aplicacao:
- owner
- manager

## Contrato canonico

Cada papel deve receber um bloco `decision_entry_context` com:

- `entry_surface`
- `entry_href`
- `entry_href_label`
- `entry_label`
- `entry_reason`
- `entry_count`
- `entry_pill_class`
- `secondary_surface`
- `secondary_href`
- `secondary_href_label`
- `secondary_label`
- `secondary_reason`

## Regra de montagem

- `priority_context` continua existindo como tese curta do topo
- `decision_entry_context` vira o contrato oficial do primeiro movimento
- `operational_focus` continua existindo como trilha/lista de apoio

## Regra de template

- owner e manager nao devem mais depender de `|first` ou `forloop.first` para descobrir a entrada dominante
- o template deve ler `decision_entry_context` para:
  - spotlight principal
  - CTA principal
  - segunda leitura

## Ordem oficial de aplicacao

1. manager
2. owner

Motivo:
- manager sofre mais com ambiguidade entre triagem, vinculos e financeiro
- owner ja tem uma leitura mais curta e menos sujeita a troca de mesa
