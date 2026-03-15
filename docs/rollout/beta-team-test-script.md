<!--
ARQUIVO: roteiro curto de teste para a equipe real do box durante o beta controlado.

TIPO DE DOCUMENTO:
- roteiro operacional de teste

AUTORIDADE:
- alta para rodada de feedback do beta interno

DOCUMENTOS IRMAOS:
- [beta-internal-release-gate.md](beta-internal-release-gate.md)
- [beta-role-test-agenda.md](beta-role-test-agenda.md)

QUANDO USAR:
- no primeiro beta controlado com equipe real do box
- quando a intencao for coletar feedback de uso, nao feedback de arquitetura

POR QUE ELE EXISTE:
- ajuda cada pessoa a testar so o que realmente pertence ao seu papel
- evita feedback vago do tipo "parece estranho" sem contexto de uso
- acelera a triagem entre bug real, confusao de fluxo e sugestao futura

O QUE ESTE ARQUIVO FAZ:
1. define um roteiro curto por papel
2. diz o que observar em cada fluxo
3. padroniza o jeito de registrar feedback

PONTOS CRITICOS:
- este roteiro nao e para explorar tudo; e para validar o uso real do box
- se houver bloqueio real, parar o teste e registrar na hora
-->

# Roteiro curto de teste para a equipe do box

## Objetivo

Fazer a equipe testar o OctoBox como usaria no dia a dia e devolver feedback util, concreto e facil de priorizar.

## Regra da rodada

Cada pessoa deve testar primeiro o proprio papel.

Se quiser explorar outra area, registrar isso como observacao lateral, nao como criterio principal.

Durante o teste, pedir sempre estas tres respostas:

1. consegui fazer o que precisava?
2. onde travei ou fiquei em duvida?
3. o que pareceu fora da ordem natural do trabalho?

## O que registrar em todo feedback

Cada anotacao precisa ter:

1. papel da pessoa
2. tela usada
3. o que ela tentou fazer
4. o que esperava acontecer
5. o que realmente aconteceu

Se possivel, anexar:

1. print
2. horario
3. nome do aluno, pagamento ou aula usada no teste

## Roteiro do Manager

Comecar por:

1. `/operacao/manager/`
2. `/alunos/`
3. `/financeiro/`
4. `/grade-aulas/`

Testar:

1. ler os cards e entender a ordem do que pede acao
2. abrir uma entrada ou aluno que exija triagem
3. abrir um caso financeiro que precise leitura curta
4. entrar na grade e editar uma aula real de teste

Observar:

1. se a ordem da tela faz sentido para o trabalho
2. se algum CTA leva para lugar errado
3. se faltou contexto para decidir a proxima acao
4. se a grade parece controlavel para quem faz gestao

## Roteiro da Recepcao

Comecar por:

1. `/operacao/recepcao/`
2. `/alunos/`
3. `/entradas/`

Testar:

1. localizar um aluno
2. abrir a fila de cobranca curta
3. confirmar ou ajustar um pagamento curto de teste
4. abrir a ficha do aluno a partir da recepcao
5. olhar a grade em leitura para orientar atendimento

Observar:

1. se a fila do balcao esta clara
2. se ficou facil entender qual aluno atender primeiro
3. se a ficha do aluno abre no ponto certo
4. se algo da recepcao parece financeiro demais ou gerencial demais

## Roteiro do Coach

Comecar por:

1. `/operacao/coach/`
2. `/grade-aulas/`

Testar:

1. abrir a turma do dia
2. registrar check-in ou check-out de teste
3. registrar uma ocorrencia tecnica curta
4. confirmar se a leitura da turma ajuda sem excesso de ruido

Observar:

1. se a tela ajuda o ritmo da aula
2. se o registro de presenca esta rapido o suficiente
3. se a ocorrencia tecnica ficou clara e natural
4. se apareceu informacao que nao pertence ao coach

## Roteiro do Owner

Comecar por:

1. `/dashboard/`
2. `/operacao/owner/`
3. `/financeiro/`
4. `/acessos/`

Testar:

1. olhar o dashboard e entender o que merece prioridade
2. confirmar se a leitura executiva bate com o financeiro
3. validar se os atrasos e o valor vencido parecem coerentes
4. revisar se os papeis fazem sentido para a operacao do box

Observar:

1. se os numeros principais contam a historia certa
2. se existe conflito entre dashboard, owner e financeiro
3. se alguma tela exige leitura longa demais para decidir

## O que conta como bug real

Registrar como bug real quando houver:

1. erro na tela
2. numero incoerente entre paginas
3. permissao errada
4. botao que nao faz o que promete
5. tela que impede concluir um trabalho simples

## O que conta como melhoria de uso

Registrar como melhoria quando houver:

1. texto confuso
2. ordem estranha da tela
3. informacao importante escondida
4. excesso de clique para concluir algo simples

## O que nao deve virar prioridade imediata

Segurar para depois se for:

1. ideia de modulo novo
2. preferencia pessoal sem impacto no fluxo
3. refatoracao tecnica sem reflexo no uso do box

## Fechamento da rodada

No fim, consolidar por papel:

1. o que funcionou bem
2. o que travou
3. o que confundiu
4. o que pode esperar

## Formula curta

Pedir para a equipe testar assim:

1. entra no seu papel
2. faz o que faria no box de verdade
3. anota onde travou
4. separa bug de sugestao