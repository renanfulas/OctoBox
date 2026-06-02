<!--
ARQUIVO: checklist de smoke visual para telas do catalogo em `contract-only`.

POR QUE ELE EXISTE:
- reduz o risco de regressao visual depois da troca de `operations.css` completo pelo contrato minimo.
- transforma validacao visual em ritual curto, repetivel e objetivo.
- evita "acho que esta ok" e substitui por pontos claros de inspeccao.

O QUE ESTE ARQUIVO FAZ:
1. lista as 5 telas auditadas em `contract-only`.
2. diz o que abrir, o que clicar e o que validar em cada uma.
3. separa defeito visual de defeito contratual.

PONTOS CRITICOS:
- este checklist e visual e humano; ele nao substitui teste automatizado.
- se uma tela falhar aqui, primeiro confirme assets e payload antes de culpar o CSS.
- se aparecer dependencia real do manifesto operacional completo, documente no presenter em vez de remendar com CSS local.
-->

# Smoke visual das telas `contract-only`

Use este checklist quando precisarmos provar que a troca do "caminhao" operacional pela "maleta" minima nao deixou nenhuma parede torta.

Em linguagem simples:

1. a tela ainda precisa abrir bonita
2. os cards ainda precisam parecer cards
3. o hero ainda precisa parecer hero
4. a tabela ou grade ainda precisa respirar direito

## Regra geral de execucao

Para cada tela:

1. abrir a rota
2. validar desktop primeiro
3. validar uma largura intermediaria depois
4. clicar nos CTAs principais
5. procurar sinais de heranca perdida

Sinais tipicos de regressao depois dessa troca:

1. hero sem espacamento ou com botoes desalinhados
2. `operation-card-head` sem respiro, titulo esmagado ou copy fora de linha
3. tabela sem moldura, overflow feio ou colunas sem alinhamento
4. cards locais ficando "crus", como se tivessem perdido casca
5. CTA rail sem gap, sem wrap ou empilhando errado

## Breakpoints recomendados

Valide em pelo menos estes dois pontos:

1. desktop largo: `>= 1280px`
2. tablet ou laptop estreito: entre `900px` e `1024px`

Se houver comportamento estranho, confira tambem:

1. mobile largo: `~768px`

## 1. Students

Tela:

1. [../../templates/catalog/students.html](../../templates/catalog/students.html)

Presenter:

1. [../../catalog/presentation/student_directory_page.py](../../catalog/presentation/student_directory_page.py)

Objetivo visual:

1. provar que tabs, KPIs, quick panel e trilhos de prioridade continuam com identidade propria
2. provar que o uso pontual de `operation-card-head` continua elegante e sem heranca faltando

Passos:

1. abrir a tela de alunos
2. validar hero e trilho de acoes do topo
3. validar os blocos de prioridade e intake
4. abrir o quick financial summary
5. alternar tabs principais da tela

O que precisa parecer certo:

1. hero com botoes alinhados e gap consistente
2. cards de prioridade com cabecalho, titulo e copy bem distribuidos
3. quick financial summary sem borda quebrada nem texto colado
4. tabs com espacamento e estados visuais intactos

Pistas de falha provavel:

1. se o topo quebrar, suspeite de `operations/refinements/hero.css`
2. se cabecalhos locais perderem hierarquia, suspeite de `operations/components/card-shell.css`

## 2. Student form

Tela:

1. [../../templates/catalog/student-form.html](../../templates/catalog/student-form.html)

Presenter:

1. [../../catalog/presentation/student_form_page.py](../../catalog/presentation/student_form_page.py)

Objetivo visual:

1. provar que a casca da ficha continua organizada
2. provar que tabela e action rail continuam se comportando bem sem o manifesto completo

Passos:

1. abrir a ficha do aluno
2. validar o hero e o trilho de acoes
3. navegar pelas secoes ou passos principais
4. localizar qualquer tabela ou area com `operation-table-wrap`
5. testar largura intermediaria

O que precisa parecer certo:

1. hero com respiro correto e botoes sem empilhar cedo demais
2. secoes do formulario com ritmo visual constante
3. tabela ou bloco tabular com overflow controlado e alinhamento limpo
4. labels, copy auxiliar e divisoes sem cara de "CSS cru"

Pistas de falha provavel:

1. se o problema for tabela, suspeite de `operations/workspace/tables.css`
2. se o problema for topo, suspeite de `operations/refinements/hero.css`

## 3. Class grid

Tela:

1. [../../templates/catalog/class-grid.html](../../templates/catalog/class-grid.html)

Presenter:

1. [../../catalog/presentation/class_grid_page.py](../../catalog/presentation/class_grid_page.py)

Objetivo visual:

1. provar que a grade, metricas e contexto da turma continuam coesos
2. confirmar que o uso de card head nao puxava dependencia escondida de operations full

Passos:

1. abrir a tela da grade
2. validar hero e contexto superior
3. validar metricas da turma
4. rolar a grade principal
5. testar largura intermediaria

O que precisa parecer certo:

1. hero limpo, sem desalinhamento de CTA
2. metricas com ritmo uniforme e sem queda de tipografia
3. cards da grade com cabecalho e copy equilibrados
4. estrutura principal sem colapsos de espacamento

Pistas de falha provavel:

1. se metricas quebrarem, primeiro suspeite do CSS local de class-grid, nao do contrato minimo
2. se cabecalhos perderem acabamento, suspeite de `card-shell.css`

## 4. Finance center

Tela:

1. [../../templates/catalog/finance.html](../../templates/catalog/finance.html)

Presenter:

1. [../../catalog/presentation/finance_center_page.py](../../catalog/presentation/finance_center_page.py)

Objetivo visual:

1. provar que KPI, tabs, boards e carteira continuam com identidade local intacta
2. provar que os pontos compartilhados de card operacional continuam saudaveis

Passos:

1. abrir a central financeira
2. validar hero e acoes do topo
3. validar KPIs
4. alternar tabs ou filtros principais
5. inspecionar pelo menos um card financeiro com cabecalho operacional

O que precisa parecer certo:

1. hero alinhado
2. KPIs sem perda de borda, respiro ou hierarquia
3. tabs e boards sem regressao de espacamento
4. titulos e copys de cards sem aspecto "desossado"

Pistas de falha provavel:

1. se so KPI ou board local quebrar, suspeite do CSS de `finance`
2. se o cabecalho compartilhado quebrar, suspeite do contrato minimo

## 5. Finance plan form

Tela:

1. [../../templates/catalog/finance-plan-form.html](../../templates/catalog/finance-plan-form.html)

Presenter:

1. [../../catalog/presentation/membership_plan_page.py](../../catalog/presentation/membership_plan_page.py)

Objetivo visual:

1. provar que a tela mais "leve" continua elegante com a maleta minima
2. confirmar que summary rail e hero nao dependiam escondido de `operations.css` inteiro

Passos:

1. abrir a tela de plano financeiro
2. validar hero
3. validar summary rail
4. validar o formulario principal
5. testar largura intermediaria

O que precisa parecer certo:

1. hero com botoes e copy equilibrados
2. summary rail com `operation-card-head` bonito, sem texto colado
3. campos com respiracao consistente
4. layout sem vazios estranhos nem empilhamento precoce

Pistas de falha provavel:

1. se o summary rail perder acabamento, suspeite de `card-shell.css`
2. se o formulario local quebrar, suspeite do CSS do catalogo, nao do contrato operacional minimo

## Ordem de resposta se algo falhar

Quando alguma tela falhar, responda nesta ordem:

1. qual tela falhou
2. em qual breakpoint falhou
3. qual bloco visual falhou
4. se o cheiro e de `hero`, `card-head`, `table-wrap` ou CSS local
5. qual arquivo e o primeiro suspeito

Formato sugerido:

1. `students`
2. `1024px`
3. `quick financial summary com cabecalho esmagado`
4. `cheiro de card-shell`
5. `primeiro suspeito: static/css/design-system/operations/components/card-shell.css`

## Veredito esperado do smoke

Se as 5 telas passarem:

1. o catalogo pode tratar `catalog-operation-contract.css` como padrao com confianca muito maior
2. `operations.css` completo fica oficialmente reservado para excecoes reais

Se 1 ou 2 telas falharem:

1. nao reverta tudo
2. isole a falha
3. descubra se faltou contrato minimo ou se o problema era CSS local

Regra de ouro:

1. se a roda do carrinho entortar, nao destrua o carrinho inteiro
2. primeiro descubra se soltou o parafuso, a rodinha ou o eixo

Planilha irma:

1. [front-end-contract-only-visual-smoke-report-template.md](front-end-contract-only-visual-smoke-report-template.md)
