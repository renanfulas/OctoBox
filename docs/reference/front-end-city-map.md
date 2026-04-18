# Front-end City Map

## Objetivo

Este arquivo e o mapa operacional do front-end do OctoBox.

Ele existe para responder rapido:

1. onde cada coisa mora
2. quem e dono de que
3. em qual arquivo procurar primeiro
4. como localizar inconsistencia
5. como auditar sem busca cega

Em linguagem simples:

1. este doc mostra a cidade
2. o [front-end-card-architecture.md](C:\Users\renan\OneDrive\Documents\OctoBOX\docs\reference\front-end-card-architecture.md) explica a lei da cidade
3. o [front-end-octobox-organization-standard.md](C:\Users\renan\OneDrive\Documents\OctoBOX\docs\reference\front-end-octobox-organization-standard.md) explica como uma obra nova deve nascer sem virar puxadinho nem overengineering
4. o [pr-front-end-checklist.md](C:\Users\renan\OneDrive\Documents\OctoBOX\docs\reference\pr-front-end-checklist.md) transforma essa lei em triagem curta de PR

## Mapa da cidade

Hoje a cascata visual do OctoBox se organiza em 4 camadas:

1. tema global
2. host de componentes
3. shells de pagina
4. cards proprios de pagina

### 1. Tema global

Arquivo canônico:

1. [C:\Users\renan\OneDrive\Documents\OctoBOX\static\css\design-system\tokens.css](C:\Users\renan\OneDrive\Documents\OctoBOX\static\css\design-system\tokens.css)

Responsabilidade:

1. tipografia base
2. cores semanticas
3. surfaces light e dark
4. bordas, sombras e accents
5. tokens-base de card

Quando mexer:

1. mudou a tinta da casa inteira
2. mudou o tema claro/escuro
3. mudou a linguagem-base de cor, texto ou superficie

Quando nao mexer:

1. o problema existe so em uma pagina
2. o ajuste e so de layout local
3. o card esta com anatomia errada, nao cor errada

### 2. Host de componentes

Arquivos canônicos:

1. [C:\Users\renan\OneDrive\Documents\OctoBOX\static\css\design-system\components\cards.css](C:\Users\renan\OneDrive\Documents\OctoBOX\static\css\design-system\components\cards.css)
2. [C:\Users\renan\OneDrive\Documents\OctoBOX\static\css\design-system\components\card-variants.css](C:\Users\renan\OneDrive\Documents\OctoBOX\static\css\design-system\components\card-variants.css)

Responsabilidade:

1. anatomia de `card` e `table-card`
2. spacing interno estrutural
3. hover e focus oficiais
4. variantes oficiais como `card--support`, `card--priority` e `card--sci-fi`

Quando mexer:

1. o mesmo comportamento vale para varios cards
2. o host precisa responder melhor aos tokens
3. uma nova variante sera reutilizada por mais de uma tela

Quando nao mexer:

1. a necessidade e so da pagina atual
2. a mudanca e editorial ou de clima local

### 3. Shells de pagina

Shells principais do sistema:

1. `student-page-shell`
2. `finance-shell`
3. `class-grid-scene` e workspace da grade
4. `student-form-shell`
5. `owner-notion-shell`

Ponto principal de descoberta:

1. [C:\Users\renan\OneDrive\Documents\OctoBOX\templates\catalog\student-form.html](C:\Users\renan\OneDrive\Documents\OctoBOX\templates\catalog\student-form.html)
2. [C:\Users\renan\OneDrive\Documents\OctoBOX\templates\catalog\finance.html](C:\Users\renan\OneDrive\Documents\OctoBOX\templates\catalog\finance.html)
3. [C:\Users\renan\OneDrive\Documents\OctoBOX\templates\catalog\class-grid.html](C:\Users\renan\OneDrive\Documents\OctoBOX\templates\catalog\class-grid.html)
4. [C:\Users\renan\OneDrive\Documents\OctoBOX\static\css\catalog\student_form_stepper.css](C:\Users\renan\OneDrive\Documents\OctoBOX\static\css\catalog\student_form_stepper.css)

Responsabilidade:

1. clima visual local
2. densidade da pagina
3. ajustes de layout e composicao
4. pequenos overrides por variavel ou contexto

Em linguagem simples:

1. o tema global escolhe a tinta
2. o host do card escolhe o molde
3. a pagina escolhe a roupa daquele ambiente

### 4. Cards proprios de pagina

Esses cards continuam usando o DNA do tema, mas ja nao dependem da anatomia generica como autoridade principal.

Exemplos reais:

1. [C:\Users\renan\OneDrive\Documents\OctoBOX\static\css\catalog\shared\student-page-shell.css](C:\Users\renan\OneDrive\Documents\OctoBOX\static\css\catalog\shared\student-page-shell.css)
2. [C:\Users\renan\OneDrive\Documents\OctoBOX\static\css\catalog\shared\student-financial.css](C:\Users\renan\OneDrive\Documents\OctoBOX\static\css\catalog\shared\student-financial.css)
3. [C:\Users\renan\OneDrive\Documents\OctoBOX\static\css\catalog\finance\_cards.css](C:\Users\renan\OneDrive\Documents\OctoBOX\static\css\catalog\finance\_cards.css)

Quando mexer:

1. o card e estruturalmente proprio daquela pagina
2. a pagina ja precisou de anatomia, slots ou hierarquia muito especificos

## O que cada arquivo faz

| Arquivo | O que faz | Quando mexer | Quando nao mexer |
|---|---|---|---|
| [C:\Users\renan\OneDrive\Documents\OctoBOX\static\css\design-system\tokens.css](C:\Users\renan\OneDrive\Documents\OctoBOX\static\css\design-system\tokens.css) | tema, fonte, surfaces, texto, bordas, sombras e tokens-base | quando a mudanca e global | quando o problema e local |
| [C:\Users\renan\OneDrive\Documents\OctoBOX\static\css\design-system\components\cards.css](C:\Users\renan\OneDrive\Documents\OctoBOX\static\css\design-system\components\cards.css) | host compartilhado de `card` e `table-card` | quando a anatomia base precisa mudar | quando a mudanca e so de uma tela |
| [C:\Users\renan\OneDrive\Documents\OctoBOX\static\css\design-system\components\card-variants.css](C:\Users\renan\OneDrive\Documents\OctoBOX\static\css\design-system\components\card-variants.css) | variantes oficiais do host | quando o padrao sera reutilizado | quando o caso e unico de uma pagina |
| [C:\Users\renan\OneDrive\Documents\OctoBOX\static\css\catalog\shared\student-page-shell.css](C:\Users\renan\OneDrive\Documents\OctoBOX\static\css\catalog\shared\student-page-shell.css) | shell da pagina do aluno e cards proprios da ficha premium | quando o ajuste e do clima da pagina do aluno | quando a mudanca vale para finance, dashboard ou class grid |
| [C:\Users\renan\OneDrive\Documents\OctoBOX\static\css\catalog\shared\student-financial.css](C:\Users\renan\OneDrive\Documents\OctoBOX\static\css\catalog\shared\student-financial.css) | cards e drawers do financeiro do aluno | quando o ajuste e do dominio student financial | quando o mesmo comportamento vale para o host global |
| [C:\Users\renan\OneDrive\Documents\OctoBOX\static\css\catalog\finance\_dark.css](C:\Users\renan\OneDrive\Documents\OctoBOX\static\css\catalog\finance\_dark.css) | ajustes dark contextuais da central financeira | quando a assinatura dark e so do finance shell | quando a resposta deveria nascer do token ou do host |
| [C:\Users\renan\OneDrive\Documents\OctoBOX\static\css\catalog\class-grid\workspace.css](C:\Users\renan\OneDrive\Documents\OctoBOX\static\css\catalog\class-grid\workspace.css) | overrides locais e `--card-local-*` da grade | quando o clima e do workspace da grade | quando a mudanca e um padrao global de card |

## Ownership por dominio

Use este mapa como trilho curto. Para ownership mais amplo do produto, veja [C:\Users\renan\OneDrive\Documents\OctoBOX\docs\reference\front-end-ownership-map.md](C:\Users\renan\OneDrive\Documents\OctoBOX\docs\reference\front-end-ownership-map.md).

| Dominio | Shell / raiz | CSS principal | Leitura pratica |
|---|---|---|---|
| Student page | `student-page-shell` em [C:\Users\renan\OneDrive\Documents\OctoBOX\templates\catalog\student-form.html](C:\Users\renan\OneDrive\Documents\OctoBOX\templates\catalog\student-form.html) | [C:\Users\renan\OneDrive\Documents\OctoBOX\static\css\catalog\shared\student-page-shell.css](C:\Users\renan\OneDrive\Documents\OctoBOX\static\css\catalog\shared\student-page-shell.css) | pagina premium do aluno e seus cards proprios |
| Student form | `student-form-shell` | [C:\Users\renan\OneDrive\Documents\OctoBOX\static\css\catalog\student_form_stepper.css](C:\Users\renan\OneDrive\Documents\OctoBOX\static\css\catalog\student_form_stepper.css) | stepper, formularios e disclosure panels |
| Finance | `finance-shell` em [C:\Users\renan\OneDrive\Documents\OctoBOX\templates\catalog\finance.html](C:\Users\renan\OneDrive\Documents\OctoBOX\templates\catalog\finance.html) | pasta [C:\Users\renan\OneDrive\Documents\OctoBOX\static\css\catalog\finance](C:\Users\renan\OneDrive\Documents\OctoBOX\static\css\catalog\finance) | boards, rail, metrics e assinatura financeira |
| Class grid | `class-grid-scene` em [C:\Users\renan\OneDrive\Documents\OctoBOX\templates\catalog\class-grid.html](C:\Users\renan\OneDrive\Documents\OctoBOX\templates\catalog\class-grid.html) | pasta [C:\Users\renan\OneDrive\Documents\OctoBOX\static\css\catalog\class-grid](C:\Users\renan\OneDrive\Documents\OctoBOX\static\css\catalog\class-grid) | agenda, weekly cards, monthly cards e contexto |
| Owner notion | `owner-notion-shell` | pasta [C:\Users\renan\OneDrive\Documents\OctoBOX\static\css\design-system\operations\owner\notion](C:\Users\renan\OneDrive\Documents\OctoBOX\static\css\design-system\operations\owner\notion) | narrativas, paineis e superfices operacionais do owner |

## Exemplos reais

### 1. Card compartilhado

Exemplo:

1. [C:\Users\renan\OneDrive\Documents\OctoBOX\templates\guide\system-map.html](C:\Users\renan\OneDrive\Documents\OctoBOX\templates\guide\system-map.html)

Leitura:

1. usa `card` direto
2. depende do host compartilhado
3. e o melhor exemplo de quando o sistema ja resolve quase tudo sozinho

### 2. Override por pagina

Exemplo:

1. [C:\Users\renan\OneDrive\Documents\OctoBOX\static\css\catalog\class-grid\workspace.css](C:\Users\renan\OneDrive\Documents\OctoBOX\static\css\catalog\class-grid\workspace.css)

Leitura:

1. a grade ajusta `--card-local-surface`, `--card-local-border` e `--card-local-shadow`
2. o card continua sendo da mesma familia
3. a pagina so muda o clima visual

### 3. Variante oficial

Exemplo:

1. [C:\Users\renan\OneDrive\Documents\OctoBOX\templates\includes\catalog\student_form\financial\financial_overview.html](C:\Users\renan\OneDrive\Documents\OctoBOX\templates\includes\catalog\student_form\financial\financial_overview.html)

Leitura:

1. usa `card card--sci-fi`
2. o host base continua mandando
3. a variante muda a personalidade oficial

### 4. Card proprio da pagina

Exemplo:

1. [C:\Users\renan\OneDrive\Documents\OctoBOX\templates\includes\catalog\student_page\student_page_payments_summary.html](C:\Users\renan\OneDrive\Documents\OctoBOX\templates\includes\catalog\student_page\student_page_payments_summary.html)
2. [C:\Users\renan\OneDrive\Documents\OctoBOX\static\css\catalog\shared\student-page-shell.css](C:\Users\renan\OneDrive\Documents\OctoBOX\static\css\catalog\shared\student-page-shell.css)

Leitura:

1. `student-page-charge-card` ja tem identidade e anatomia editorial local
2. ele ainda usa o tema global
3. mas a manutencao estrutural pertence a pagina do aluno

## Sinais de perigo

Estes sinais indicam que a cascata esta virando divida:

1. `!important` visual para ganhar no grito
2. seletor profundo demais, como `body[data-theme=\"dark\"] .alguma-pagina .algum-card .algum-titulo`
3. dark mode paralelo da pagina redesenhando o card inteiro
4. override espalhado pelo mesmo dominio em muitos arquivos
5. pagina redefinindo `.card` ou `.table-card` estruturalmente
6. card que nao responde nem ao token global nem ao shell da pagina
7. card que exige muitos seletores contextuais para manter a mesma aparencia

Em linguagem simples:

1. quando a parede precisa de muita fita, a estrutura ja esta pedindo revisao

## Convencao de auditoria

### Buscas recomendadas

Procure estes sinais:

```powershell
Get-ChildItem -Path .\\static\\css -Recurse -File | Select-String -Pattern '!important'
```

```powershell
Get-ChildItem -Path .\\static\\css -Recurse -File | Select-String -Pattern 'legacy-panel'
```

```powershell
Get-ChildItem -Path .\\static\\css -Recurse -File | Select-String -Pattern '\\.card|\\.table-card'
```

```powershell
Get-ChildItem -Path .\\static\\css -Recurse -File | Select-String -Pattern 'body\\[data-theme=\"dark\"\\].*\\.card'
```

### Classificacao de achados

| Classe do achado | O que significa |
|---|---|
| Saudavel | usa host, variante ou shell de forma previsivel |
| Transitorio | adaptador de migracao ainda aceitavel |
| Divida real | seletor profundo, repaint estrutural ou `!important` visual |
| Candidato a split | a pagina ja esta lutando demais contra o host |

## Anti-patterns

Evite estes comportamentos:

1. redefinir `.card` inteira dentro da pagina
2. criar card novo sem passar pela arvore de decisao
3. fazer dark mode estrutural local do card
4. usar `!important` para superficie, borda, sombra ou texto estrutural do card
5. espalhar override da mesma pagina em varios arquivos sem ownership claro
6. criar um segundo host visual escondido para resolver um caso unico

## Referencias cruzadas

Para entender a lei da cidade, leia:

1. [C:\Users\renan\OneDrive\Documents\OctoBOX\docs\reference\front-end-card-architecture.md](C:\Users\renan\OneDrive\Documents\OctoBOX\docs\reference\front-end-card-architecture.md)
2. [C:\Users\renan\OneDrive\Documents\OctoBOX\docs\reference\design-system-contract.md](C:\Users\renan\OneDrive\Documents\OctoBOX\docs\reference\design-system-contract.md)
3. [C:\Users\renan\OneDrive\Documents\OctoBOX\docs\experience\css-guide.md](C:\Users\renan\OneDrive\Documents\OctoBOX\docs\experience\css-guide.md)
