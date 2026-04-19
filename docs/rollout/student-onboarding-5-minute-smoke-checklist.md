<!--
ARQUIVO: smoke script manual de 5 minutos para validar os 3 corredores do onboarding do aluno em homologacao.

TIPO DE DOCUMENTO:
- checklist operacional
- smoke test manual

AUTORIDADE:
- media

DOCUMENTOS PAIS:
- [homologation-deploy-checklist.md](homologation-deploy-checklist.md)
- [first-box-onboarding-runbook.md](first-box-onboarding-runbook.md)
- [../plans/intelligent-student-onboarding-plan.md](../plans/intelligent-student-onboarding-plan.md)

QUANDO USAR:
- logo apos deploy ou migrate em homologacao
- antes de abrir o onboarding para box piloto
- quando precisarmos validar rapidamente se os 3 corredores principais continuam vivos

POR QUE ELE EXISTE:
- reduz risco de confiar so em teste automatizado
- transforma a validacao do onboarding em um ritual curto, repetivel e objetivo
- ajuda o time a detectar quebra de rota, UX ou operacao em ambiente real

O QUE ESTE ARQUIVO FAZ:
1. valida o corredor de link em massa
2. valida o corredor de lead importado via WhatsApp
3. valida o corredor de aluno ja cadastrado
4. valida o editar perfil posterior
5. fecha com criterio claro de aprovado ou bloqueado

PONTOS CRITICOS:
- este smoke assume ambiente de homologacao com migrate aplicado
- se qualquer corredor principal falhar, nao liberar onboarding para o box
- se o teste abrir WhatsApp real, usar numeros de homologacao ou contas controladas
-->

# Smoke script manual de 5 minutos - onboarding do aluno

## Objetivo

Confirmar em ambiente real que os 3 corredores do onboarding estao funcionando:

1. `link em massa do box`
2. `lead importado via WhatsApp`
3. `aluno ja cadastrado`

E confirmar tambem que:

4. `editar perfil` continua coerente depois da entrada

## Definicao de aprovado

O smoke so passa quando:

1. os 3 corredores abrem a jornada correta
2. nenhum deles cai em erro 500
3. o painel operacional mostra o estado correto do link em massa
4. o perfil do aluno salva sem quebrar identidade

Se qualquer item falhar:

1. marcar como `BLOQUEADO`
2. nao abrir o onboarding para box real
3. registrar print, rota e mensagem de erro

## Preparacao rapida

Separar antes:

1. 1 usuario staff com acesso a `configuracoes-operacionais` e `entradas`
2. 1 aluno ja cadastrado com e-mail valido
3. 1 lead de homologacao com WhatsApp valido
4. 1 navegador limpo ou aba anonima para testar a experiencia do aluno

Tempo alvo:

1. 5 minutos

## Modos por papel

### Modo Recepcao

Foco:

1. validar a operacao do dia a dia
2. confirmar que convite, WhatsApp e aprovacao nao travam
3. detectar friccao de uso real

Responsabilidades:

1. abrir o painel de convites do aluno
2. gerar ou regenerar o `link em massa`
3. validar o `Convidar 1 clique` na Central de Entradas
4. conferir se o convite recente apareceu com a jornada correta
5. registrar se alguma etapa ficou confusa para operacao

Criterio de sucesso:

1. a recepcao consegue operar sem ajuda tecnica
2. o painel fala a verdade sobre o estado do link
3. o clique de WhatsApp funciona sem improviso

### Modo Owner

Foco:

1. validar a jornada do box como negocio
2. confirmar que a massa pode entrar com pouco atrito
3. verificar se o processo esta pronto para box piloto

Responsabilidades:

1. abrir o `link em massa` em aba anonima
2. validar a landing e o wizard completo
3. validar o fluxo do `aluno ja cadastrado`
4. decidir se a experiencia esta boa o bastante para liberar
5. marcar `APROVADO` ou `BLOQUEADO` na rodada

Criterio de sucesso:

1. a jornada em massa parece onboarding, nao tarefa tecnica
2. o aluno ja cadastrado entra sem wizard desnecessario
3. o owner sente confianca para liberar o box

### Modo QA

Foco:

1. validar consistencia ponta a ponta
2. confirmar que estado, redirect e persistencia estao corretos
3. registrar evidencias objetivas

Responsabilidades:

1. acompanhar os 3 corredores com olhar de falha silenciosa
2. validar se houve redirect correto apos OAuth
3. validar se o perfil salva sem inconsistencia
4. registrar print, horario e erro exato se algo falhar
5. decidir se a falha e bloqueadora ou observacao menor

Criterio de sucesso:

1. nenhum corredor quebra com erro 500
2. nenhuma jornada cai em tela errada
3. `Student`, `StudentIdentity` e convite ficam coerentes

## Roteiro de execucao

### Bloco 1 - Link em massa do box

Tempo alvo:

1. 90 segundos

Passos:

1. abrir `Configuracoes operacionais > Aluno > Convites`
2. localizar o card `Link em massa`
3. confirmar que o painel mostra um estado coerente:
   - `Disponivel`
   - `Pausado`
   - `Expirado`
   - `Limite atingido`
4. se necessario, clicar em `Criar link em massa` ou `Regenerar link em massa`
5. copiar o link
6. abrir o link em aba anonima
7. confirmar que a landing fala em cadastro do box e nao em convite individual
8. clicar em `Entrar com Google ou Apple`

Resultado esperado:

1. a rota abre sem erro
2. a copy fala de cadastro do box
3. depois do OAuth, o aluno cai no `wizard completo`
4. o wizard mostra campos de:
   - nome
   - WhatsApp
   - e-mail
   - data de nascimento
   - plano

Falhou se:

1. o link parecer disponivel no painel, mas abrir bloqueado sem explicar
2. a landing parecer convite individual
3. o OAuth voltar para lugar errado
4. o wizard nao abrir

### Bloco 2 - Lead importado via WhatsApp

Tempo alvo:

1. 90 segundos

Passos:

1. abrir `Central de Entradas`
2. localizar um lead de homologacao com telefone
3. clicar em `Convidar 1 clique`
4. confirmar que o sistema abre o handoff do WhatsApp
5. confirmar que a mensagem contem o link do convite
6. voltar para o painel de convites do aluno
7. localizar o convite recente
8. confirmar que a jornada aparece como `Lead importado`

Resultado esperado:

1. o clique nao quebra
2. o lead vira `linked_student` internamente
3. o convite nasce com a jornada correta
4. o WhatsApp abre com mensagem pronta

Falhou se:

1. o clique gerar erro
2. o WhatsApp nao abrir
3. o convite nascer como jornada errada
4. o lead continuar solto sem vinculo

### Bloco 3 - Aluno ja cadastrado

Tempo alvo:

1. 60 segundos

Passos:

1. no painel de convites do aluno, gerar convite para um aluno ja cadastrado
2. garantir que a jornada escolhida e `Aluno ja cadastrado`
3. abrir o link em aba anonima
4. passar pelo OAuth

Resultado esperado:

1. o aluno nao cai em wizard
2. o aluno entra direto no app ou na tela de aguardando aprovacao, conforme o tipo do convite
3. o painel operacional registra o convite sem erro

Falhou se:

1. o aluno cair em wizard sem precisar
2. o callback voltar para login sem motivo
3. o fluxo parar em erro 500

### Bloco 4 - Editar perfil

Tempo alvo:

1. 60 segundos

Passos:

1. entrar no app do aluno com uma conta valida
2. abrir `Configuracoes`
3. alterar ao menos 1 campo simples:
   - nome
   - WhatsApp
   - e-mail
4. salvar

Resultado esperado:

1. a tela salva sem erro
2. aparece feedback de sucesso
3. o e-mail continua coerente entre `Student` e `StudentIdentity`

Falhou se:

1. o formulario salva parcialmente
2. o e-mail desaparecer de um lado e ficar no outro
3. houver erro de validacao incoerente

## Checklist final

Marcar:

1. `Link em massa` -> `OK` ou `FALHOU`
2. `Lead importado via WhatsApp` -> `OK` ou `FALHOU`
3. `Aluno ja cadastrado` -> `OK` ou `FALHOU`
4. `Editar perfil` -> `OK` ou `FALHOU`

## Divisao de execucao recomendada

### Recepcao executa

1. Bloco 1 - painel e leitura do `link em massa`
2. Bloco 2 - `lead importado via WhatsApp`

### Owner executa

1. Bloco 1 - abertura do `link em massa` em aba anonima
2. Bloco 3 - `aluno ja cadastrado`
3. decisao final de liberar ou nao

### QA executa

1. observa os 3 blocos
2. executa Bloco 4 - `editar perfil`
3. registra evidencias e classifica falhas

## Matriz curta de responsabilidade

1. `Recepcao`:
   operar o painel, disparar convite, confirmar ergonomia operacional

2. `Owner`:
   validar percepcao do box e tomar decisao de liberacao

3. `QA`:
   validar consistencia tecnica visivel e registrar evidencias

## Regra de decisao

### Pode liberar

Quando:

1. os 4 itens acima estiverem `OK`

### Nao pode liberar

Quando:

1. qualquer corredor principal estiver `FALHOU`
2. houver erro 500
3. o painel operacional mentir sobre o estado do link

## Registro minimo da rodada

Salvar internamente:

1. data e hora da rodada
2. ambiente testado
3. quem executou
4. status de cada bloco
5. print ou observacao curta do que falhou

## Formula curta

Em linguagem simples:

1. a rede precisa abrir
2. o convite de precisao precisa disparar
3. o aluno pronto precisa entrar sem atrito
4. o perfil precisa continuar editavel

Se essas 4 portas abrirem, o onboarding esta respirando em homologacao.
