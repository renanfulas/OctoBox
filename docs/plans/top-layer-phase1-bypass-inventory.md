<!--
ARQUIVO: inventario de bypasses remanescentes da Fase 1 do Center Layer.

POR QUE ELE EXISTE:
- registra de forma explicita onde a borda ainda atravessa para dentro demais.
- separa o que ja foi corrigido do que segue como bypass consciente.
- fecha a parte documental da Fase 1 sem esconder excecoes.

TIPO DE DOCUMENTO:
- inventario tecnico de fronteiras

AUTORIDADE:
- media para acompanhamento da Fase 1

DOCUMENTO PAI:
- [top-layer-phase1-center-layer-task-breakdown.md](top-layer-phase1-center-layer-task-breakdown.md)

PONTOS CRITICOS:
- este documento nao autoriza novos bypasses.
- um item listado aqui deve sair por promoted facade, adapter fino ou justificativa formal.
-->

# Inventario de bypasses remanescentes da Fase 1

## Estado atual

1. `catalog/views/student_views.py` deixou de importar `students.infrastructure.source_capture_links` diretamente.
2. a captura declarada de origem agora sobe pela fronteira publica de `students.facade`.
3. `catalog/views/` deixou de importar `reporting.infrastructure.build_report_response` diretamente.
4. exportacoes de relatorio agora sobem por `reporting.facade`.

## Resolvidos nesta onda

### 1. token de captura declarada em alunos

**Antes**

1. [../../catalog/views/student_views.py](../../catalog/views/student_views.py) importava:
2. `students.infrastructure.source_capture_links.build_student_source_capture_token`
3. `students.infrastructure.source_capture_links.read_student_source_capture_token`

**Agora**

1. [../../catalog/views/student_views.py](../../catalog/views/student_views.py) usa:
2. `students.facade.run_student_source_capture_token_build`
3. `students.facade.run_student_source_capture_token_read`

**Leitura arquitetural**

1. a borda HTTP voltou a passar pela porta oficial do app `students`.
2. o detalhe tecnico de assinatura continua em `infrastructure`, mas escondido atras da facade.

## Remanescentes conscientes

1. nenhum bypass de `reporting.infrastructure` permanece em `catalog/views/` depois desta onda.
2. futuros consumidores de exportacao HTTP devem preferir `reporting.facade`.

## Regra para os proximos passos

1. nenhum novo import de `*.infrastructure` deve entrar em `catalog/views/` sem justificativa formal.
2. se a borda precisar de comportamento de outro app, a preferencia e:
3. `facade publica` -> `service de compatibilidade fino` -> `bypass explicitamente inventariado`.
