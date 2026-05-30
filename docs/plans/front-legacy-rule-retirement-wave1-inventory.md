<!--
ARQUIVO: inventario da Onda 1 para aposentadoria de regras visuais legadas.

TIPO DE DOCUMENTO:
- inventario operacional de front-end

AUTORIDADE:
- media para a execucao da Onda 1 do SDD de aposentadoria do legado visual

DOCUMENTO PAI:
- [front-legacy-rule-retirement-sdd.md](front-legacy-rule-retirement-sdd.md)

QUANDO USAR:
- quando a duvida for quais regras antigas ainda vivem no front
- quando precisarmos decidir o que pode morrer, o que precisa de ponte e o que nao deve ser tocado ainda

POR QUE ELE EXISTE:
- transforma a Onda 1 em evidência documentada
- separa legado morto, legado em ponte e legado ainda estrutural
- evita exclusao cega baseada apenas em intuicao visual

O QUE ESTE ARQUIVO FAZ:
1. registra o raio de alcance atual do legado visual
2. lista familias auditadas e seu status
3. aponta candidatos seguros para a Onda 2
4. fixa o que nao deve ser apagado nesta rodada

PONTOS CRITICOS:
- este inventario nao substitui smoke visual e teste antes de exclusao
- algumas familias parecem antigas, mas ainda sustentam telas reais
- qualquer item marcado como ponte ou estrutural temporaria deve migrar antes de morrer
-->

# Inventario Onda 1: Legacy Visual Rules

## Resumo

A Onda 1 confirmou que o legado visual do OctoBox hoje se divide em tres grupos:

1. familias antigas ainda vivas em telas reais do catalogo
2. residuos de prototipo presos em [utilities.css](../../static/css/catalog/shared/utilities.css)
3. nomes historicos que ja nao deixaram pegada ativa na base

Em linguagem simples:

1. existe um encanamento velho ainda levando agua para algumas salas
2. existe tambem torneira que ja nao alimenta nada
3. o erro seria quebrar a parede toda antes de saber qual cano ainda esta molhado

## Raio de alcance atual

O principal ponto de distribuicao do legado visual auditado e [shared.css](../../static/css/catalog/shared.css), que importa [utilities.css](../../static/css/catalog/shared/utilities.css).

Hoje essa base compartilhada ainda e carregada por estas superficies:

1. [class_grid_page.py](../../catalog/presentation/class_grid_page.py)
2. [finance_center_page.py](../../catalog/presentation/finance_center_page.py)
3. [membership_plan_page.py](../../catalog/presentation/membership_plan_page.py)
4. [student_directory_page.py](../../catalog/presentation/student_directory_page.py)
5. [student_form_page.py](../../catalog/presentation/student_form_page.py)

Traducao pratica:

1. qualquer legado preso em `utilities.css` ainda pode respingar em grade, financeiro, planos, diretorio e ficha do aluno
2. por isso a Onda 2 deve priorizar remocao por familia, nunca por arquivo inteiro

## Classificacao oficial

## 1. Estrutural temporaria

Estas familias ainda apareciam em telas vivas na auditoria inicial, mas nesta frente ja foram migradas para classes locais.

| Familia | Evidencia atual | Onde aparece | Status | Direcao |
|---|---|---|---|---|
| `glass-panel` | uso antigo absorvido por classes locais em [system-pages.css](../../static/css/system-pages.css), [workspace.css](../../static/css/catalog/class-grid/workspace.css), [context.css](../../static/css/catalog/class-grid/context.css), [intakes.css](../../static/css/onboarding/intakes.css) e [student-financial.css](../../static/css/catalog/shared/student-financial.css) | class-grid, intake, ficha financeira do aluno, [403.html](../../templates/403.html) | migrada | alias removido de [utilities.css](../../static/css/catalog/shared/utilities.css) |
| `finance-glass-panel` | uso antigo absorvido por classes locais do financeiro em [finance/_signature.css](../../static/css/catalog/finance/_signature.css) | boards e support cards do financeiro | migrada | alias removido de [utilities.css](../../static/css/catalog/shared/utilities.css) |

Leitura:

1. esses dois canos eram principais na auditoria inicial
2. agora a agua ja passa por tubulacao local e nomeada

## 2. Ponte controlada

Estas familias ainda tem uso real, mas ja podem entrar na fila de aposentadoria controlada.

| Familia | Evidencia atual | Onde aparece | Status | Direcao |
|---|---|---|---|---|
| `info-card` | uso antigo migrado para [workspace.css](../../static/css/catalog/class-grid/workspace.css) com `class-planner-intro-card` | class-grid planner | migrada | alias removido de [utilities.css](../../static/css/catalog/shared/utilities.css) |
| `primary-glow` | uso antigo migrado para [intakes.css](../../static/css/onboarding/intakes.css) com `intake-metric-card` | intake metrics | migrada | alias removido de [utilities.css](../../static/css/catalog/shared/utilities.css) |
| `orange-glow` | uso antigo migrado para [finance/_signature.css](../../static/css/catalog/finance/_signature.css) com `finance-metric-card--copper` | metricas do financeiro | migrada | alias removido de [utilities.css](../../static/css/catalog/shared/utilities.css) |
| `green-glow` | uso antigo migrado para [finance/_signature.css](../../static/css/catalog/finance/_signature.css) com `finance-metric-card--teal` | metricas do financeiro | migrada | alias removido de [utilities.css](../../static/css/catalog/shared/utilities.css) |
| `blue-glow` | uso antigo migrado para [finance/_signature.css](../../static/css/catalog/finance/_signature.css) com `finance-metric-card--cyan` | metricas do financeiro | migrada | alias removido de [utilities.css](../../static/css/catalog/shared/utilities.css) |
| `text-premium` | uso antigo migrado para [student_form_stepper.css](../../static/css/catalog/student_form_stepper.css) com `student-plan-expected-price` | ficha do aluno | migrada | alias removido de [utilities.css](../../static/css/catalog/shared/utilities.css) |

Leitura:

1. essas regras ainda ligam alguma lampada
2. mas nao deveriam continuar morando como “tema paralelo compartilhado”

## 3. Nao tocar ainda

Estas familias parecem antigas no nome, mas hoje participam do host oficial ou de uma camada que ja foi canonizada.

| Familia | Evidencia atual | Onde aparece | Status | Direcao |
|---|---|---|---|---|
| `note-panel*` | definida em [states.css](../../static/css/design-system/components/states.css) e usada em varias telas reais | ficha do aluno, plano financeiro, recepcao, pagina expressa | nao tocar ainda | tratar como alias canonizado do host de estados; so migrar se houver plano explicito para `notice-panel` ou `state-notice` |
| `legacy-copy*` | referencias vivas em [scene.css](../../static/css/catalog/shared/scene.css), [student-financial.css](../../static/css/catalog/shared/student-financial.css), [student-page-shell.css](../../static/css/catalog/shared/student-page-shell.css), [utilities.css](../../static/css/catalog/shared/utilities.css) e camadas de operations | shared catalog, student page shell, operations | divida de nomenclatura controlada | manter por agora; migrar so com plano proprio de equivalencia para `--theme-text-secondary`, `--theme-text-muted`, `--muted` e `--muted-strong` |

Leitura:

1. o nome e historico
2. mas a casa atual da familia ja e o design system
3. apagar agora seria matar a campainha achando que ela ainda e fio antigo
4. `legacy-copy*` segue a mesma logica: o nome envelheceu, mas a funcao continua viva e espalhada

## 4. Morta ou sem pegada ativa

Nao encontrei uso real atual em templates, JS ou CSS carregado para estas familias:

| Familia | Evidencia atual | Status | Direcao |
|---|---|---|---|
| `elite-glass-card` | nenhum match ativo na auditoria | sem pegada ativa | pode ser tratada como ja aposentada; se existir definicao escondida, remover na Onda 2 |
| `glass-panel-elite` | nenhum match ativo na auditoria | sem pegada ativa | pode ser tratada como ja aposentada; se existir definicao escondida, remover na Onda 2 |
| `ui-card` | nenhum match ativo na auditoria | sem pegada ativa | pode ser tratada como ja aposentada; se existir definicao escondida, remover na Onda 2 |
| `glass-card` | so definicao em [utilities.css](../../static/css/catalog/shared/utilities.css), sem consumidor vivo | morta | candidata forte para exclusao imediata na Onda 2 |
| `btn-premium` | so definicao em [utilities.css](../../static/css/catalog/shared/utilities.css), sem consumidor vivo | morta | candidata forte para exclusao imediata na Onda 2 |
| `secondary-glow` | so definicao em [utilities.css](../../static/css/catalog/shared/utilities.css), sem consumidor vivo | morta | candidata forte para exclusao imediata na Onda 2 |

## Hotspot principal

O principal hotspot de legado visual auditado e [utilities.css](../../static/css/catalog/shared/utilities.css).

Motivos:

1. mistura utilitarios validos com familias de tema historicas
2. concentra classes mortas, pontes e estruturas temporarias no mesmo arquivo
3. entra em varias superficies porque [shared.css](../../static/css/catalog/shared.css) ainda e carregado amplamente

Traducao infantil:

1. esse arquivo e uma gaveta onde tem ferramenta boa, parafuso velho e cabo sem uso juntos
2. a Onda 2 precisa separar essa gaveta por tipo, nao despejar tudo no lixo de uma vez

## Candidatos imediatos para Onda 2

Itens com melhor relacao risco baixo x retorno alto:

1. remover `glass-card`
2. remover `btn-premium`
3. remover `secondary-glow`
4. confirmar que `elite-glass-card`, `glass-panel-elite` e `ui-card` nao existem em arquivo residual fora da busca principal e apagar qualquer sobra encontrada

Status apos execucao da Onda 2:

1. `glass-card` removida de [utilities.css](../../static/css/catalog/shared/utilities.css)
2. `btn-premium` removida de [utilities.css](../../static/css/catalog/shared/utilities.css)
3. `secondary-glow` removida de [utilities.css](../../static/css/catalog/shared/utilities.css)
4. `elite-glass-card`, `glass-panel-elite` e `ui-card` continuam sem pegada ativa encontrada

## Itens que pedem migracao antes da exclusao

1. nenhuma familia estrutural legada de glass permanece ativa
2. nenhuma outra glow rule de catalogo permanece em ponte controlada

## Itens protegidos nesta rodada

1. `note-panel*`
2. `legacy-copy*`

## Veredito da Onda 1

O legado visual ainda vivo nao esta espalhado ao acaso.

Ele esta concentrado em um eixo previsivel:

1. [utilities.css](../../static/css/catalog/shared/utilities.css)
2. superficies do catalogo que ainda carregam [shared.css](../../static/css/catalog/shared.css)

Isso e bom porque:

1. a demoliçao pode ser cirúrgica
2. a Onda 2 pode começar com pouca chance de quebrar telas centrais

## Proximo passo correto

Executar a Onda 2 assim:

1. excluir os mortos imediatos de `utilities.css`
2. rodar testes e smoke visual
3. abrir a proxima auditoria para aliases historicos residuais fora de `utilities.css`, se houver
