<!--
ARQUIVO: mapa forense do front-end do OctoBox.

POR QUE ELE EXISTE:
- transforma bug visual, override estranho e comportamento de tela em trilho curto de investigacao.
- reduz limpeza cega e remendo por tentativa e erro.
- junta pistas reais da base para dizer onde o problema costuma nascer e que tipo de correcao costuma resolver.

O QUE ESTE ARQUIVO FAZ:
1. define um protocolo curto de leitura da "cena do crime".
2. lista padroes recorrentes de bug, override e legado visual.
3. aponta arquivos suspeitos e ownership provavel por tipo de sintoma.
4. sugere correcoes de menor arrependimento para evitar debito tecnico.

PONTOS CRITICOS:
- este documento nao substitui runtime, smoke visual ou testes.
- ele nao autoriza apagar CSS por grep isolado.
- exemplos citados aqui sao pistas reais da base atual, mas o ownership vivo do codigo ainda deve vencer se houver divergencia.
-->

# Mapa forense do front-end

Este documento existe para responder quatro perguntas quando a interface parece "estranha":

1. o que olhar primeiro
2. qual pista costuma significar o que
3. onde o problema provavelmente nasceu
4. qual correcao tende a resolver sem quebrar outra sala do predio

Em linguagem simples:

1. primeiro a gente identifica em qual comodo a fumaca apareceu
2. depois descobre se o fogo veio da tomada, do fio na parede ou do quadro geral
3. so entao troca o que precisa ser trocado

Mapas irmaos desta frente:

1. [front-end-ownership-map.md](front-end-ownership-map.md) para ownership e trilho curto de localizacao
2. [front-end-contract-forensics-map.md](front-end-contract-forensics-map.md) para falhas de payload, presenter e backend visual
3. [front-end-forensics-checklist.md](front-end-forensics-checklist.md) para checklist operacional de depuracao
4. [front-end-wave1-catalog-shared-audit.md](front-end-wave1-catalog-shared-audit.md) para o raio-x da primeira onda no hotspot `catalog/shared`
5. [front-end-runtime-boundary-map.md](front-end-runtime-boundary-map.md) para separar runtime ativo, output coletado e arvore espelho
6. [front-end-error-patterns-map.md](front-end-error-patterns-map.md) para padroes recorrentes de erro, causa raiz e correcao segura
7. [front-end-neon-contract-map.md](front-end-neon-contract-map.md) para o contrato vivo entre KPI, shell e highlight da sidebar
8. [front-end-dashboard-action-contract-map.md](front-end-dashboard-action-contract-map.md) para o catalogo dos `data_action` interativos do dashboard
9. [front-end-data-action-debug-checklist.md](front-end-data-action-debug-checklist.md) para o pronto-socorro de debug quando um clique nao reage
10. [front-end-wave4-contract-audit.md](front-end-wave4-contract-audit.md) para o raio-x da trilha contratual entre payload, presenter, shell e template
11. [front-end-wave4-operations-dependency-map.md](front-end-wave4-operations-dependency-map.md) para o inventario de onde `operations.css` ainda e full, pending ou contract-only no catalogo
12. [front-end-contract-only-visual-smoke-checklist.md](front-end-contract-only-visual-smoke-checklist.md) para o roteiro curto de validacao visual das telas migradas para o contrato minimo
13. [front-end-search-cache-contract-map.md](front-end-search-cache-contract-map.md) para o contrato de cache local, versionamento e invalidação das buscas ricas
14. [front-end-owner-workspace-audit.md](front-end-owner-workspace-audit.md) para o raio-x do `/operacao/owner/`, legado notion e manifestos vivos da superficie
15. [dashboard-darkmode-cascade-roadmap.md](dashboard-darkmode-cascade-roadmap.md) para o mapa de familias repetidas de contraste ruim, wrappers paralelos e ordem de correcao do dashboard no dark mode

## Ordem curta de leitura da cena do crime

Se o problema for visual, de layout, de CSS ou de comportamento de tela, comece nesta ordem:

1. [../../README.md](../../README.md)
2. [documentation-authority-map.md](documentation-authority-map.md)
3. [front-end-ownership-map.md](front-end-ownership-map.md)
4. [design-system-contract.md](design-system-contract.md)
5. [../plans/front-end-restructuring-guide.md](../plans/front-end-restructuring-guide.md)
6. [../experience/css-guide.md](../experience/css-guide.md)
7. [../plans/front-legacy-rule-retirement-sdd.md](../plans/front-legacy-rule-retirement-sdd.md)
8. [../../.agents/skills/octobox-ui-cleanup-auditor/scripts/frontend_forensics.py](../../.agents/skills/octobox-ui-cleanup-auditor/scripts/frontend_forensics.py)
9. [../../.agents/scripts/ghost_audit.py](../../.agents/scripts/ghost_audit.py)

Regra pratica:

1. se o bug aparece em varias telas, suspeite primeiro do shell, design system ou camada compartilhada
2. se aparece so em uma tela, suspeite primeiro do template local, CSS local, JS local ou presenter da pagina
3. se os dados estao certos e a tela esta errada, o problema costuma estar do payload para frente
4. se os dados ja chegam errados, o problema costuma estar do presenter para tras
5. se o sintoma for "texto escuro, pill estranha, card lavado ou board pesado no dashboard dark", abra antes o [dashboard-darkmode-cascade-roadmap.md](dashboard-darkmode-cascade-roadmap.md)
6. se o sintoma for "moldura dupla em grid dark" ou "barra de progresso curta dentro do card", consulte tambem [front-end-error-patterns-map.md](front-end-error-patterns-map.md) antes de mexer em HTML

## Perguntas que resolvem metade da investigacao

Antes de mexer no codigo, responda estas perguntas:

1. o problema esta na casca global ou so no miolo de uma pagina?
2. a tela esta errada porque o dado veio errado ou porque o dado foi montado errado visualmente?
3. a regra esta no lugar certo ou um arquivo local esta tentando mandar em uma regra canonica?
4. existe `!important`, `style=""`, seletor muito longo ou id selector ganhando no grito?
5. o nome parece legado, mas a regra ainda e host canonico ou alias protegido?
6. a pagina realmente carrega esse CSS ou esse JS, ou estamos investigando um arquivo que nem sobe?

## Padroes principais, pistas e correcoes

### 1. Casca certa, miolo errado

Sinais na cena:

1. sidebar, topbar e hero principal parecem certos
2. o card interno, rail ou bloco de conteudo parece desalinhado, pesado demais ou com respiro errado
3. a sensacao e "o quarto esta feio, mas a casa esta certa"

Leitura provavel:

1. o shell global nao e o culpado principal
2. a autoridade errada costuma estar no CSS local da pagina ou num include interno

Onde olhar primeiro:

1. template principal da tela
2. includes locais da tela
3. CSS local da area
4. presenter ou payload da pagina

Arquivos suspeitos recorrentes:

1. [../../static/css/catalog/finance/](../../static/css/catalog/finance/)
2. [../../static/css/catalog/students/](../../static/css/catalog/students/)
3. [../../static/css/catalog/class-grid/](../../static/css/catalog/class-grid/)
4. [../../templates/catalog](../../templates/catalog)

Correcao que costuma funcionar:

1. corrigir primeiro no CSS local da superficie
2. so subir para design system se a regra for realmente compartilhada
3. evitar mexer em `tokens.css` ou `components.css` para apagar um bug que vive so em uma sala

### 2. Override gritando com `!important`

Sinais na cena:

1. a regra so funciona quando alguem "grita mais alto"
2. pequenos ajustes em um lugar quebram outro
3. a sensacao e "uma fita isolante segurando um cano"

Leitura provavel:

1. existe disputa de autoridade entre camada compartilhada e camada local
2. a hierarquia de ownership foi invertida

Onde olhar primeiro:

1. [../../static/css/catalog/shared/utilities.css](../../static/css/catalog/shared/utilities.css)
2. [../../static/css/catalog/shared/student-page-shell.css](../../static/css/catalog/shared/student-page-shell.css)
3. [../../static/css/catalog/class-grid/workspace.css](../../static/css/catalog/class-grid/workspace.css)
4. [../../static/css/design-system/components/pills.css](../../static/css/design-system/components/pills.css)
5. [../../static/css/design-system/components/actions.css](../../static/css/design-system/components/actions.css)

Pistas reais da base:

1. ha `!important` em regras de selecao de plano, hidden states, pills e refinamentos locais
2. isso costuma indicar que a regra certa perdeu ownership em algum ponto da cascata

Correcao que costuma funcionar:

1. mover a responsabilidade para a camada certa
2. reduzir especificidade em vez de adicionar mais `!important`
3. preferir `token -> primitivo canonico -> classe semantica local -> helper neutro`

### 3. `style=""` ou `<style>` dentro de template

Sinais na cena:

1. o HTML esta carregando decisao visual na mao
2. a regra desaparece do mapa de ownership do CSS
3. a manutencao vira caca ao tesouro

Leitura provavel:

1. a tela esta pulando a estrada oficial do design system
2. parte da aparencia virou detalhe secreto no template

Onde olhar primeiro:

1. [../../templates/catalog/student-source-capture.html](../../templates/catalog/student-source-capture.html)
2. includes da pagina que usa barras, charts ou width dinamica
3. assets da tela no payload

Pistas reais da base:

1. ha `style=""` em [../../templates/catalog/student-source-capture.html](../../templates/catalog/student-source-capture.html)
2. ha tambem usos de custom properties inline para largura, altura ou colunas dinamicas em includes de financeiro

Correcao que costuma funcionar:

1. se o valor for estatico, mover para CSS local ou shared
2. se o valor for realmente dinamico, manter apenas a variavel inline e deixar toda a aparencia no CSS
3. nao usar inline style para decidir margem, cor, borda ou estrutura fixa

### 4. Nome legado que parece morto, mas ainda esta vivo

Sinais na cena:

1. a classe parece velha
2. o nome da variavel ou do host nao combina com a linguagem nova
3. a intuicao pede apagar, mas a tela ainda depende dela

Leitura provavel:

1. voce esta diante de um alias canonizado ou de uma ponte de transicao
2. matar rapido aqui gera regressao silenciosa

Onde olhar primeiro:

1. [../../static/css/design-system/components/states.css](../../static/css/design-system/components/states.css)
2. [../../static/css/catalog/shared/scene.css](../../static/css/catalog/shared/scene.css)
3. [../../static/css/catalog/shared/student-financial.css](../../static/css/catalog/shared/student-financial.css)
4. [../plans/front-legacy-rule-retirement-sdd.md](../plans/front-legacy-rule-retirement-sdd.md)

Pistas reais da base:

1. `note-panel*` ainda vive como host de estado real
2. `legacy-copy*` ainda aparece como nomenclatura historica em camadas vivas

Correcao que costuma funcionar:

1. classificar antes de deletar
2. tratar `note-panel*` e `legacy-copy*` como suspeitos protegidos
3. so migrar com plano explicito de equivalencia

### 5. Ponte legada ainda segurando uma tela

Sinais na cena:

1. a aparencia parece misturar tema atual e atmosfera antiga
2. a tela melhora quando voce mexe em arquivo "shared" ou "utilities", mesmo sem ser o dono ideal
3. a sensacao e "essa parede ainda esta apoiada em um escoramento temporario"

Leitura provavel:

1. uma familia historica ainda esta sustentando uma superficie real
2. o rebaixo do legado ainda nao terminou

Onde olhar primeiro:

1. [../../static/css/catalog/shared.css](../../static/css/catalog/shared.css)
2. [../../static/css/catalog/shared/utilities.css](../../static/css/catalog/shared/utilities.css)
3. [../../static/css/catalog/finance/_shell.css](../../static/css/catalog/finance/_shell.css)
4. [../plans/front-legacy-rule-retirement-wave1-inventory.md](../plans/front-legacy-rule-retirement-wave1-inventory.md)

Pistas reais da base:

1. `glass-panel` ainda aparece em partes vivas do catalogo
2. `utilities.css` continua sendo hotspot de heranca, helper e resquicio historico

Correcao que costuma funcionar:

1. migrar a autoridade para token, componente canonico ou classe semantica local
2. rebaixar a ponte antes de excluir
3. nunca apagar a ponte sem provar que a sala ja esta apoiada em outra estrutura

### 6. Mesmo seletor mandando em arquivos diferentes

Sinais na cena:

1. duas alteracoes distantes brigam pelo mesmo comportamento
2. corrigir um arquivo nao encerra o bug
3. a sensacao e "dois chefes dando ordem para o mesmo time"

Leitura provavel:

1. ha duplicacao de ownership
2. um seletor foi copiado, promovido ou refinado sem matar a sombra antiga

Onde olhar primeiro:

1. [../../static/css/design-system/operations/refinements/display-wall.css](../../static/css/design-system/operations/refinements/display-wall.css)
2. [../../static/css/design-system/operations.css](../../static/css/design-system/operations.css)

Pistas reais da base:

1. seletores de boards como `#manager-enrollment-link-board`, `#manager-finance-board` e `#manager-intake-board` aparecem em mais de um arquivo

Correcao que costuma funcionar:

1. escolher o dono canonico
2. manter a sombra so se houver motivo de transicao claramente documentado
3. se nao houver motivo, fundir ou remover a definicao secundaria

### 7. Arquivo residual, backup ou fantasma de obra

Sinais na cena:

1. existe arquivo `.bkp`, `.bak` ou `.old`
2. ele parece inocente, mas gera duvida sobre qual e a verdade
3. a equipe perde tempo lendo parede falsa

Leitura provavel:

1. ha residuo de obra ou backup manual no meio do runtime visual
2. mesmo que nao carregue, ele aumenta ruido operacional

Onde olhar primeiro:

1. [../../static/css/design-system/components/dashboard/summary.css.bkp](../../static/css/design-system/components/dashboard/summary.css.bkp)

Correcao que costuma funcionar:

1. confirmar que nao existe import ou referencia viva
2. remover do repositorio quando a prova de nao uso estiver clara
3. nao usar backup manual no meio da arvore canonica de CSS

### 8. JS achando elemento por classe visual

Sinais na cena:

1. renomear classe "quebra o comportamento"
2. o CSS muda e o JS para de achar o alvo
3. a interface parece acoplada por maquiagem

Leitura provavel:

1. o comportamento esta dependente de classe cosmetica
2. faltam hooks estruturais estaveis

Onde olhar primeiro:

1. [../../static/js/core/shell.js](../../static/js/core/shell.js)
2. [../../static/js/core/forms.js](../../static/js/core/forms.js)
3. JS local da pagina
4. template para procurar `data-page`, `data-slot`, `data-panel`, `data-ui` e `data-action`

Correcao que costuma funcionar:

1. mover descoberta de elemento para `data-*`
2. deixar classe para aparencia e hook para comportamento
3. nao usar classe visual como contrato tecnico quando um hook estrutural puder existir

### 9. Template descobrindo regra de negocio no grito

Sinais na cena:

1. template cheio de `if`, `elif`, duplicacao de badge ou repeticao de copy
2. a tela so funciona porque o HTML esta inferindo o estado
3. a sensacao e "a recepcao esta fazendo o trabalho do backoffice"

Leitura provavel:

1. o payload da tela esta fraco, ambiguo ou pesado de forma errada
2. a view ou presenter nao entregou o contrato semantico limpo

Onde olhar primeiro:

1. [../../shared_support/page_payloads.py](../../shared_support/page_payloads.py)
2. `presentation` do dominio
3. [../../access/context_processors.py](../../access/context_processors.py)
4. [../../access/shell_actions.py](../../access/shell_actions.py)

Correcao que costuma funcionar:

1. backend entrega verdade, acesso, estado e acao possivel
2. frontend organiza composicao, repeticao visual e hierarquia
3. se a mesma informacao aparece em varios pontos, o payload continua semantico e unico

### 10. Voce mexe no arquivo certo, mas nada muda

Sinais na cena:

1. a regra parece correta, mas o navegador continua igual
2. a mudanca so aparece em outra tela ou nao aparece em nenhuma
3. a sensacao e "estamos trocando a lampada do quarto errado"

Leitura provavel:

1. o arquivo nao esta sendo carregado pela pagina
2. voce esta olhando uma fachada de compatibilidade, nao o ponto vivo
3. o include certo ou asset certo nao foi localizado ainda

Onde olhar primeiro:

1. payload ou builder da pagina
2. template principal
3. includes carregados por aquela pagina
4. CSS local da area
5. JS local da area

Correcao que costuma funcionar:

1. provar a cadeia `template -> include -> CSS -> JS -> payload`
2. listar os assets reais carregados pela tela
3. so depois editar

## Suspeitos recorrentes da base

Estes arquivos merecem lupa primeiro quando o front aparenta comportamento fantasma:

1. [../../static/css/catalog/shared/utilities.css](../../static/css/catalog/shared/utilities.css)
2. [../../static/css/catalog/shared.css](../../static/css/catalog/shared.css)
3. [../../static/css/catalog/shared/student-page-shell.css](../../static/css/catalog/shared/student-page-shell.css)
4. [../../static/css/design-system/components/states.css](../../static/css/design-system/components/states.css)
5. [../../static/css/design-system/operations/refinements/display-wall.css](../../static/css/design-system/operations/refinements/display-wall.css)
6. [../../static/css/design-system/operations.css](../../static/css/design-system/operations.css)
7. [../../templates/catalog/student-source-capture.html](../../templates/catalog/student-source-capture.html)
8. [../../shared_support/page_payloads.py](../../shared_support/page_payloads.py)
9. [../../access/context_processors.py](../../access/context_processors.py)
10. [../../access/shell_actions.py](../../access/shell_actions.py)

## Correcoes de menor arrependimento

Quando a duvida for "qual correcao mexe menos no predio inteiro?", prefira esta ordem:

1. mapear ownership real da tela
2. provar a cadeia de carregamento
3. classificar o achado como morto, ponte, alias, hotspot ou duplicacao
4. mover a autoridade para a camada certa
5. so depois excluir, fundir ou rebaixar regra antiga

Regra de ouro:

1. nao apague CSS porque o nome parece velho
2. nao suba um ajuste local para o design system por preguiça
3. nao adicione `!important` para ganhar uma briga que o ownership deveria resolver
4. nao confunda alias canonico com sujeira morta

## Veredito pratico

No OctoBox, bug visual raramente nasce por magia.

Quase sempre ele nasce de uma destas familias:

1. ownership errado
2. cascata invertida
3. ponte legada ainda viva
4. template mandando demais
5. payload fraco ou ambiguo
6. arquivo certo nao carregado pela tela

Em termos infantis:

1. a bagunca quase nunca aparece porque "a casa e ruim"
2. ela costuma aparecer porque alguem guardou o brinquedo na caixa errada
3. o trabalho correto e descobrir qual caixa manda naquela brincadeira
