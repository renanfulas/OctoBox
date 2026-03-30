<!--
ARQUIVO: checklist operacional para validacao mobile real do front web do OctoBox.

TIPO DE DOCUMENTO:
- checklist de validacao externa

AUTORIDADE:
- media para fechamento de beta assistido

DOCUMENTO PAI:
- [../plans/front-beta-closure-board.md](../plans/front-beta-closure-board.md)

QUANDO USAR:
- quando a duvida for como executar e registrar a passada mobile real fora do browser integrado

POR QUE ELE EXISTE:
- organiza a validacao fisica que o ambiente assistido nao consegue fechar sozinho.
- evita rodadas soltas de teste sem criterio, evidência ou estado claro por superficie.
- transforma a passada externa em um fechamento complementar objetivo do beta.

O QUE ESTE ARQUIVO FAZ:
1. define o escopo minimo da rodada mobile real.
2. organiza o teste por superficie e por tipo de risco.
3. oferece um formato curto para registrar resultado, evidencia e bloqueio.

PONTOS CRITICOS:
- este checklist nao substitui o board beta; ele detalha a passada externa pendente.
- o foco aqui e validar uso real em largura fisica, nao descobrir requisito novo.
-->

# Checklist de validacao mobile real

## Regra de uso

Use este checklist em navegador externo real ou dispositivo fisico.

Para cada superficie, marque apenas um estado:

1. ok: sem problema relevante
2. toleravel: existe atrito, mas ainda cabe em beta assistido
3. bloqueador: impede uso com confianca e precisa voltar para implementacao

Formato curto de registro por item:

1. status
2. largura ou aparelho
3. evidencia curta
4. rota exata

## Rodada aberta agora

Data base:

1. 2026-03-14

Estado da rodada:

1. checklist organizado e pronto para execucao externa
2. passada fisica ainda nao executada neste ambiente
3. principais watchpoints atuais: toque real do shell, autocomplete da busca global e leitura humana das superficies densas

## Matriz minima de execucao

Execute pelo menos nestes contextos:

1. celular pequeno em retrato, perto de 375px
2. celular maior em retrato, perto de 390px a 430px
3. se possivel, um teste rapido em paisagem para shell e tabelas

Navegadores preferenciais:

1. Chrome Android ou Chrome desktop em janela real estreita
2. Safari iPhone, se houver aparelho disponivel

## Preparacao

Marque antes de testar:

- [ ] servidor local acessivel no navegador externo ou no aparelho
- [ ] usuario autenticado disponivel para shell, dashboard, alunos, financeiro, grade e recepcao
- [ ] pelo menos um aluno de teste acessivel na ficha leve
- [ ] possibilidade de registrar print ou video curto quando aparecer bloqueador

## Primeira rodada recomendada

Se a ideia for comecar pelo menor corte util, rode primeiro estas tres superficies:

1. shell global autenticado
2. login e busca global
3. diretorio de alunos

Registro pronto desta rodada:

1. [mobile-real-validation-round-1-2026-03-14.md](mobile-real-validation-round-1-2026-03-14.md)

Ordem pratica de execucao:

1. abrir /dashboard/ e validar shell
2. ainda em /dashboard/, validar busca global
3. abrir /alunos/ e validar filtros, tabela e abertura da ficha

Objetivo desta primeira rodada:

1. confirmar se a casca principal continua utilizavel em largura fisica real
2. confirmar se a busca global continua previsivel em toque e teclado
3. confirmar se o diretorio de alunos continua claro e tocavel no celular mesmo sem overflow horizontal

Modelo curto de retorno desta primeira rodada:

Shell global autenticado:

1. status:
2. largura ou aparelho:
3. evidencia:
4. observacao:

Login e busca global:

1. status:
2. largura ou aparelho:
3. evidencia:
4. observacao:

Diretorio de alunos:

1. status:
2. largura ou aparelho:
3. evidencia:
4. observacao:

Resumo da rodada 1:

1. ok:
2. toleravel:
3. bloqueador:

## 1. Shell global autenticado

Rota sugerida:

1. /dashboard/

Verificar:

- [ ] sidebar abre e fecha sem cobrir controles de forma quebrada
- [ ] topbar continua legivel e clicavel
- [ ] chips de alerta continuam tocaveis
- [ ] foco visual e hierarquia continuam claros
- [ ] nao existe sobreposicao ruim entre topbar, compass e conteudo

Registro:

1. status:
2. largura ou aparelho:
3. evidencia:
4. observacao:

## 2. Login e busca global

Rotas sugeridas:

1. /login/
2. /dashboard/ com busca global ativa

Verificar login:

- [ ] campos continuam legiveis e tocaveis
- [ ] submit permanece claro e acessivel
- [ ] nenhum bloco fica comprimido ou cortado

Verificar busca global:

- [ ] dropdown nasce alinhado ao campo
- [ ] resultados nao escapam da viewport
- [ ] seta para baixo, Enter e Escape seguem previsiveis
- [ ] tocar em resultado abre a ficha correta

Registro:

1. status:
2. largura ou aparelho:
3. evidencia:
4. observacao:

## 3. Recepcao

Rota sugerida:

1. /operacao/recepcao/

Verificar:

- [ ] intake, cobranca e grade continuam legiveis em sequencia
- [ ] botoes de confirmar pagamento continuam clicaveis
- [ ] cards e formularios nao quebram ritmo nem viram mosaico apertado
- [ ] navegar para a ficha do aluno e voltar preserva contexto

Registro:

1. status:
2. largura ou aparelho:
3. evidencia:
4. observacao:

## 4. Diretorio de alunos

Rota sugerida:

1. /alunos/

Verificar:

- [ ] filtros continuam usaveis sem sobreposicao
- [ ] tabela continua legivel
- [ ] scroll horizontal, se necessario, continua toleravel
- [ ] abrir uma ficha a partir da listagem continua simples

Watchpoint conhecido:

1. a tabela ainda depende de largura minima e pode exigir scroll horizontal em tela pequena

Registro:

1. status:
2. largura ou aparelho:
3. evidencia:
4. observacao:

## 5. Ficha leve do aluno

Rota sugerida:

1. /alunos/22/editar/

Verificar:

- [ ] passos essencial, perfil, saude, plano e cobranca continuam navegaveis no toque
- [ ] campos de data, valor e selecao seguem utilizaveis
- [ ] resumo financeiro nao quebra a hierarquia da tela
- [ ] acoes finais continuam claras sem empilhamento ruim

Registro:

1. status:
2. largura ou aparelho:
3. evidencia:
4. observacao:

## 6. Financeiro

Rota sugerida:

1. /financeiro/

Verificar:

- [ ] filtros continuam usaveis em largura pequena
- [ ] fila, regua e portfolio empilham sem colapsar leitura
- [ ] cards de acao continuam clicaveis
- [ ] nao existe texto ou valor monetario cortado

Registro:

1. status:
2. largura ou aparelho:
3. evidencia:
4. observacao:

## 7. Grade de aulas

Rota sugerida:

1. /grade-aulas/

Verificar:

- [ ] agenda do dia continua legivel
- [ ] visao semanal empilha sem virar bloco ilegivel
- [ ] preview mensal continua entendivel
- [ ] edicao rapida e planejador seguem acionaveis

Registro:

1. status:
2. largura ou aparelho:
3. evidencia:
4. observacao:

## Fechamento da rodada

Resumo final curto:

1. superficies ok:
2. superficies toleraveis:
3. bloqueadores:
4. prints ou videos coletados:
5. decisao: manter beta assistido, ajustar depois, ou corrigir antes de seguir

## Inicio desta rodada

Esta rodada ja comeca com estes fatos conhecidos:

1. a rodada browser-assisted consolidada de `2026-03-29` nao mostrou overflow horizontal em login, dashboard, recepcao e alunos
2. a confirmacao fisica continua pendente por limitacao do browser integrado
3. o primeiro ponto a observar no teste externo agora e o comportamento humano de toque, busca e leitura, nao mais vazamento lateral bruto
