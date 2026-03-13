<!--
ARQUIVO: plano de implementacao do modulo de recepcao.

POR QUE ELE EXISTE:
- registra a decisao de criar uma area especializada para recepcao como parte da obra visivel do produto.
- traduz uma lacuna percebida em um modulo real, com fronteira, custo e plano de execucao claros.

O QUE ESTE ARQUIVO FAZ:
1. define a tese do modulo de recepcao.
2. descreve o contrato funcional da area.
3. apresenta o plano tecnico de implementacao.
4. compara custo agora versus custo depois de maior organizacao do Django.

PONTOS CRITICOS:
- recepcao nao pode nascer como manager disfarcado.
- a area precisa cobrar sem virar o financeiro completo.
- a fronteira do papel precisa ser tecnica, visual e operacional ao mesmo tempo.
-->

# Modulo da Recepcao

## Tese central

A Recepcao nao entra neste projeto como remendo tardio.

Ela entra como prova publica de entendimento real do negocio.

Uma lacuna que poderia parecer negligencia passa a funcionar como triunfo de engenharia, produto e linguagem visual.

Em vez de esconder que a recepcao tinha ficado para depois, a decisao correta e transformar essa falta em evidencia de maturidade:

1. o sistema entendeu que recepcao nao e coach
2. o sistema entendeu que recepcao nao e manager completo
3. o sistema entendeu que recepcao precisa ver aluno, aula e cobranca curta no mesmo compasso
4. a obra continua visivel, mas agora aparece como crescimento bonito, especializado e digno de torcida

## Por que isso importa para a Front Display Wall

Quando o produto rodar para outras pessoas, a Recepcao pode virar uma das pecas mais fortes da fachada.

Ela comunica de imediato que o projeto nao foi desenhado por abstracao administrativa apenas.

Ela mostra intimidade com o chao do box.

Ela tambem ajuda a transformar a propria construcao em valor percebido:

1. quem usar o sistema vai ver que o predio esta crescendo com sensibilidade real
2. quem olhar a interface vai perceber uma frente viva, especializada e consciente
3. uma parte esquecida da obra se converte em parte memoravel da obra

## Definicao da area

Nome operacional:

Recepcao

Subtitulo sugerido:

Entrada, orientacao e cobranca curta do box

Promessa da area:

A Recepcao existe para acolher a chegada, localizar o aluno certo, enxergar a aula certa e resolver a cobranca necessaria sem afundar a pessoa em administrativo amplo, tecnico de treino ou leitura financeira gerencial.

## Contrato funcional da Recepcao

### O que a Recepcao ve

1. diretorio de alunos
2. criacao e edicao de aluno
3. grade de aulas em modo somente leitura
4. proximas aulas do turno ou do dia
5. fila curta de cobranca operacional
6. alunos em atraso
7. motivo resumido do atraso
8. atalhos de atendimento rapido

### O que a Recepcao faz

1. cadastrar aluno
2. editar aluno
3. buscar aluno por nome, telefone ou CPF
4. consultar a grade
5. localizar a proxima aula relevante
6. registrar pagamento
7. atualizar dados operacionais da cobranca quando fizer sentido
8. encaminhar casos para manager, coach ou owner quando o assunto sair da sua fronteira

### O que a Recepcao nao faz

1. nao entra no financeiro completo
2. nao ve comparativos, exportacoes ou leitura gerencial ampla de caixa
3. nao gerencia carteira de planos como centro comercial
4. nao opera presenca tecnica do coach
5. nao acessa auditoria
6. nao mexe em papeis, permissoes ou admin sensivel
7. nao assume toda a rotina do manager

## Recorte de cobranca da Recepcao

O ponto critico deste modulo e este:

A Recepcao precisa cobrar sem receber o modulo inteiro de financeiro.

Traducao pratica:

1. a recepcao nao deve entrar em /financeiro/
2. a recepcao precisa ver somente a fila operacional de cobranca
3. a recepcao precisa conseguir concluir o pagamento no contexto do atendimento

### O que a fila operacional de cobranca deve mostrar

1. aluno
2. vencimento
3. valor
4. status
5. referencia
6. observacoes curtas
7. motivo resumido do atraso
8. acao de registrar pagamento

### Como mostrar o motivo do atraso sem remodelar o dominio agora

Hoje o dominio financeiro ainda nao tem um campo formal de motivo do atraso.

Entao a recomendacao mais inteligente e derivar esse motivo por regra de leitura.

Motivos derivados sugeridos:

1. vencido e ainda pendente
2. cobranca sem matricula vinculada
3. referencia em branco
4. observacao operacional presente em notes
5. atraso acumulado por data vencida

Isso entrega uma explicacao util para a Recepcao sem abrir migration, sem inventar um mini-financeiro novo e sem travar a evolucao do modulo.

## Estrutura ideal da tela

### 1. Hero de atendimento

Mensagem central sugerida:

Veja quem chegou, qual aula importa agora e qual cobranca precisa ser resolvida no balcao.

Esse hero precisa comunicar:

1. rapidez
2. acolhimento
3. orientacao
4. cobranca curta sem opacidade

### 2. Comece por aqui

Tres leituras obrigatorias:

1. primeiro o aluno
2. depois a aula
3. por fim a cobranca

### 3. Pulso rapido

Cards sugeridos:

1. alunos localizados no turno
2. proximas aulas
3. atrasos visiveis
4. pagamentos resolvidos hoje

### 4. Atendimento rapido

Atalhos sugeridos:

1. buscar aluno
2. novo aluno
3. abrir alunos
4. abrir grade

### 5. Grade do dia em leitura

Essa area precisa:

1. mostrar proximas aulas
2. mostrar horario, coach e ocupacao
3. impedir acao administrativa sobre a grade

### 6. Cobranca operacional

Essa area precisa:

1. mostrar quem esta em atraso
2. mostrar por que aquilo esta em atraso em linguagem curta
3. permitir registrar pagamento sem navegar para o centro financeiro

## Plano de implementacao

### Fase 1: papel formal de Recepcao

Arquivos principais:

1. access/roles/
2. access/context_processors.py
3. boxcore/management/commands/bootstrap_roles.py
4. operations/base_views.py

Entregas:

1. novo role Recepcao
2. novo grupo no bootstrap
3. novo redirecionamento por papel
4. nova navegacao filtrada

### Fase 2: workspace da Recepcao

Arquivos principais:

1. operations/workspace_views.py
2. operations/queries.py
3. operations/urls.py
4. templates/operations/

Entregas:

1. nova workspace dedicada
2. snapshot proprio da Recepcao
3. copy e foco de atendimento
4. leitura guiada no mesmo idioma visual dos outros papeis

### Fase 3: permissao fina em alunos e grade

Arquivos principais:

1. catalog/views/student_views.py
2. catalog/views/class_grid_views.py
3. formularios e templates envolvidos em aluno e grade

Entregas:

1. acesso de Recepcao a alunos
2. acesso de Recepcao a cadastro e edicao de aluno
3. acesso de Recepcao a grade somente em leitura
4. bloqueio de edicao administrativa da grade

### Fase 4: cobranca operacional da Recepcao

Arquivos principais:

1. operations/queries.py
2. catalog/views/student_views.py
3. templates/operations/reception.html
4. eventualmente operations/action_views.py se algum endpoint novo for necessario

Entregas:

1. fila curta de cobranca para a Recepcao
2. leitura de atrasos sem abrir /financeiro/
3. registro de pagamento em contexto operacional
4. motivo derivado do atraso

### Fase 5: testes de fronteira e uso real

Arquivos principais:

1. boxcore/tests/test_access.py
2. boxcore/tests/test_operations.py
3. boxcore/tests/test_catalog.py

Entregas:

1. recepcao acessa apenas o que deve
2. recepcao nao entra onde nao deve
3. recepcao consegue cobrar sem ver o financeiro amplo

## Diagnostico de custo

### Custo agora

Estimativa pragmatica:

1. 1 a 2 dias de trabalho solido

Faixa realista por bloco:

1. papel, bootstrap, menu e redirect: baixo
2. workspace da Recepcao: baixo
3. permissao fina em alunos e grade: medio
4. cobranca operacional com motivo derivado: medio
5. testes: baixo a medio

Motivos para esse custo atual:

1. a arquitetura por papel ja existe
2. o idioma visual dos workspaces ja existe
3. o sistema de bootstrap e navegacao ja existe
4. a acao de pagamento ja existe
5. mas o recorte de cobranca operacional ainda nao existe como peca formal separada do financeiro

### Custo depois de mais organizacao do Django

Estimativa se alguns cortes estruturais vierem antes:

1. 0.5 a 1 dia para a maior parte do modulo

Isso seria possivel se estas tres coisas existissem com mais clareza:

1. contratos de papel ainda mais centralizados
2. cobranca operacional separada formalmente do financeiro amplo
3. politicas de permissao menos espalhadas por allowed_roles em views de catalogo e operacao

### O que reduziria custo no futuro

1. snapshots modulares por intencao de atendimento
2. uma superficie declarativa de permissoes por papel
3. um conceito formal de motivo do atraso no dominio financeiro
4. uma camada propria de cobranca operacional reutilizavel por workspace

## Decisao recomendada

Mesmo que o Django fique mais organizado depois, a Recepcao ja esta madura o suficiente para nascer agora.

Recomendacao:

1. implementar agora em escopo enxuto e correto
2. evitar transformar Recepcao em manager reduzido
3. evitar abrir o financeiro inteiro por conveniencia
4. usar motivo derivado do atraso como solucao inteligente desta fase

## Por que esta decisao muda o nivel da obra

Esta nao e apenas uma feature nova.

Ela faz tres coisas ao mesmo tempo:

1. corrige uma negligencia sem esconder que ela existiu
2. transforma essa negligencia em evidencia publica de inteligencia de produto
3. fortalece a Front Display Wall com uma tela especializada que faz gente de fora torcer pela construcao

Em linguagem direta:

1. a Recepcao pega uma falta da obra
2. transforma essa falta em gesto de refinamento
3. e devolve isso como triunfo visivel de engenharia de software, produto e arte