<!--
ARQUIVO: plano de execucao do acesso em camadas com elevacao temporaria.

TIPO DE DOCUMENTO:
- plano de frente ativa e rollout arquitetural

AUTORIDADE:
- alta para a execucao da frente de acesso profundo controlado

DOCUMENTO PAI:
- [../architecture/deep-access-control-architecture.md](../architecture/deep-access-control-architecture.md)

QUANDO USAR:
- quando a duvida for por onde comecar a implementacao
- quando for necessario quebrar a iniciativa em fases, entregas e criterios de pronto
- quando o time precisar validar se esqueceu algum guardrail importante

POR QUE ELE EXISTE:
- traduz a tese arquitetural em sequencia realista de execucao
- reduz o risco de tentar construir tudo de uma vez
- ajuda a tirar valor cedo sem improvisar seguranca

O QUE ESTE ARQUIVO FAZ:
1. organiza a execucao por fases
2. lista dependencias, riscos e criterios de pronto
3. aponta o que deve sair do admin e o que pode continuar la
4. define o backlog minimo da capacidade

PONTOS CRITICOS:
- nao implementar elevacao temporaria antes de mapear o que realmente e profundo
- nao mover tudo para paginas proprias sem classificar risco e recorrencia
- nao deixar o mecanismo depender so de memoria operacional do time
-->

# Plano de rollout do acesso profundo controlado

## Tese operacional

O objetivo desta frente nao e apenas endurecer o admin.

O objetivo e redesenhar a superficie de risco do produto.

Em termos praticos:

1. fluxo normal fica cada vez mais dentro do produto
2. fluxo sensivel recorrente ganha paginas proprias
3. fluxo profundo vira excecao supervisionada
4. credencial roubada perde profundidade automatica

## Resultado esperado ao fim da frente

1. owner e dev trabalham normalmente no dia a dia sem depender do admin puro
2. operacoes sensiveis recorrentes ficam em superficies dedicadas
3. admin profundo fica bloqueado por padrao
4. acesso extraordinario depende de grant temporario escopado
5. tentativas de acesso profundo geram evento observavel e resposta operacional clara

## O que nao podemos esquecer

Checklist de guardrails que precisam entrar no desenho desde o inicio:

1. MFA ou reautenticacao forte para owner e dev
2. grants com TTL automatico
3. revogacao imediata
4. auditoria completa de pedido, concessao, uso e expiracao
5. break-glass com trilha forte
6. escopo por capacidade, nao por admin inteiro
7. vinculo por sessao ou contexto quando viavel
8. alerta interno quando houver tentativa ou uso profundo
9. UX clara para bloqueio e pedido de liberacao
10. fallback operacional para incidente fora de horario

## Mapa inicial de classificacao

Antes de implementar, cada operacao atual ligada ao admin deve ser classificada em uma destas colunas:

1. comum
2. sensivel recorrente
3. profunda rara

### Comum

Deve sair do admin ou ja permanecer fora dele.

Criterio:

1. acontece com frequencia
2. faz parte do trabalho normal
3. nao justifica autorizacao humana extraordinaria

### Sensivel recorrente

Deve ganhar pagina propria e talvez reautenticacao.

Criterio:

1. afeta dinheiro, cadastro ou operacao importante
2. acontece de forma legitima mais de uma vez por mes
3. ainda precisa de UX de produto, nao de backoffice tecnico

### Profunda rara

Pode continuar fora do fluxo normal e atras de grant.

Criterio:

1. uso eventual
2. alto potencial de dano
3. manutencao, auditoria profunda ou administracao estrutural

## Fase 0: inventario e classificacao

Objetivo:

1. descobrir tudo que hoje depende do admin ou de acesso profundo

Entregas:

1. mapa de paginas admin usadas de verdade
2. lista de operacoes sensiveis recorrentes
3. lista de operacoes profundas raras
4. primeira proposta de escopos de grant

Artefatos sugeridos:

1. mapa por modelo admin
2. tabela de frequencia de uso
3. tabela de risco por operacao

Criterio de pronto:

1. nenhuma area relevante ficou sem classificacao
2. existe uma primeira separacao entre o que sai do admin e o que continua profundo

## Fase 1: safety rails imediatos

Objetivo:

1. reduzir risco antes de mover muita interface

Entregas:

1. desligar qualquer auto-honeypot agressivo para navegacao autenticada legitima sem score composto
2. explicitar logs e auditoria de acesso profundo
3. criar conceito de grant temporario, mesmo que ainda simples
4. garantir revogacao manual imediata

Criterio de pronto:

1. o sistema ja nao age como caixa-preta
2. qualquer elevacao ou bloqueio relevante deixa rastro revisavel

## Fase 2: Deep Access Gate

Objetivo:

1. bloquear por padrao a zona profunda

Entregas:

1. middleware ou policy gate para recursos profundos
2. tela padrao de bloqueio com orientacao de liberacao
3. registro de tentativa
4. regra por escopo em vez de if espalhado

Dependencias:

1. classificacao da fase 0
2. estrutura minima de grant da fase 1

Criterio de pronto:

1. entrar em area profunda sem grant deixa de ser possivel
2. a resposta ao usuario e clara
3. o time consegue ver o que foi tentado

## Fase 3: paginas proprias para operacoes sensiveis recorrentes

Objetivo:

1. tirar do admin o que e importante demais para continuar escondido e frequente demais para continuar profundo

Primeiros candidatos naturais:

1. mudanca de plano
2. ajustes financeiros recorrentes com criterio claro
3. leitura operacional de auditoria amigavel

Entregas:

1. UX dedicada
2. regras de permissao declaradas
3. reautenticacao onde fizer sentido
4. auditoria de mutacao

Criterio de pronto:

1. a necessidade de entrar no admin cai de verdade
2. o usuario nao precisa "fuçar" para operar o que e legitimo

## Fase 4: concessao temporaria madura

Objetivo:

1. profissionalizar o grant

Entregas:

1. escopo por capacidade
2. TTL configuravel
3. vinculo contextual por sessao ou IP quando viavel
4. emissao e revogacao por interface interna
5. expiracao automatica

Criterio de pronto:

1. concessao deixa de ser improviso
2. o sistema sabe exatamente quem liberou o que, para quem e ate quando

## Fase 5: validacao humana fora da banda

Objetivo:

1. impedir que senha roubada baste para entrar no cofre

Entregas:

1. protocolo operacional de validacao
2. script curto de confirmacao
3. campos de registro da validacao
4. regra de quando liberar por 24h e quando liberar por 48h

Criterio de pronto:

1. a equipe consegue validar rapido sem improviso
2. o processo deixa lastro auditavel

## Fase 6: sessao de alta confianca

Objetivo:

1. separar papel do usuario de confianca da sessao

Entregas:

1. reautenticacao para acoes sensiveis
2. MFA para owner e dev
3. nivel de confianca da sessao
4. degradacao de confianca antes de contencao extrema

Criterio de pronto:

1. ser owner deixa de ser suficiente por si so para profundidade maxima
2. a sessao precisa provar contexto atual

## Fase 7: honeypot e contencao excepcional

Objetivo:

1. reposicionar o honeypot como ultima barreira, nao como primeira

Entregas:

1. score composto para insistencia hostil
2. politica clara de quando isolar
3. separacao entre contencao de IP e contencao de usuario ou sessao
4. painel de liberacao e revisao

Criterio de pronto:

1. falso positivo cai
2. insistencia maliciosa continua contida

## Escopos iniciais recomendados

Primeira lista pragmatica:

1. `plan_management`
2. `finance_adjustments`
3. `finance_admin_read`
4. `audit_read`
5. `admin_model_write_restricted`
6. `full_admin_break_glass`

Regra:

1. comecar com poucos escopos bem entendidos
2. expandir depois de observar uso real

## Politica de expiracao recomendada

1. 24h como padrao
2. 48h apenas para trabalho operacional real que atravesse turnos ou janela de suporte
3. `full_admin_break_glass` com TTL menor e revisao obrigatoria

## Politica de concessao recomendada

1. toda concessao precisa de motivo
2. toda concessao precisa de concedente identificado
3. toda concessao precisa de expiracao
4. toda concessao sensivel precisa de trilha de validacao

## Riscos operacionais desta frente

### 1. gargalo humano

Se tudo depender de liberacao manual, a equipe vira porteiro de um predio com fila.

Mitigacao:

1. mover rapido o que for recorrente para pagina propria
2. reservar liberacao manual para o que for realmente profundo

### 2. escopo ruim

Se o escopo for largo demais, a seguranca vira teatro.

Mitigacao:

1. liberar por capacidade
2. evitar grant generico de admin inteiro

### 3. UX punitiva

Se a mensagem for ruim, o usuario legitimo sente que foi tratado como invasor.

Mitigacao:

1. linguagem clara e nao acusatoria
2. explicacao de que o acesso normal continua disponivel

### 4. dependencia do admin continua alta

Se as paginas proprias demorarem demais, o fluxo profundo continua sendo a unica porta.

Mitigacao:

1. priorizar operacoes recorrentes logo nas primeiras ondas

## Dependencias tecnicas e documentais

1. alinhar com `access`, `auditing`, `operations` e `catalog`
2. revisar o papel do admin dentro da arquitetura oficial
3. conectar esta frente aos docs de seguranca de baseline e edge

## Criterio de sucesso real

Esta frente so pode ser considerada bem-sucedida quando:

1. a equipe quase nao precisa usar o admin para rotina legitima
2. owner e dev conseguem operar o normal com fluidez
3. acesso profundo fica raro, escopado e rastreavel
4. senha roubada deixa de ser suficiente para profundidade total
5. o sistema protege sem parecer arbitrario

## Recomendacao de ordem pratica

1. mapear tudo que hoje depende do admin
2. classificar por comum, sensivel recorrente e profundo raro
3. implantar o gate de acesso profundo com trilha e mensagem clara
4. extrair as primeiras paginas proprias de operacoes recorrentes
5. profissionalizar grants e revogacao
6. adicionar validacao humana e confianca de sessao
7. so depois endurecer honeypot e contencao excepcional

## Tese final

O ganho aqui nao e apenas tecnico.

E estrategico.

Quando o OctoBox tira a rotina legitima de dentro do admin e transforma a profundidade em acesso temporario supervisionado, ele cria um abismo de maturidade em relacao ao financeiro comum de SaaS:

1. a experiencia diaria fica mais limpa
2. a area sensivel fica mais segura
3. a operacao extraordinaria passa a ter ritual, contexto e trilha
