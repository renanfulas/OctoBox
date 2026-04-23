<!--
ARQUIVO: baseline da revolucao UI/UX do app do aluno.

POR QUE ELE EXISTE:
- registra o estado anterior as ondas de refactor para comparacao objetiva.

O QUE ESTE ARQUIVO FAZ:
1. fixa metricas textuais iniciais dos templates core.
2. registra tamanho inicial dos CSS do app do aluno.
3. guarda o primeiro resultado de teste antes das mudancas.
-->

# Student App UI Revolution Baseline

Data: 2026-04-23

## Templates

| Arquivo | Linhas | Palavras aproximadas |
| --- | ---: | ---: |
| `templates/student_app/home.html` | 181 | 1022 |
| `templates/student_app/grade.html` | 79 | 405 |
| `templates/student_app/wod.html` | 158 | 670 |
| `templates/student_app/rm.html` | 61 | 355 |
| `templates/student_app/settings.html` | 74 | 349 |
| `templates/student_app/layout.html` | 264 | 1431 |

## CSS

| Arquivo | Bytes |
| --- | ---: |
| `static/css/student_app/app.css` | 804 |
| `static/css/student_app/components.css` | 22403 |
| `static/css/student_app/forms.css` | 5254 |
| `static/css/student_app/pages.css` | 3240 |
| `static/css/student_app/shell.css` | 20517 |

## Teste inicial

Comando:

```powershell
.\.venv\Scripts\python.exe manage.py test student_app
```

Resultado: 48 testes, OK.

## Nota visual

Screenshots reais dependem de sessao autenticada e servidor local com dados de aluno. Este baseline textual serve como trava inicial automatizavel; os screenshots devem ser capturados na validacao visual de cada onda quando houver ambiente autenticado disponivel.
