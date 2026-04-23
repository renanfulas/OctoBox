<!--
ARQUIVO: fechamento da revolucao UI/UX do app do aluno.

POR QUE ELE EXISTE:
- registra o estado final das ondas CORDA executadas no app do aluno.

O QUE ESTE ARQUIVO FAZ:
1. lista os checkpoints tecnicos fechados.
2. registra as metricas finais de template/CSS.
3. separa validacao automatizada de validacao de campo com alunos reais.
-->

# Student App UI Revolution Closeout

Data: 2026-04-23

## Contexto

A frente `/aluno/` saiu do modelo de painel explicado para uma ferramenta de acao rapida. O foco da rodada foi reduzir copy, baixar acoplamento de template/CSS, criar progresso real e mover as telas para dado pessoal primeiro.

## Ondas executadas

| Onda | Estado | Evidencia |
| --- | --- | --- |
| 0 - Baseline | Fechada | `docs/reports/student-app-ui-revolution-baseline.md` |
| 1 - Estrutura sem redesign | Fechada | `layout.html` com 40 linhas e CSS separado em `primitives/`, `shell/`, `screens/` |
| 2 - Contratos V2 | Fechada | `StudentAppActivity`, `StudentExerciseMaxHistory`, `primary_action`, `progress_days`, `rm_of_the_day` |
| 3 - Primitivos UI V2 | Fechada | `hero-number`, `primary-action`, `progress-strip`, `context-switch`, compact states |
| 4 - RM piloto | Fechada | `rm.html` com 12 linhas e composicao por partials |
| 5 - WOD | Fechada | hero de carga sugerida e blocos compactos com carga calculada |
| 6 - Home | Fechada | CTA unico por `primary_action` e `progress-strip` de 7 dias |
| 7 - Grade e settings | Fechada | abertura por proxima aula/perfil, sem page-head explicativo |
| 8 - Cleanup | Fechada | candidatos orfaos reduzidos a classes dinamicas/geradas pelo Django |
| 9 - Campo | Pendente humano | requer 5 alunos reais usando o app |

## Metricas finais

| Arquivo | Linhas | Palavras aproximadas |
| --- | ---: | ---: |
| `templates/student_app/home.html` | 64 | 226 |
| `templates/student_app/grade.html` | 52 | 178 |
| `templates/student_app/wod.html` | 111 | 287 |
| `templates/student_app/rm.html` | 12 | 52 |
| `templates/student_app/settings.html` | 43 | 141 |
| `templates/student_app/layout.html` | 40 | 114 |

## Validacao automatizada

Comandos executados:

```powershell
.\.venv\Scripts\python.exe manage.py test student_app
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py sync_runtime_assets --collectstatic
.\.venv\Scripts\python.exe manage.py check_static_drift --strict
git diff --check
```

Resultados:

- `student_app`: 49 testes, OK.
- `manage.py check`: sem issues.
- `check_static_drift --strict`: sem drift depois do sync.
- `git diff --check`: sem erro de whitespace; apenas avisos esperados de CRLF/LF do Git no Windows.
- `stylelint`: nao executado porque `node_modules/.bin/stylelint.cmd` nao esta instalado no workspace atual.

## Auditoria de cleanup

Removido com evidencia de nao uso:

- `student-page-head*`
- `student-card--soft`
- `student-insight-stack`
- `student-insight-pill`
- `student-home-grid`
- `student-rm-value`
- `student-rm-empty`
- `student-rm-preview`
- variantes pequenas/inline antigas sem uso

Mantido por geracao dinamica:

- `errorlist`, criado por Django forms.
- `student-flash--success`, `student-flash--error`, `student-flash--warning`, criadas por `message.tags`.

## Protocolo de campo

Para fechar a Onda 9, testar com 5 alunos reais em celular:

1. Abrir `/aluno/` e medir se a primeira acao util aparece em ate 20s.
2. Abrir `/aluno/wod/` com WOD publicado e confirmar se a primeira carga aparece sem explicacao verbal.
3. Abrir `/aluno/rm/` e confirmar se o RM relevante ou principal e entendido em ate 5s.
4. Pedir para o aluno explicar o ciclo Grade -> WOD -> RM sem o operador ensinar a tela.
5. Registrar se houve toque errado, hesitacao, scroll desnecessario ou pergunta de entendimento.

Meta de aceite de campo:

- 5/5 alunos encontram a acao primaria sem ajuda.
- 4/5 alunos entendem WOD/RM sem explicacao extra.
- 3/3 metas T5, T20 e T45 batidas no uso real.
