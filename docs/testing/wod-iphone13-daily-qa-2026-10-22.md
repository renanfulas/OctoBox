# WOD diário e simulação do Safari no iPhone 13 — 22/10/2026

## Ambiente e alcance

WebKit 26.4 do Playwright em Windows, perfil oficial **iPhone 13**: viewport
390 × 664, escala 3, contexto móvel, locale `pt-BR` e fuso `America/Sao_Paulo`.
PostgreSQL local em Docker e banco/schema de teste separados. O cache dos testes
Django é LocMemCache; o Redis local foi iniciado, mas não substitui esse backend
na configuração de testes.

A simulação usa o motor WebKit e o perfil móvel. Não executa iOS/UIKit: teclado,
seletor de data do sistema, permissões de colagem e interface do Safari físico
não são reproduzidos integralmente. No WebKit para Windows, a injeção de toque
é traduzida para eventos de mouse. Os testes verificam o alvo real, `isTrusted`,
foco e sincronização ao confirmar a edição; não comprovam a folha nativa do iOS.

## Problemas encontrados e corrigidos

| Problema | Reprodução / efeito | Correção |
|---|---|---|
| Carga decimal desaparecia ao editar | `40,50` era renderizado em `input[type=number]`, que ficava vazio; salvar novas repetições apagava a carga | `unlocalize` no valor HTML e regressão de edição preservando 40,50 kg |
| Autocomplete vazio em aula nova | O catálogo dependia de movimentos já existentes ou de RM dos alunos | Incluir o dicionário canônico e aliases não ambíguos, mantendo a prioridade dos dados de RM |
| Aviso de colagem transparente e sobreposto ao editor | A superfície global misturava uma cor com um token que contém gradiente; modal ficava dentro de superfícies com efeitos | Dialog nativo no body, superfície local válida, foco inicial no título e altura rolável |
| Aplicação por dia misturava modalidades | O endpoint aplicou em quatro aulas quando só uma deveria ser elegível | Modalidade explícita obrigatória, filtro de aulas ativas e de responsabilidade do coach |
| Coach acessava template/altera aula de outro coach | Filtro visual do calendário não era repetido na mutação diária nem no editor individual | Repetir os limites de autoria e responsabilidade no servidor, inclusive no preview de prescrição |
| Substituição afetava treinos publicados/pendentes | Modo overwrite removia os blocos sem proteger o estado | Substituir somente rascunhos; preservar publicado, pendente e rejeitado |
| Desfazer não recuperava o treino anterior | Título e blocos originais eram perdidos | Guardar antes/depois e restaurar conteúdo original com versão crescente |
| Desfazer apagava edições posteriores ou aceitava outro usuário | Token sem vínculo ao usuário e ausência de comparação do estado atual | Token por schema/usuário e comparação do lote inteiro antes de restaurar |
| Calendário permanecia desatualizado após aplicar | Toast de sucesso sem atualizar as células | Recarregar a grade após o sucesso, preservando a janela de desfazer no sessionStorage do contexto |

A aplicação diária permanece em rascunho: a publicação para os alunos continua
seguindo o fluxo de aprovação do box.

## Fluxos exercitados

- Calendário preenchido: três aberturas, com e sem `showPicker`, valor preservado,
  ano completo e ajuste de uma quarta-feira para a segunda correspondente.
- WOD individual: abrir a aula no calendário, criar cabeçalho, adicionar bloco,
  escolher movimento pelo nome, definir séries/repetições/carga, editar e enviar
  para aprovação. A modalidade vizinha e o dia seguinte permanecem intactos.
- Colagem diária: texto livre, aviso antes de gravar e confirmação explícita;
  conteúdo e quebras de linha preservados no caminho sem estrutura.
- Template diário: exigir modalidade, substituir rascunho, atualizar a célula,
  manter HYROX separado e restaurar o conteúdo anterior ao desfazer.
- Backend: autorização, conteúdo publicado/pendente protegido, edições
  posteriores preservadas, desfazer sem aplicação parcial e rollback do lote
  quando uma aplicação falha.

Evidências visuais locais: `tmp/visual_contract/iphone13/`.

## Resultados

- WebKit com perfil iPhone 13: **10 cenários passaram**, nos temas claro/escuro.
- Regressão existente do Smart Paste, calendário e app do aluno no Chromium:
  **47 cenários passaram**.
- Backend do editor, aplicação diária, regras e Smart Paste: **125 testes e
  9 subtests passaram**.
- Django check, sintaxe JavaScript, `git diff --check` e
  `check_static_drift --strict` passaram.

Comando da simulação móvel:

```powershell
.venv/Scripts/python.exe -m pytest tests/e2e/test_wod_iphone13.py --browser webkit --reuse-db --migrations --no-cov
```

## Limites

- A revisão não fez chamada real ao provedor de IA nem ao GPT externo. Exercitou
  a montagem manual e o fluxo de texto livre com confirmação/aprovação.
- A simulação não substitui a conferência final em Safari/iPhone 13 físico.
- As alterações são locais e precisam de publicação para chegar à produção.
