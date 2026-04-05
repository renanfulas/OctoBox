<!--
ARQUIVO: SDD para aposentadoria segura de regras visuais legadas do front-end.

TIPO DE DOCUMENTO:
- solution design document operacional

AUTORIDADE:
- media para a frente de limpeza controlada de CSS legado

DOCUMENTO PAI:
- [theme-implementation-final.md](theme-implementation-final.md)

QUANDO USAR:
- quando a duvida for como remover regras antigas do front sem regressao visual
- quando precisarmos decidir o que pode morrer agora, o que precisa de ponte e o que ainda e estrutural

POR QUE ELE EXISTE:
- transforma a limpeza do legado visual em execucao disciplinada
- impede que a remocao de CSS antigo vire regressao silenciosa
- usa C.O.R.D.A. para alinhar contexto, risco, direcao e ondas de exclusao

O QUE ESTE ARQUIVO FAZ:
1. define o problema da permanencia de regras visuais antigas
2. registra o objetivo de aposentadoria segura dessas regras
3. organiza a remocao em ondas pequenas com rollback claro
4. fixa criterios para deletar, manter em transicao ou preservar temporariamente

PONTOS CRITICOS:
- este documento nao autoriza apagar regras sem prova de nao uso
- qualquer exclusao que afete shell, payload ou contrato de tela precisa de teste verde e smoke visual
- se uma regra antiga ainda estiver sustentando uma tela secundaria, ela deve ser rebaixada para ponte antes de morrer
-->

# SDD: Front Legacy Rule Retirement

## Resumo

Este SDD abre a frente oficial para aposentar regras visuais antigas do front-end sem reintroduzir regressao.

Em linguagem simples:

1. nao vamos sair arrancando fio da parede
2. primeiro vamos descobrir quais fios ainda ligam alguma lampada
3. depois desligamos circuito por circuito
4. so no fim removemos o cobre antigo da parede

Documentos que governam esta frente:

1. [../architecture/themeOctoBox.md](../architecture/themeOctoBox.md)
2. [theme-implementation-final.md](theme-implementation-final.md)
3. [../experience/css-guide.md](../experience/css-guide.md)
4. [../reference/design-system-contract.md](../reference/design-system-contract.md)
5. [../reference/front-end-ownership-map.md](../reference/front-end-ownership-map.md)

## C.O.R.D.A.

## C - Contexto

O OctoBox ja consolidou uma linguagem visual oficial baseada em **Luxo Futurista 2050**.

Ao mesmo tempo, a base ainda carrega residuos de fases anteriores:

1. familias visuais legadas que perderam soberania, mas ainda existem no codigo
2. seletores de transicao que podem competir com a hierarquia nova
3. helpers atmosfericos antigos que voltam a aparecer por heranca, import ou copia de template
4. pontes temporarias que podem ter sido validas numa onda anterior, mas hoje viraram risco de regressao

Exemplos de familias explicitamente rebaixadas pelo guia de CSS:

1. `glass-panel`
2. `finance-glass-panel`
3. `note-panel*`
4. `elite-glass-card`
5. `glass-panel-elite`
6. `ui-card`

Problema real:

1. enquanto essas regras continuarem vivas sem ownership claro, o front permanece vulneravel a override acidental
2. a cada ajuste de tema, o passado pode voltar pela cascata
3. isso aumenta o custo de manutencao e reduz confianca em polimento futuro

## O - Objetivo

Aposentar regras visuais legadas do front-end com seguranca, preservando:

1. a identidade atual do produto
2. a hierarquia local correta das telas
3. os contratos de design system e page payload
4. os testes e a estabilidade do shell

Definicao de sucesso:

1. regras antigas deixam de ter autoridade visual real
2. as telas principais continuam visualmente corretas apos a limpeza
3. os testes relevantes continuam verdes
4. fica claro o que foi deletado, o que ficou em ponte e por que

## R - Riscos

### Risco medio

Apagar CSS que ainda esta sendo herdado por uma tela secundaria.

Traducao infantil:
e como tirar a rodinha da bicicleta achando que a crianca ja sabe pedalar, quando uma curva ainda depende dela.

### Risco medio

Confundir regra antiga de tema com estrutura utilitaria ainda necessaria.

Exemplo:
uma classe pode parecer “feia e velha”, mas ainda pode segurar espaco, fluxo ou fallback de acessibilidade.

### Risco medio a alto

Apagar ponte legada sem antes mover a tela para a autoridade correta.

Isso vale especialmente quando:

1. a tela ainda depende de heranca acidental
2. o CSS local esta incompleto
3. o shell ou o host compartilhado ainda nao cobrem toda a composicao

### Risco alto

Fazer exclusao ampla sem auditoria de uso, diff visual e teste.

Isso criaria debito tecnico do tipo “limpo no arquivo, quebrado no navegador”.

## D - Direcao

Direcao oficial desta frente:

1. primeiro classificar
2. depois isolar
3. depois rebaixar
4. por ultimo excluir

Regra de ouro:

Uma regra antiga so pode morrer quando cair em uma destas categorias:

1. **Morta**: nao tem referencia ativa em template, JS ou CSS carregado
2. **Ponte controlada**: ainda existe, mas foi rebaixada e cercada para nao mandar no visual
3. **Migrada**: sua funcao ja foi absorvida por token, primitivo canonico ou CSS local legitimo

Regra de bloqueio:

Uma regra antiga nao pode ser apagada se ainda estiver:

1. sustentando uma superficie real
2. sendo usada por fallback de shell
3. cobrindo lacuna de responsividade ou acessibilidade
4. escondendo dependencia que ainda nao foi migrada

## A - Acoes

### Onda 1: Inventario e classificacao

Objetivo:

1. listar regras antigas e classificar por risco

Entregaveis:

1. inventario de seletores e familias legadas
2. mapa de uso por template, CSS e JS
3. status de cada item:
   `morta`, `ponte`, `estrutural temporaria`, `nao tocar ainda`

Critero de pronto:

1. nenhuma exclusao acontece antes desse inventario

### Onda 2: Rebaixamento seguro

Objetivo:

1. impedir que regras antigas continuem mandando na identidade visual

Acoes:

1. mover a responsabilidade visual para tokens, componentes canonicos ou CSS local correto
2. reduzir especificidade de familias antigas quando necessario
3. parar de importar regras antigas onde elas ja nao sao necessarias

Critero de pronto:

1. a tela continua igual ou melhor
2. a regra antiga deixa de ser fonte de autoridade

### Onda 3: Exclusao controlada

Objetivo:

1. apagar o que ja morreu de verdade

Acoes:

1. remover seletores mortos
2. remover imports mortos
3. remover helpers paralelos sem uso real
4. ajustar snapshots de `staticfiles` quando necessario

Critero de pronto:

1. diff visual limpo
2. testes verdes
3. nenhuma tela principal regressiva

### Onda 4: Blindagem contra retorno do legado

Objetivo:

1. impedir que a regra antiga volte em futuro patch

Acoes:

1. atualizar docs de ownership quando necessario
2. registrar familias proibidas para novas telas
3. adicionar testes de protecao em fluxos sensiveis quando houver risco recorrente

Critero de pronto:

1. o legado para de voltar como “atalho rapido”

## Taxonomia de decisao

Ao encontrar uma regra antiga, decidir nesta ordem:

### Tipo 1: Morta

Pode apagar ja quando:

1. nao aparece em template vivo
2. nao aparece em JS ativo
3. nao compoe CSS carregado por pagina real
4. nao participa de fallback de shell

### Tipo 2: Ponte

Nao apaga ainda quando:

1. ainda cobre uma tela secundaria
2. ainda protege markup legado em transicao
3. ainda evita regressao de responsividade

Acao:

1. rebaixar
2. documentar
3. matar depois

### Tipo 3: Estrutural temporaria

Ainda nao pode morrer quando:

1. a tela correta ainda nao absorveu sua responsabilidade
2. a remocao quebraria leitura, layout ou comportamento

Acao:

1. abrir migracao especifica
2. nao chamar isso de limpeza concluida

## Escopo inicial sugerido

Esta frente deve comecar por familias e residuos com maior chance de ghost override:

1. familias legadas explicitamente rebaixadas no [../experience/css-guide.md](../experience/css-guide.md)
2. utilitarios atmosfericos paralelos que disputem identidade visual
3. imports que tragam linguagem antiga para telas novas
4. helpers de transicao que ja perderam uso real

Fora de escopo inicial:

1. reestruturar templates inteiros
2. reabrir presenter ou payload sem necessidade
3. reescrever shell compartilhado so para “limpeza bonita”

## Checklist de exclusao segura

Antes de apagar qualquer regra:

1. localizar referencias no repositorio
2. verificar se o CSS e realmente carregado pela tela
3. confirmar ownership correto da responsabilidade substituta
4. validar dark e light nas telas afetadas
5. rodar testes relevantes
6. fazer smoke visual das superficies principais

## Criterios de validacao

Validacao minima por onda:

1. `py -3 manage.py check`
2. testes das areas afetadas
3. smoke visual das superficies principais tocadas

Validacao humana final:

1. a tela continua mais limpa, mais previsivel e sem “fantasma visual”
2. Maria nao sente que algo “voltou do nada”

## Trade-off assumido

Escolha arquitetural:

1. preferimos uma limpeza mais lenta e confiavel
2. em vez de uma exclusao agressiva e heroica

Motivo:

1. front legado costuma quebrar por cascata escondida
2. apagar devagar aqui economiza muito retrabalho depois

## Proxima entrega esperada

Depois deste SDD, a proxima entrega correta e:

1. auditoria do legado visual ainda vivo
2. classificacao por risco
3. primeira lista de regras que podem morrer hoje sem susto

Artefato oficial da Onda 1:

1. [front-legacy-rule-retirement-wave1-inventory.md](front-legacy-rule-retirement-wave1-inventory.md)
