<!--
ARQUIVO: registro operacional pronto da rodada 1 de validacao mobile real.

TIPO DE DOCUMENTO:
- execucao guiada

AUTORIDADE:
- operacional

DOCUMENTO PAI:
- [mobile-real-validation-checklist.md](mobile-real-validation-checklist.md)

QUANDO USAR:
- quando a ideia for executar a primeira rodada curta de validacao mobile real sem precisar montar roteiro na hora

POR QUE ELE EXISTE:
- reduz atrito para iniciar a passada externa.
- concentra as tres primeiras superficies de maior valor em um unico registro.
- permite devolver resultado curto e rastreavel depois do teste.

O QUE ESTE ARQUIVO FAZ:
1. organiza shell, busca global e diretorio de alunos em ordem exata.
2. define o que abrir, o que observar e como registrar o resultado.
3. deixa um resumo final pronto para consolidacao posterior.

PONTOS CRITICOS:
- este documento nao executa o teste; ele deixa a execucao externa pronta.
- se houver bloqueador, registrar print ou video curto e anotar a rota exata.
-->

# Rodada 1 de validacao mobile real

## Estado desta rodada

1. preparada em 2026-03-14
2. pronta para execucao externa
3. escopo: shell global, login e busca global, diretorio de alunos

## Leitura virtual por contrato CSS

Esta secao nao substitui validacao fisica real.

Ela registra a melhor aproximacao tecnica disponivel quando a emulacao de viewport do browser integrado nao respeita a largura pedida.

Base adotada para a leitura:

1. iPhone 13 em retrato como referencia de largura estreita, perto de 390px
2. interpretacao feita a partir dos breakpoints e larguras minimas do CSS real da base

Conclusao curta desta rodada virtual:

1. shell global: provavel ok
2. login e busca global: provavel ok com vigilancia leve de densidade vertical
3. diretorio de alunos: toleravel, com dependencia explicita de scroll horizontal na tabela

Motivo da simulacao por contrato:

1. o browser integrado ignorou a troca de viewport e continuou reportando largura de desktop
2. por isso, a validacao abaixo e inferencia tecnica seria, nao emulacao fisica real

## Ambiente de teste

Preencher antes de comecar:

1. aparelho ou navegador: Iphone
2. largura aproximada: 71,5 mm
3. orientacao: retrato
4. usuario autenticado: sim

## Ordem fixa da rodada

1. dashboard para validar shell global
2. dashboard para validar busca global
3. alunos para validar filtros, tabela e abertura da ficha

---

## Etapa 1. Shell global autenticado

Rota:

1. /dashboard/

Abrir e verificar:

- [ ] sidebar abre e fecha sem cobrir controles de forma quebrada
- [ ] topbar continua legivel e clicavel
- [ ] chips de alerta continuam tocaveis
- [ ] compass e conteudo nao se sobrepoem de modo ruim
- [ ] a leitura geral da pagina continua clara em poucos segundos

Resultado:

1. status: provavel ok na simulacao por contrato CSS
2. evidencia curta: abaixo de 960px o shell vira 1 coluna, a sidebar vira overlay e o toggle mobile deixa de ficar oculto
3. observacao: a base de layout do shell esta bem preparada para 390px; o risco aqui parece mais de ritmo vertical do que de quebra estrutural
4. print ou video: nao se aplica nesta leitura virtual

---

## Etapa 2. Login e busca global

Rotas:

1. /login/
2. /dashboard/

Validacao do login:

- [ ] campos continuam legiveis e tocaveis
- [ ] submit permanece claro e acessivel
- [ ] nenhum bloco importante fica cortado

Validacao da busca global no dashboard:

- [ ] digitar resultado conhecido abre dropdown alinhado ao campo
- [ ] resultados nao escapam da viewport
- [ ] seta para baixo, Enter e Escape continuam previsiveis
- [ ] tocar em um resultado abre a ficha correta

Consulta sugerida:

1. Caio

Resultado:

1. status: provavel ok na simulacao por contrato CSS
2. evidencia curta: o login ja nasce com meta viewport; abaixo de 960px a busca vai para largura total e abaixo de 640px a topbar empilha melhor, com submit ocupando largura total quando necessario
3. observacao: a busca global parece estruturalmente preparada para largura estreita; a principal vigilancia continua sendo conforto de leitura, nao quebra do contrato visual
4. print ou video: nao se aplica nesta leitura virtual

---

## Etapa 3. Diretorio de alunos

Rota:

1. /alunos/

Validar:

- [ ] filtros continuam usaveis sem sobreposicao
- [ ] tabela continua legivel
- [ ] scroll horizontal, se aparecer, continua toleravel
- [ ] abrir uma ficha a partir da listagem continua simples

Watchpoint principal desta rodada:

1. a tabela do diretorio pode depender de scroll horizontal em largura pequena

Resultado:

1. status: toleravel na simulacao por contrato CSS
2. evidencia curta: o layout dos blocos cai para 1 coluna abaixo de 960px, mas a tabela principal continua com min-width de 760px dentro de um container com overflow-x auto
3. observacao: a pagina nao deve desmontar em 390px, mas a experiencia depende de scroll horizontal na tabela e esse continua sendo o watchpoint principal da rodada 1
4. print ou video: nao se aplica nesta leitura virtual

---

## Resumo final da rodada 1

1. shell global autenticado:
2. login e busca global:
3. diretorio de alunos:
4. bloqueadores encontrados:
5. superfícies toleraveis:
6. decisao: seguir, ajustar depois ou corrigir antes

Resumo virtual atual:

1. shell global autenticado: provavel ok
2. login e busca global: provavel ok
3. diretorio de alunos: toleravel com scroll horizontal na tabela
4. bloqueadores encontrados: nenhum bloqueador estrutural novo na leitura por contrato CSS
5. superficies toleraveis: diretorio de alunos
6. decisao: seguir com vigilancia e confirmar fisicamente fora do browser integrado

Complemento para as outras superficies:

1. [mobile-virtualization-by-css-contract-2026-03-14.md](mobile-virtualization-by-css-contract-2026-03-14.md)

## Devolutiva curta pronta para consolidacao

Copie e preencha este bloco ao terminar:

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