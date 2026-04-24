<!--
ARQUIVO: inventario Wave 0 da revolucao UI/UX do corredor WOD.

TIPO DE DOCUMENTO:
- baseline operacional e tecnico antes de alteracao visual

AUTORIDADE:
- alta para comparacao das ondas seguintes do corredor /operacao/wod/*

DOCUMENTO PAI:
- [wod-ui-ux-revolution-corda.md](wod-ui-ux-revolution-corda.md)

QUANDO USAR:
- antes de iniciar Onda 1, Onda 2 ou qualquer refatoracao visual no corredor WOD
- para comparar reducao de template, CSS e rotas depois das ondas

PONTOS CRITICOS:
- este inventario nao autoriza delete de CSS por si so
- runtime, testes e tela real continuam vencendo quando houver divergencia
-->

# Wave 0 - Inventario do corredor WOD

Data base: 2026-04-23.

## Escopo medido

Corredor WOD operacional:

1. `templates/operations/workout_approval_board.html`
2. `templates/operations/workout_editor_home.html`
3. `templates/operations/coach_session_workout_editor.html`
4. `templates/operations/workout_publication_history.html`
5. `templates/operations/includes/wod_corridor_tabs.html`
6. `templates/operations/includes/wod_publication_history_content.html`
7. `templates/operations/includes/wod_publication_history_filters.html`
8. `static/css/design-system/operations/dev-coach/coach.css`
9. `operations/urls.py`
10. `operations/workout_action_views.py`

## Baseline de templates

| Arquivo | Linhas |
|---|---:|
| `templates/operations/workout_approval_board.html` | 329 |
| `templates/operations/workout_editor_home.html` | 37 |
| `templates/operations/coach_session_workout_editor.html` | 383 |
| `templates/operations/workout_publication_history.html` | 17 |
| `templates/operations/includes/wod_corridor_tabs.html` | 13 |
| `templates/operations/includes/wod_publication_history_content.html` | 545 |
| `templates/operations/includes/wod_publication_history_filters.html` | 33 |
| **Total** | **1357** |

## Baseline de rotas

Rotas atuais relacionadas ao corredor WOD: **10**.

1. `operacao/wod/editor/`
2. `operacao/coach/aula/<session_id>/wod/`
3. `operacao/wod/aprovacoes/`
4. `operacao/wod/historico/`
5. `operacao/wod/<workout_id>/aluno/<student_id>/rm/<exercise_slug>/`
6. `operacao/wod/aprovacoes/checkpoint-semanal/`
7. `operacao/wod/<workout_id>/follow-up/`
8. `operacao/wod/<workout_id>/rm-gap/`
9. `operacao/wod/<workout_id>/memory/`
10. `operacao/wod/<workout_id>/<action>/`

## Baseline de CSS

Arquivo medido: `static/css/design-system/operations/dev-coach/coach.css`.

| Metrica | Valor |
|---|---:|
| Linhas totais do arquivo | 1886 |
| Seletores unicos `.coach-wod-*` | 83 |
| Ocorrencias textuais `coach-wod-` no CSS | 335 |

Leitura: o corredor ainda depende fortemente de uma familia local `coach-wod-*`. Isso nao e erro automatico, mas e sinal de que a Onda 7 precisa migrar autoridade para tokens, cards, pills e componentes canonicos antes de remover regras.

## Frontend forensics

Comando executado:

```powershell
.\.venv\Scripts\python.exe .\.agents\skills\octobox-ui-cleanup-auditor\scripts\frontend_forensics.py --base-path . --report tmp\wod_wave0_frontend_forensics.json
```

Resumo global do scan:

| Achado | Valor |
|---|---:|
| Regras `!important` | 20 |
| Atributos `style=""` inline | 160 |
| Blocos `<style>` em templates | 8 |
| Arquivos residuais de backup | 0 |
| Seletores duplicados | 5857 |
| Override hotspots | 3653 |
| Ocorrencias de familias legadas | 240 |
| Seletores candidatos a nao uso | 197 |

Artefato gerado:

```text
tmp/wod_wave0_frontend_forensics.json
```

## Telemetria adicionada na Wave 0

Arquivo alterado:

```text
operations/workout_action_views.py
```

Evento emitido:

```text
wod_action_duration_ms
```

Atributos:

1. `action`
2. `workout_id`
3. `user_id`
4. `duration_ms`

Acoes instrumentadas:

1. `approval.approve`
2. `approval.reject`
3. `follow_up`
4. `operational_memory`
5. `weekly_checkpoint`
6. `rm_gap`

Toggle de seguranca:

```text
WOD_ACTION_TELEMETRY_ENABLED=True|False
WOD_ACTION_TELEMETRY_SAMPLE_RATE=0.0..1.0
```

Logger:

```text
octobox.operations.wod
```

Observacao importante: a amostragem historica de 100 eventos reais ainda nao existia antes desta Wave 0. Portanto, o baseline de tempo medio atual deve ser coletado em staging apos a instrumentacao receber trafego real. A partir de agora, a medicao passa a existir.

## Resultado da Wave 0

1. UI nao foi alterada.
2. Baseline visual e estrutural foi registrado.
3. Telemetria de duracao das actions WOD foi adicionada com toggle por settings/env.
4. Proximas ondas podem comparar reducao de linhas, reducao de CSS `coach-wod-*` e queda de tempo de aprovacao.

## Guardrail para Onda 1

Nao remover copy permanente antes de validar se ela e apenas explicativa ou se carrega contrato de produto.

Metafora simples: copy explicativa e como etiqueta em brinquedo. Se a etiqueta so fala "aperte aqui", podemos trocar por um icone. Se a etiqueta avisa "nao coloque na tomada", ela precisa continuar visivel ou virar aviso melhor.
