# C.O.R.D.A.

## Contexto

O workspace financeiro do aluno ja foi absorvido pelo tema canonico, mas o miolo de acoes de pagamento ainda carrega naming `elite-*` vivo em templates e JS.

Isso gera um risco pequeno visualmente, mas alto arquiteturalmente, porque mexe com:

1. cobranca
2. confirmacao de recebimento
3. parcelamento
4. escolha de metodo

## Objetivo

Canonicalizar a superficie viva de pagamento do aluno para que:

1. os botoes falem a lingua do sistema atual
2. o JS dependa de contratos semanticos e nao de apelidos historicos
3. o fluxo continue rapido e confiavel

## Riscos

1. quebrar o submit de pagamento por trocar classe sem mapa do JS
2. reduzir clareza do CTA em uma area de dinheiro
3. achatar demais a superficie e perder hierarquia de acao

## Direcao

1. mapear o runtime vivo
2. decidir naming canonico dos botoes e grupos
3. migrar o markup
4. migrar o JS
5. validar a leitura e a integridade do fluxo

## Acoes

1. fechar o mapa de ownership
2. definir estrategia canonica de CTA e estados
3. remover `elite-button-*` e `elite-stripe-btn*` do runtime vivo tocado
4. mover o JS para seletor canonico
5. validar o fluxo final
