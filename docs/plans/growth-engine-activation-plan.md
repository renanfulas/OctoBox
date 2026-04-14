<!--
ARQUIVO: plano de ativacao futura do OctoBox Growth Engine.

TIPO DE DOCUMENTO:
- plano de execucao arquitetural e de produto

AUTORIDADE:
- alta para a ordem de ativacao da frente Growth Engine

DOCUMENTO PAI:
- [../architecture/octobox-growth-engine.md](../architecture/octobox-growth-engine.md)

DOCUMENTOS IRMAOS:
- [scale-transition-20-100-open-multitenancy-plan.md](scale-transition-20-100-open-multitenancy-plan.md)
- [../architecture/operational-intelligence-ml-layer.md](../architecture/operational-intelligence-ml-layer.md)
- [../reference/lead-attribution-ml-foundation.md](../reference/lead-attribution-ml-foundation.md)

QUANDO USAR:
- quando a duvida for quando e como ativar a frente Growth Engine do OctoBox
- quando precisarmos decidir o que precisa existir antes de entrar em playbooks, cadencias, ML comercial e expansion intelligence
- quando precisarmos proteger a base atual para que a visao futura nao vire debito tecnico prematuro

POR QUE ELE EXISTE:
- evita que a tese de Growth Engine entre cedo demais por empolgacao.
- transforma a visao comercial de medio e longo prazo em ordem de ativacao objetiva.
- conecta a iniciativa de crescimento ao marco de 80-100 clientes e ao preparo para multitenancy.

O QUE ESTE ARQUIVO FAZ:
1. define as fases oficiais de ativacao do Growth Engine.
2. estabelece precondicoes, gates e entregas por fase.
3. separa validacao com early adopters de rollout amplo.
4. organiza a ponte futura entre growth comercial e expansion intelligence.

PONTOS CRITICOS:
- o Growth Engine nao pode competir com a consolidacao do core atual.
- ML comercial nao pode entrar antes de contratos de dados confiaveis.
- especialista humano de vendas deve calibrar metodo, nao virar gargalo estrutural.
-->

# Growth Engine Activation Plan

## Tese central

O OctoBox Growth Engine nao deve nascer como feature oportunista.

Ele deve nascer como `segunda grande alavanca do produto`, depois que a primeira alavanca estiver madura.

Em linguagem simples:

1. primeiro o OctoBox precisa provar que organiza a casa
2. depois ele pode virar motor de crescimento da casa

## Regra de ativacao

Esta frente so pode ser ativada quando estes quatro pontos estiverem suficientemente maduros:

1. base de aproximadamente `80-100 clientes`
2. preparo tecnico para `multitenancy`
3. observabilidade e contratos de dados confiaveis
4. grupo controlado de `early adopters` disposto a validar a frente

Se um desses pilares faltar, a iniciativa deve continuar apenas como preparacao arquitetural.

## O que significa "ativar" de verdade

Ativar o Growth Engine nao significa apenas criar telas novas.

Significa liberar um novo circuito de produto e operacao com:

1. oportunidade comercial
2. cadencia de follow-up
3. playbook versionado
4. ownership comercial
5. priorizacao inteligente
6. leitura de capacidade

Regra:

1. sem esse circuito completo, existe no maximo prototipo
2. nao existe Growth Engine real

## Fase 0 - Preparacao silenciosa

## Objetivo

Registrar e preparar a fundacao enquanto o OctoBox ainda esta focado no core.

## O que deve acontecer nesta fase

1. amadurecer lead intake e atribuicao
2. proteger origem operacional versus origem comercial
3. padronizar timeline de interacoes relevantes
4. endurecer observabilidade de conversao e jornada
5. preparar identidade futura de tenant sem ligar a camada completa

## O que ainda nao deve entrar

1. playbook complexo no produto
2. CRM comercial amplo
3. score de conversao em producao
4. expansion intelligence operacionalizado

## Sinal de sucesso

1. a arquitetura ja sabe onde essa frente vai morar
2. mas o produto ainda nao desviou energia demais para ela

## Fase 1 - Gate de prontidao

## Objetivo

Verificar se o OctoBox chegou no ponto certo para abrir essa trilha.

## Checklist obrigatorio

1. base ativa na faixa de `80-100 clientes`
2. plano de `multitenancy` em estado de execucao ou prontidao imediata
3. contratos de lead, conversao e historico com confianca suficiente
4. capacidade de segmentar dados por box, tenant e origem
5. time interno com espaco para tocar nova frente sem quebrar a atual

## Pergunta de gate

1. o OctoBox ja aguenta crescer em duas direcoes ao mesmo tempo: operacao core e growth comercial?

## Se a resposta for nao

1. a iniciativa volta para preparacao silenciosa

## Fase 2 - Laboratorio com early adopters

## Objetivo

Testar a tese do Growth Engine em ambiente controlado com poucos clientes.

## Perfil ideal dos early adopters

1. box com dono engajado
2. operacao aberta a disciplina comercial
3. volume minimo de leads para gerar aprendizado
4. disponibilidade para feedback rapido
5. tolerancia a iteracao de processo

## Entregas minimas

1. pipeline comercial basico
2. registro de atividades comerciais
3. fila de follow-up
4. motivos de ganho e perda
5. leitura de tempo ate primeiro contato

## O que medir nesta fase

1. tempo ate primeiro toque
2. numero de tentativas por lead
3. taxa de resposta
4. taxa de agendamento
5. taxa de fechamento
6. objecoes recorrentes

## Regra

1. esta fase serve para descobrir metodo
2. nao para vender escala cedo demais

## Fase 3 - Camada de metodo e treinamento

## Objetivo

Transformar aprendizagem de campo em metodo reproduzivel.

## Entregas

1. playbooks por perfil de lead
2. scripts de abertura e follow-up
3. mapa de objecoes
4. cadencias por tipo de oportunidade
5. training layer com especialista humano de vendas

## Papel do especialista humano

1. calibrar discurso
2. revisar playbooks
3. orientar metodologia inicial
4. transformar talento em processo

## Guardrail

1. o especialista nao pode ser dependencia permanente para cada box

## Sinal de sucesso

1. o metodo continua funcionando mesmo quando sai da mao do criador

## Fase 4 - Productization da operacao comercial

## Objetivo

Empacotar a camada comercial para que ela deixe de ser servico artesanal puro.

## Entregas

1. workspace de oportunidade
2. boards de cadencia
3. ownership comercial
4. comandos operacionais claros
5. dashboards de produtividade e conversao

## Regra de ouro

1. se a operacao so funciona com acompanhamento manual total, ela ainda nao virou produto

## Fase 5 - Priorizacao inteligente

## Objetivo

Usar heuristica e leitura analitica para melhorar alocacao de energia comercial.

## Entregas

1. ranking de oportunidade
2. janela recomendada de contato
3. alertas de follow-up vencido
4. reason codes basicos
5. priorizacao por sinais observaveis

## Importante

1. esta fase pode comecar com heuristica forte
2. sem depender ainda de modelo supervisionado completo

## Fase 6 - ML comercial supervisionado

## Objetivo

Transformar historico de conversao em foco comercial mais preciso.

## Precondicoes

1. dados consolidados e reconciliados
2. historico suficiente por canal, perfil e outcome
3. definicoes estaveis de ganho, perda, resposta e conversao
4. trilha de auditoria confiavel

## Entregas

1. `conversion_propensity_score`
2. `follow_up_priority_score`
3. `lead_quality_score`
4. `reason_codes`
5. leitura de nuances de comportamento e timing

## Guardrail

1. ML recomenda prioridade
2. o humano continua dono do fechamento

## Fase 7 - Expansion intelligence

## Objetivo

Conectar crescimento comercial a saturacao saudavel e expansao real.

## Entregas

1. radar de capacidade
2. previsao de saturacao
3. sugestao de novos horarios
4. tese de abertura de nova unidade
5. ponte futura com parceiros, credito e leitura de demanda local

## Regra

1. esta fase so entra depois de a maquina comercial provar que gera crescimento de verdade

## Gates oficiais de passagem

### Gate A - Core pronto para bifurcar

1. `80-100 clientes`
2. multitenancy no horizonte imediato
3. dados de lead e conversao confiaveis

### Gate B - Metodo validado

1. early adopters mostrando disciplina e resultados operacionais
2. playbooks gerando repetibilidade
3. objecoes e ganhos mapeados

### Gate C - Produto repetivel

1. time comercial usando fluxo sem acompanhamento manual total
2. boards, filas e ownership claros
3. indicadores consistentes por box

### Gate D - Inteligencia pronta

1. base historica suficiente
2. features reproduziveis
3. definicoes de sucesso e perda sem ambiguidade grave

## O que matar cedo se aparecer

1. automacao rasa por WhatsApp como pilar principal
2. promessa comercial fantasiosa
3. CRM inflado sem disciplina operacional
4. ML cenografico sem dado confiavel
5. expansion intelligence antes da hora

## Relacao com os concorrentes

O plano so vale a pena porque ele aponta para uma diferenciacao real.

O OctoBox Growth Engine nao deve competir como:

1. CRM generico
2. ferramenta de disparo
3. dashboard bonito sem operacao

Ele deve competir como:

1. sistema operacional do box
2. maquina de growth humano assistido
3. ponte entre captacao, conversao, lotacao e expansao

## Regra final

Se essa frente entrar cedo demais, ela enfraquece o OctoBox.

Se entrar na hora certa, ela pode se tornar a camada que transforma o OctoBox de software operacional em plataforma de crescimento.
