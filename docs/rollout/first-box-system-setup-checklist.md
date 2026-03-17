<!--
ARQUIVO: checklist de configuracao interna do primeiro box no sistema.

TIPO DE DOCUMENTO:
- checklist operacional de setup interno

AUTORIDADE:
- alta para o dia da implantacao do primeiro box

DOCUMENTO PAI:
- [first-box-onboarding-runbook.md](first-box-onboarding-runbook.md)

QUANDO USAR:
- quando a duvida for qual ordem seguir dentro do OctoBox para deixar o primeiro box apto a operar no dia 1

POR QUE ELE EXISTE:
- transforma o onboarding do primeiro box em passos curtos e verificaveis dentro da propria aplicacao.
- evita esquecer configuracoes essenciais de usuario, plano, base inicial e validacao por rota.

O QUE ESTE ARQUIVO FAZ:
1. define a ordem de setup do box no sistema.
2. registra as rotas e validacoes centrais do dia 1.
3. cria uma sequencia repetivel para o primeiro piloto.

PONTOS CRITICOS:
- este checklist usa o escopo curto do piloto e nao deve ser inflado no dia da implantacao.
- se algum passo critico falhar, o box nao deve ser considerado pronto para uso real naquele dia.
-->

# Checklist de setup interno do primeiro box

## Objetivo

Configurar o primeiro box piloto dentro do OctoBox em uma ordem que reduza risco e permita validar uso real ainda no mesmo dia.

## Regra de uso

Seguir esta ordem sem pular para refinamentos paralelos.

Se um passo critico falhar, corrigir antes de seguir para o proximo.

## Etapa 1. Validar acesso base

Confirmar:

1. home redireciona corretamente em [../../access/urls.py](../../access/urls.py)
2. login abre em [../../access/urls.py](../../access/urls.py)
3. dashboard abre em [../../dashboard/urls.py](../../dashboard/urls.py)
4. operacao por papel responde em [../../operations/urls.py](../../operations/urls.py)

URLs base do dia 1:

1. `/login/`
2. `/dashboard/`
3. `/operacao/`
4. `/alunos/`
5. `/grade-aulas/`

## Etapa 2. Criar usuarios do box

Criar no minimo:

1. um Owner
2. um Manager, se existir operacao de gestao no box
3. um Recepcao, se houver operador real de balcao ou se o piloto ja for usar a area oficial
4. um Coach

Se o box ainda nao tiver operador dedicado de balcao:

1. manter a Recepcao como fluxo oficial do sistema
2. registrar explicitamente a contingencia se o piloto precisar de cobertura por Owner ou Manager
3. nao inventar usuario de recepcao ficticio apenas para completar papel sem uso real
4. criar usuario Recepcao assim que houver operador real de balcao

Checklist:

1. usuario criado
2. grupo correto vinculado
3. login testado
4. redirecionamento por papel testado

## Etapa 3. Cadastrar planos principais

Como o fluxo leve atual favorece edicao e nao criacao rapida de plano, o cadastro inicial pode usar o admin com disciplina.

Campos minimos por plano:

1. nome
2. valor
3. billing_cycle
4. sessions_per_week
5. active

Checklist:

1. plano Iniciante criado
2. plano Scaled criado
3. plano RX criado
4. billing cycle coerente com a ficha do box

## Etapa 4. Carregar base inicial de alunos

Se a entrada for manual:

1. começar pelos alunos ativos mais importantes
2. garantir nome completo e WhatsApp corretos

Se a entrada for por lote:

1. usar [first-box-student-import-template.csv](first-box-student-import-template.csv)
2. usar o comando documentado em [first-box-onboarding-runbook.md](first-box-onboarding-runbook.md)

Checklist:

1. aluno aparece em `/alunos/`
2. busca por nome funciona
3. busca por telefone funciona
4. edicao do aluno funciona

## Etapa 5. Montar grade essencial

Entrar apenas com as aulas que precisam existir no primeiro dia.

Checklist:

1. ao menos 3 aulas cadastradas
2. dia e horario corretos
3. coach coerente
4. leitura em `/grade-aulas/` validada

## Etapa 6. Testar Recepcao do piloto

Validar a capacidade da area oficial de Recepcao:

1. abrir `/operacao/recepcao/` com o usuario oficial de Recepcao ou, se necessario, com a contingencia registrada
2. localizar aluno
3. enxergar grade em leitura
4. validar cobranca curta quando houver dado suficiente

Se o box nao tiver pessoa dedicada na recepcao ainda:

1. tratar a Recepcao como fluxo funcional do sistema
2. registrar que a cobertura operacional esta em contingencia por Owner ou Manager
3. nao tratar essa cobertura como desenho final do piloto

## Etapa 7. Validar cobranca curta

Testar pelo menos um caso controlado:

1. pagamento pendente localizado
2. ajuste curto salvo ou pagamento marcado
3. reflexo visivel na ficha do aluno

## Etapa 8. Smoke test por papel

### Owner

1. login
2. dashboard
3. alunos
4. grade

### Manager

1. login
2. operacao
3. alunos
4. Recepcao, quando o piloto estiver cobrindo esse fluxo com Manager

### Recepcao

1. login, quando houver usuario dedicado
2. operacao
3. alunos
4. cobranca curta

### Coach

1. login
2. operacao
3. grade ou rotina ligada ao papel

## Etapa 9. Aceite do dia 1

So considerar o box apto quando:

1. login estiver funcionando
2. ao menos um usuario por papel principal entrar sem erro
3. planos minimos existirem
4. base inicial de alunos estiver minimamente utilizavel
5. grade essencial estiver visivel
6. o responsavel do box confirmar que consegue operar o pacote curto do piloto

## Formula curta

No dia 1, o box nao precisa sentir o sistema inteiro.

Ele precisa sentir que o essencial funciona com previsibilidade.