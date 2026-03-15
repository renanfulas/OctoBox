<!--
ARQUIVO: gate operacional curto para decidir se o beta interno pode ser liberado ou se precisa voltar para ajuste.

TIPO DE DOCUMENTO:
- checklist operacional de release interno

AUTORIDADE:
- alta para fechamento do beta interno

DOCUMENTOS IRMAOS:
- [beta-role-test-agenda.md](beta-role-test-agenda.md)
- [homologation-deploy-checklist.md](homologation-deploy-checklist.md)
- [first-box-system-setup-checklist.md](first-box-system-setup-checklist.md)

QUANDO USAR:
- ao fechar um pacote do beta interno
- antes de chamar a base atual de pronta para rodada real de validacao
- depois de ajustes que tocam papel, shell, CTA, ancora, fila ou contadores

POR QUE ELE EXISTE:
- transforma a decisao de liberacao em uma sequencia curta e repetivel
- separa bloqueador real de detalhe cosmetico
- evita reabrir discussao estrutural no momento de fechar release

O QUE ESTE ARQUIVO FAZ:
1. define a ordem minima de verificacao antes da liberacao
2. classifica falhas em bloqueador, aceitavel e pos-beta
3. cria um criterio simples de segue ou nao segue

PONTOS CRITICOS:
- este gate nao substitui testes automatizados nem checklist de deploy
- se um item bloqueador falhar, o beta nao fecha
-->

# Gate de release do beta interno

## Objetivo

Decidir com rapidez se o pacote atual pode ser tratado como beta interno pronto ou se ainda precisa de correcao obrigatoria.

## Regra de uso

Executar nesta ordem:

1. suite focada do pacote alterado
2. smoke manual das telas centrais
3. conferencia de papeis e fronteiras
4. registro dos bloqueadores restantes

Se um item bloqueador falhar, parar e corrigir antes de seguir.

## Bloco 1. Precondicoes tecnicas

Tudo abaixo precisa estar verde:

1. servidor sobe sem erro
2. login funciona
3. nenhuma rota central responde 500
4. suite focada do pacote alterado passa
5. nao existe erro novo no arquivo alterado

Minimo esperado nesta fase:

1. `manage.py test` focado no circuito alterado
2. validacao visual das telas tocadas

## Bloco 2. Smoke funcional obrigatorio

Validar manualmente, nessa ordem:

1. `/dashboard/`
2. `/operacao/owner/`
3. `/operacao/manager/`
4. `/operacao/recepcao/`
5. `/operacao/coach/`
6. `/alunos/`
7. `/entradas/`
8. `/financeiro/`
9. `/grade-aulas/`
10. `/acessos/`

Em cada tela, confirmar:

1. titulo e contexto corretos
2. contadores principais coerentes com o resto do sistema
3. CTA principal aponta para ancora ou destino real
4. papel ativo nao ganhou acesso indevido

## Bloco 3. Fios que nao podem quebrar

Os seguintes circuitos precisam continuar coerentes:

1. Dashboard ↔ Financeiro ↔ Recepcao para atrasos e cobranca curta
2. Dashboard ↔ Alunos ↔ Entradas para intake e conversao
3. Coach ↔ Grade ↔ historico do aluno para rotina tecnica
4. Manager ↔ Alunos ↔ Financeiro ↔ Grade para leitura operacional
5. Acessos ↔ papeis reais do sistema para escopo e fronteira

## Bloco 4. Gate de papeis

Antes de fechar o beta, confirmar:

1. Owner enxerga amplitude sem perder fronteira
2. Manager consegue atuar no calendario da grade e no fluxo operacional que lhe pertence
3. Recepcao atua no balcao sem ganhar o financeiro inteiro
4. Coach continua dono de presenca e ocorrencia tecnica
5. DEV continua leitura tecnica e auditoria, sem virar operador informal

## Bloco 5. Classificacao de falhas

### Bloqueador

Nao pode fechar o beta se houver:

1. erro 500 ou falha de login
2. rota central quebrada
3. contador central incoerente apos reload
4. papel com permissao errada de negocio
5. CTA principal levando para destino inexistente ou fluxo morto

### Aceitavel para beta interno

Pode fechar com registro se houver:

1. copy secundaria imperfeita sem mudar entendimento do fluxo
2. detalhe visual pequeno sem quebra de uso
3. texto documental ainda precisando polimento

### Pos-beta

Deve ser empurrado para depois se for:

1. refatoracao estrutural sem impacto direto no uso atual
2. limpeza de compatibilidade historica sem risco operacional imediato
3. melhoria incremental que nao corrige bug real nem fronteira de acesso

## Bloco 6. Decisao final

O beta interno fecha quando:

1. suite focada passou
2. smoke das telas centrais passou
3. papeis centrais batem com o runtime real
4. nao restou bloqueador aberto

Se esses quatro pontos estiverem verdes, parar de expandir escopo e tratar o pacote como pronto.

## Formula curta

Para chamar de beta interno pronto, precisamos conseguir dizer quatro coisas sem hesitar:

1. sobe
2. navega
3. respeita fronteiras
4. nao esconde bloqueador