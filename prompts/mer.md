<!--
ARQUIVO: sistema mestre M.E.R de medicao, evals e roteamento do OctoBOX.

POR QUE ELE EXISTE:
- tira a escolha de modelo e prompt do improviso.
- transforma tarefas reais do projeto em benchmark operacional.

O QUE ESTE ARQUIVO FAZ:
1. define um benchmark com tarefas reais do OctoBOX.
2. registra metricas de qualidade, custo e repetibilidade.
3. estabelece roteamento de modelo, rotina e circuito de aprendizado.

PONTOS CRITICOS:
- se nao houver medicao, a sensacao de progresso pode ser falsa.
- este arquivo precisa evoluir com o repositorio e com os erros reais encontrados.
-->

# M.E.R

`M.E.R` significa `Medicao, Evals e Roteamento`.

O papel dele e simples:

- medir se a IA esta ajudando de verdade
- comparar tarefas reais do OctoBOX
- escolher modelo e modo com criterio
- transformar erro em sistema e nao em trauma

## Benchmark real do OctoBOX

Use estas tarefas como campo de treino e medicao.

### Debug

| ID | Tarefa real | Arquivos base | Resultado ideal | Erro aceitavel | Erro proibido | Tempo esperado | Tokens aceitaveis |
| --- | --- | --- | --- | --- | --- | --- | --- |
| D1 | Corrigir teste que tenta setar `is_authenticated` manualmente | `tests/test_shell_and_context.py`, `access/roles/__init__.py` | achar a simulacao errada, trocar por estrategia correta e validar o fluxo | ajustar o teste com pequena mudanca de fixture | mascarar o bug sem entender o contrato do Django | 20-35 min | 2k-6k |
| D2 | Resolver falha de teste por dependencia ausente de `pytest` | `tests/test_performance.py`, `requirements_dev.txt`, `pytest.ini` | provar se o problema e dependencia, runner ou escopo do teste | sugerir instalacao e confirmar impacto | remover teste relevante sem justificativa | 15-30 min | 2k-5k |
| D3 | Isolar side effect no import que quebra smoke de importacao | `tests/test_import_all_modules.py`, `check_users.py` | encontrar o side effect de banco no import e mover para trilho seguro | sugerir guardrail parcial | deixar import com mutacao silenciosa de dados | 25-45 min | 3k-8k |
| D4 | Diagnosticar 404 de CSS do dashboard | `dashboard/presentation.py`, `static/css/design-system/dashboard.css` | localizar path errado e restaurar contrato de asset | corrigir um path e deixar outro para follow-up explicito | dizer que esta resolvido sem validar 404 | 15-30 min | 2k-5k |
| D5 | Investigar lentidao percebida no dashboard | `dashboard/dashboard_snapshot_queries.py`, `shared_support/performance.py`, `dashboard/presentation.py` | localizar gargalo em query, snapshot ou payload e propor medicao ou fix | entregar hipotese com plano de prova | afirmar gargalo sem evidencia | 30-60 min | 4k-10k |

### Refactor

| ID | Tarefa real | Arquivos base | Resultado ideal | Erro aceitavel | Erro proibido | Tempo esperado | Tokens aceitaveis |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R1 | Tirar bootstrap perigoso da raiz e mover para trilho explicito | `check_users.py`, `shared_support/management/commands/*` | remover side effect no import e criar caminho manual seguro | manter script transicional com aviso forte | deixar senha fraca e mutacao no import | 30-60 min | 4k-9k |
| R2 | Separar shell global de CSS de dominio | `static/css/design-system.css`, `static/css/design-system/components.css`, `static/css/design-system/dashboard.css`, `static/css/design-system/financial.css` | ownership claro entre shell, shared e domain | deixar um modulo ainda transicional com TODO explicito | continuar carregando CSS de dominio no bundle global sem necessidade | 45-90 min | 5k-12k |
| R3 | Quebrar `dashboard/presentation.py` em builders menores | `dashboard/presentation.py` | reduzir tamanho e acoplamento mantendo a mesma facade publica | extrair 1 ou 2 builders e manter parte monolitica por enquanto | alterar contrato de payload sem mapear impacto | 60-120 min | 6k-14k |
| R4 | Organizar montagem da ficha do aluno por responsabilidades | `catalog/presentation/student_form_page.py`, `catalog/presentation/shared.py` | separar assets, contexto e bloco de composicao | manter agregador final enquanto extrai helpers | espalhar contexto em varios lugares sem ownership | 60-120 min | 6k-14k |
| R5 | Consolidar namespace de seguranca duplicado | `shared_support/defenses/*`, `shared_support/security/*` | definir corredor unico e plano de migracao seguro | manter alias transicional documentado | apagar namespace usado sem mapear imports | 60-120 min | 6k-14k |

### Front-end

| ID | Tarefa real | Arquivos base | Resultado ideal | Erro aceitavel | Erro proibido | Tempo esperado | Tokens aceitaveis |
| --- | --- | --- | --- | --- | --- | --- | --- |
| F1 | Remover `onclick` inline do shell principal | `templates/layouts/base.html`, `static/js/core/shell.js` | mover comportamento para delegation com hook estrutural | manter um fallback curto enquanto adapta | manter logica relevante presa no template | 20-40 min | 3k-7k |
| F2 | Substituir handlers globais no billing console | `templates/includes/catalog/student_form/financial/billing_console.html`, `static/js/pages/finance/billing_console.js` | migrar para `data-action` e listeners locais | manter `prompt` ou `alert` temporariamente com trilha clara | continuar com `window.*` chamado do HTML | 30-60 min | 4k-9k |
| F3 | Tirar aparencia inline do sistema de tabs | `static/js/pages/interactive_tabs.js`, CSS do modulo | mover visual para classes de estado | ajustar uma classe adicional no CSS | deixar JS manipulando cor, sombra ou borda inline | 20-45 min | 3k-7k |
| F4 | Limpar API global do stepper do aluno | `static/js/pages/students/student-form-stepper.js`, templates do form | substituir `window.*` por `data-*` e estado local | manter adaptador curto enquanto migra | quebrar fluxo de matricula e pagamento | 45-90 min | 5k-12k |
| F5 | Fechar ownership visual do dashboard | `dashboard/presentation.py`, `static/css/design-system/dashboard.css`, templates do dashboard | dashboard carregar seu pacote visual sem contaminar shell | manter um import transicional com TODO documentado | espalhar regras do dashboard no bundle global | 45-90 min | 5k-12k |

### Arquitetura

| ID | Tarefa real | Arquivos base | Resultado ideal | Erro aceitavel | Erro proibido | Tempo esperado | Tokens aceitaveis |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A1 | Definir corredor oficial entre snapshots financeiros e dashboard | `dashboard/dashboard_snapshot_queries.py`, `catalog/finance_snapshot/*`, `dashboard/presentation.py` | mapa claro de ownership, facade e fluxo de dados | assumir um estado transicional com camada adaptadora | misturar query, composicao e view sem fronteira | 45-90 min | 5k-12k |
| A2 | Desenhar fronteira minima para futuro multi-tenant | `access/*`, `catalog/*`, `finance/*`, `operations/*` | definir conceito de workspace ou box, escopo de dados e pontos de isolamento | propor etapa 0 sem implementar tudo | tratar multi-tenant como rename cosmetico | 60-120 min | 7k-16k |
| A3 | Planejar camada assincrona para auditoria, jobs e integracoes | `auditing/tasks.py`, `jobs/*`, `integrations/*`, `shared_support/events.py` | propor corredor de eventos e regra de quando usar fila | aceitar fase transicional sem broker completo | colocar Celery ou fila sem contrato nem dono | 60-120 min | 7k-16k |
| A4 | Evoluir pipeline de assets sem reescrever stack | `shared_support/page_payloads.py`, `shared_support/static_assets.py`, `catalog/presentation/shared.py` | definir caminho de curto e medio prazo para assets e cache | manter expansao runtime com cache melhorado | propor bundler complexo sem necessidade atual | 45-90 min | 5k-12k |
| A5 | Desenhar hardening do perimetro de seguranca e performance | `shared_support/security/*`, `shared_support/defenses/*`, `api/*`, `monitoring/*` | plano claro de camadas, guardrails e observabilidade | deixar uma camada duplicada transicional | criar seguranca cenografica sem enforcement | 60-120 min | 7k-16k |

### Review

| ID | Tarefa real | Arquivos base | Resultado ideal | Erro aceitavel | Erro proibido | Tempo esperado | Tokens aceitaveis |
| --- | --- | --- | --- | --- | --- | --- | --- |
| V1 | Review de superficies sensiveis de bootstrap e admin | `check_users.py`, `api/v1/views.py` | apontar riscos concretos de senha fraca, side effect e bootstrap inseguro | aceitar um atalho local se estiver isolado e documentado | ignorar risco porque o projeto ainda e local | 20-40 min | 3k-7k |
| V2 | Review do pipeline de assets do dashboard | `dashboard/presentation.py`, `shared_support/page_payloads.py`, `shared_support/static_assets.py` | achar 404, duplicacao, acoplamento ou vazamento de CSS | aceitar debt transicional com plano claro | aprovar contrato quebrado de asset | 25-45 min | 4k-8k |
| V3 | Review do cockpit financeiro do aluno | `billing_console.html`, `billing_console.js`, CSS relacionado | achar acoplamento HTML-JS, UX ruim e risco de manutencao | aceitar fase transicional com backlog claro | focar so em cosmetica e perder risco estrutural | 25-45 min | 4k-8k |
| V4 | Review das queries e snapshots do dashboard | `dashboard/dashboard_snapshot_queries.py`, `catalog/finance_snapshot/*` | apontar risco de N+1, custo e dados inconsistentes | deixar microotimizacao fora do review | ignorar gargalo estrutural evidente | 30-60 min | 4k-10k |
| V5 | Review da duplicacao de namespace de seguranca | `shared_support/defenses/*`, `shared_support/security/*` | apontar risco de drift, import incorreto e ownership nebuloso | aceitar compatibilidade transicional | deixar conflito de ownership passar em branco | 20-40 min | 3k-7k |

## Metricas obrigatorias

Meca estas cinco metricas continuamente:

| Metrica | O que mede | Formula simples | Meta inicial |
| --- | --- | --- | --- |
| `first-pass success rate` | quantas tarefas saem boas na primeira tentativa | tarefas aprovadas sem retrabalho / tarefas totais | `>= 55%` no inicio, `>= 70%` depois |
| `revisoes por tarefa` | quanta iteracao voce precisou fazer | total de rodadas / total de tarefas | `<= 2.5` |
| `tokens por tarefa simples` | desperdicio em trabalho pequeno | media de tokens em tarefas pequenas | cair 20% a cada ciclo de 30 dias |
| `tempo ate causa raiz no debug` | eficiencia investigativa | minutos ate primeira causa raiz comprovada | `<= 30 min` em bugs medios |
| `taxa de reuso de prompt` | maturidade da biblioteca | tarefas feitas com prompt reutilizado / total | `>= 60%` |

## Tabela de roteamento

Escolha modelo e modo assim:

| Tipo de trabalho | Modelo | Modo | Regra pratica |
| --- | --- | --- | --- |
| Arquitetura | modelo forte | Planning | quando mexe em fronteira, ownership ou corredor oficial |
| Debug | modelo forte | Planning | quando precisa provar causa raiz |
| Refator grande | modelo forte | Planning | quando mexe em varios arquivos ou contratos |
| UI ou CSS local | modelo rapido | Fast | quando o corte e visual e bem localizado |
| Produtividade curta | modelo rapido | Fast | renome, copy, ajuste simples, snippet curto |

Meta deste ciclo:

- parar de escolher modelo no feeling
- operar IA como tecnico que escala time, nao como jogador improvisando jogada

## Transformar aprendizado em sistema

Regra operacional:

- cada bug importante vira melhoria de prompt
- cada refator bom vira playbook
- cada falha vira guardrail
- cada acerto vira padrao reutilizavel

Arquivos fixos para consulta:

- `prompts/checklists/debug-checklist.md`
- `prompts/checklists/refactor-checklist.md`
- `prompts/checklists/frontend-checklist.md`
- `prompts/checklists/review-checklist.md`
- `prompts/checklists/technical-debt-good-vs-bad.md`

## Circuitos operacionais

Trabalhe por circuitos:

1. `Circuito de arquitetura`: define fronteira, ownership, corte e sequencia.
2. `Circuito de diagnostico`: localiza sintoma, evidencia e causa raiz.
3. `Circuito de entrega`: implementa o menor corte seguro.
4. `Circuito de validacao`: prova que comportamento, risco e objetivo ficaram corretos.
5. `Circuito de aprendizado`: transforma o que aconteceu em prompt, checklist ou playbook.

## Rotina semanal

| Dia | Foco |
| --- | --- |
| Segunda | arquitetura e decisoes de sistema |
| Terca | debug e causa raiz |
| Quarta | refator e debito tecnico |
| Quinta | front-end e UI ou UX |
| Sexta | review, seguranca e performance |
| Sabado | retro semanal e limpeza da biblioteca |
| Domingo | descanso ou revisao leve |

## Rotina diaria de 60-90 min

| Bloco | Tempo | O que fazer |
| --- | --- | --- |
| Escolha | 10 min | escolher 1 tarefa real do benchmark |
| Execucao | 20 min | rodar com o prompt atual |
| Revisao | 15 min | revisar saida com checklist |
| Ajuste | 10 min | corrigir o prompt |
| Registro | 10 min | registrar aprendizado, custo e resultado |
| Reuso | 10-20 min | transformar o aprendizado em ativo reutilizavel |

## Habitos que vao te levar para cima

- nunca confiar em resposta bonita sem validacao
- sempre pedir evidencia, arquivo, linha, risco e impacto
- separar tarefa simples de tarefa critica
- medir tokens em tarefas pequenas
- reusar o que funciona
- matar prompt ruim sem apego

## Sinais de que voce esta subindo de nivel

- voce comeca a prever onde a IA vai errar
- seus prompts ficam menores e melhores
- voce gasta menos tokens em tarefas simples
- suas correcoes ficam mais cirurgicas
- voce deixa de pedir ajuda e passa a orquestrar trabalho
