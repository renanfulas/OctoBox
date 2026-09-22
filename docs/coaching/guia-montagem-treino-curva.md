<!--
ARQUIVO: guia operacional de como montar e publicar um treino no corredor
de consultoria individual (Curva Treino & Nutrição, app public_workouts).

TIPO DE DOCUMENTO:
- runbook operacional de coaching

AUTORIDADE:
- alta pra dúvidas de "como montar treino pra um cliente da Curva" —
  runtime real (schema.py/periodization.py/services.py) sempre vence se
  este doc ficar desatualizado, mas até lá é a referência rápida.

QUANDO USAR:
- ao montar um programa de treino novo (ou nova versão) pra um cliente
  do corredor public_workouts (ex.: Bruno, Juliana, Isabelle) — NÃO o
  CrossFit do OctoBox principal (isso é docs/coaching/guia-de-prescricao.md).

POR QUE ELE EXISTE:
- achado real: sem este runbook, montar um treino novo significou
  redescobrir cada peça na marra — ler schema.py do zero pra entender o
  formato do payload, copiar a estrutura de outro aluno por tentativa, e
  buscar cada exercício no MuscleWiki individualmente sem saber que já
  existia um banco de slugs verificados. Este doc existe pra eliminar essa
  re-exploração.

O QUE ESTE ARQUIVO FAZ:
1. define o passo a passo de montar um treino, do dado bruto até publicado
2. documenta o formato do payload PublicWorkoutProgram e do modelo canônico
   de periodização
3. mantém um banco de slugs do MuscleWiki já verificados, reutilizável
4. documenta a fórmula de composição corporal por dobras cutâneas
-->

# Como montar um treino no corredor Curva (public_workouts)

> Contraparte deste app pro CrossFit do OctoBox principal:
> [guia-de-prescricao.md](./guia-de-prescricao.md) (domínio diferente, não confundir).
> Conhecimento científico de treino (hipertrofia, periodização, biomecânica)
> vive na skill do projeto `.claude/skills/expert-ef/SKILL.md` — este doc é
> o complemento operacional, focado em COMO publicar de verdade no sistema.

## O padrão atual: payload, não HTML por aluno

Até uma fase anterior do produto, cada aluno tinha sua própria página HTML
estática (`templates/public_workouts/<slug>.html` + entrada em
`PUBLIC_WORKOUT_LIBRARY`, `student_app/views/public_workout_views.py`).
**Isso foi substituído por um template ÚNICO e universal**
(`templates/public_workouts/workout.html`) que renderiza um **payload de
dados** (`dict` Python no formato de `public_workouts/schema.py`) — nunca
HTML por aluno. Os arquivos `.html` por aluno que ainda existem são material
de migração absorvendo o legado, não o molde a seguir.

Se alguma outra referência (incluindo uma skill externa não versionada
neste repositório, tipo `expert-treino-pwa`) disser pra copiar um template
HTML e montar uma página nova por aluno, **ignore** — é o padrão antigo.
A fonte de verdade sobre como publicar é este documento + `schema.py`.

## Passo a passo

1. **Reúna os dados** do aluno (pergunte o que faltar): nome, idade,
   objetivo, nível de treino, dias/semana disponíveis, onde treina
   (academia completa? equipamento limitado?), restrições físicas, e
   qualquer avaliação física/adipometria já feita.

2. **Se vier adipometria (7 dobras) + idade, calcule o %GC** — fórmula na
   seção "Composição corporal" abaixo. Sem idade não dá pra calcular.

3. **Avalie/proponha a divisão de treino** aplicando os princípios de
   frequência (2x/semana por grupo é o mínimo eficaz bem estabelecido —
   com poucos dias de treino/semana, full body geralmente bate divisão por
   segmento corporal), volume dentro de MEV-MRV pro nível do atleta,
   seleção de exercício por SFR (ver `expert-ef/SKILL.md` pra
   fundamentação científica completa). Dê uma opinião fundamentada mesmo
   que o usuário não peça, antes de simplesmente montar em cima do que foi
   passado.

4. **Verifique os exercícios no MuscleWiki** — comece pelo banco de slugs
   verificados abaixo. Só pesquise um exercício novo se ele não estiver lá.

5. **Monte o payload Python** no formato documentado abaixo (espelha
   `public_workouts/schema.py` — `validate_payload`/`assert_valid_payload`
   são a fonte de verdade, este doc é só a referência rápida).

6. **Rode o protocolo de acentuação** (grep + releitura manual, seção
   abaixo) em cima do texto visível do payload antes de considerar pronto.

7. **Valide**: `public_workouts.schema.validate_payload(payload)` precisa
   devolver lista vazia antes de publicar.

8. **Teste renderizado antes de publicar de verdade**: rode local
   (`python manage.py runserver`) e abra `/renan/<slug>/preview-b3`
   (`PublicWorkoutTemplatePreviewView`) — renderiza `workout.html` contra
   o payload sem precisar de conta/cookie, só existe com `DEBUG=True`.

9. **Publique**: `public_workouts.services.publish_program(slug=..., payload=payload)`.
   Cria uma versão nova e ativa automaticamente, nunca edita a anterior
   in-place. Isso NÃO exige nenhuma `PublicWorkoutAccount`/
   `PublicWorkoutSubscription` existir antes — o programa fica acessível
   em `/renan/<slug>` imediatamente (mesmo fluxo de "cookie de posse" que
   os clientes legados usam), mesmo sem o e-mail do aluno ainda. Conectar
   o login por e-mail é um passo independente e posterior.

10. **Confirme em produção com `curl -sI` (sem cookie nenhum)** antes de
    testar no navegador: deve devolver `200`. Testar no navegador logo
    depois de ter usado outras contas na mesma sessão (outro aluno já
    logado) pode mostrar um 404 falso — é o cookie de sessão de OUTRA
    conta bloqueando por posse (nunca revela via 403, vira 404 mesmo
    sendo só cookie cruzado, ver `_confirm_ownership_or_404` em
    `student_app/views/public_workout_views.py`). `curl` sem cookie é a
    fonte da verdade nesse caso.

11. Rode a suíte antes de considerar o trabalho fechado:
    `pytest public_workouts/ student_app/tests.py -q --create-db --migrations`.

## Formato do payload (`public_workouts/schema.py`)

Estrutura de alto nível:

```python
{
    'schema_version': 1,                       # schema.SCHEMA_VERSION
    'program_id': 'nome-atleta-2026-qN',        # único, versionado (publish_program incrementa version se reusar program_id)
    'program_label': 'Texto que aparece pro aluno',
    'started_on': '2026-09-19',                 # ISO date
    'weeks': 8,                                 # duração em semanas, pra exibição ("Programa · N semanas")
    'accent_variant': 'F',                      # 'F' / 'M' / None
    'days': [
        {
            'day_id': 'seg',                    # curto, usado internamente
            'label': 'Full Body A',             # o que aparece na aba do dia
            'blocks': [
                {'movements': [ { ... um movimento ... } ]},
                # um block por exercício é o padrão comum (não precisa agrupar)
            ],
        },
        # ... um dict por dia de treino
    ],
    'cardio': { ... },           # opcional
    'periodization': { ... },    # opcional, ver seção própria abaixo
}
```

Cada **movimento**:

```python
{
    'name': 'Agachamento goblet com halter',   # português, o que aparece na tela
    'movement_slug': 'dumbbell-goblet-squat',  # do MuscleWiki quando tem link; senão slugify(nome)
    'reps_spec': '2× Prep → 1× Feeder → 2× Top (12-15)',  # texto livre; padrão N× <Fase> (min-max) vira chip colorido sozinho
    'rir_spec': 'RIR 3-4 · nota curta opcional de execução',
    'is_tracked': True,             # True = aluno registra carga (histórico + sugestão de progressão automáticos)
    'load_type': 'free',            # 'free' / 'fixed_kg' / 'percentage_of_rm'
    'load_value': None,             # número quando load_type != 'free'
    'reference_url': 'https://musclewiki.com/exercise/dumbbell-goblet-squat',  # ou None
    # 'variations': [{'label': ..., 'reference_url': ...}],  # opcional
}
```

Trabalho de aquecimento/mobilidade que não é um exercício de verdade nem
cardio: vira um `movement` normal e leve, `is_tracked=False`,
`load_type='free'`, `reference_url=None`, com o texto todo dentro de
`reps_spec` (não existe campo separado de "nota do dia" — se não é
prescrição de exercício nem sessão de cardio, não força um encaixe).

Fases reconhecidas dentro de `reps_spec` (viram chip colorido automático):
**Prep** (aquecimento progressivo), **Feeder** (1 série de calibração,
RIR 4-5), **Top** (trabalho de verdade), **Max**/**AMRAP** (opcional, mede
progressão).

## Periodização (`payload['periodization']`, opcional)

Modelo canônico **já implementado**
(`public_workouts/periodization.py::PHASE_PROFILES`) — vocabulário
FECHADO de 8 fases, cada uma com %1RM/RIR/reps vindos de literatura real
(NSCA/Prilepin/Bompa/Helms). Nunca invente uma nona fase — se o objetivo
genuinamente não encaixa em nenhuma das 8, é sinal de que o modelo precisa
crescer; proponha isso explicitamente em vez de inventar um rótulo solto.

| `phase_type` | Label | %1RM | RIR alvo | Reps alvo |
|---|---|---|---|---|
| `adaptation` | Adaptação | 50-62% | 3,5 | 12-15 |
| `volume` | Volume | 62-72% | 2,5 | 8-12 |
| `strength_hypertrophy` | Força-Hipertrofia | 72-80% | 1,5 | 6-8 |
| `intensity` | Intensidade | 80-90% | 0,5 | 3-6 |
| `peak` | Pico | 90-97% | 0 | 1-3 |
| `deload` | Deload | 50-65% | 4,5 | 8-10 |
| `maintenance` | Manutenção | 67-80% | 1,5 | 6-10 |
| `test` | Teste | 85-95% | 0 | 1-5 |

Formato mínimo:

```python
'periodization': {
    'weeks': [
        {'phase_type': 'adaptation', 'week_number': 1},
        {'phase_type': 'adaptation', 'week_number': 2},
        # ... uma linha por semana do mesociclo
    ],
    'note': 'Texto em pt-BR explicando a lógica da progressão pro aluno.',
    'volume_table': [
        {'muscle_group': 'Quadríceps', 'sets_per_week': '~6 séries', 'frequency': '2x/semana', 'where': 'Segunda + Quarta'},
        # ... uma linha por grupo muscular; as 4 chaves são obrigatórias, todas string
    ],
}
```

Com `weeks` (canônico) presente, o formato legado (`weeks_table` + `chart`
manuais, ainda usado pelos clientes antigos nunca migrados) fica opcional —
o template já desenha o gráfico de barras e o banner "Semana X de Y · Fase"
sozinho a partir de `weeks`.

## Banco de slugs MuscleWiki já verificados

Forma canônica sempre `https://musclewiki.com/exercise/<slug>`. Reutilize
sem buscar de novo. **Adicione aqui** qualquer slug novo que confirmar.

Protocolo de verificação completo (busca antes de adivinhar, `WebFetch`
pode devolver `403` nesse domínio — quando bloquear todas as tentativas,
aceite confirmação por título de busca "... Exercise Guide - ... Workout |
MuscleWiki" batendo com o formato canônico da URL) está em
`.claude/skills/expert-ef/SKILL.md`.

**Pernas / glúteo:** `barbell-squat` · `dumbbell-goblet-squat` ·
`machine-leg-press` · `machine-leg-extension` · `barbell-romanian-deadlift` ·
`dumbbell-romanian-deadlift` · `machine-seated-leg-curl` ·
`machine-hamstring-curl` · `barbell-hip-thrust` · `dumbbell-hip-thrust` ·
`machine-standing-calf-raises` · `machine-horizontal-leg-press-calf-raise` ·
`dumbbell-bulgarian-split-squat` · `dumbbell-goblet-bulgarian-split-squat` ·
`machine-hack-squat`

**Peito / costas / ombro:** `barbell-bench-press` · `dumbbell-bench-press` ·
`dumbbell-incline-bench-press` · `machine-pulldown` ·
`machine-assisted-pull-up` · `barbell-bent-over-row` ·
`machine-seated-cable-row` · `barbell-overhead-press` ·
`dumbbell-overhead-press` · `dumbbell-neutral-seated-overhead-press` ·
`dumbbell-seated-overhead-press` · `cable-low-single-arm-lateral-raise` ·
`cable-low-bilateral-lateral-raise`

**Braço:** `cable-bar-curl` · `dumbbell-preacher-curl` ·
`dumbbell-hammer-curl` · `cable-rope-pushdown` · `cable-bar-pushdown` ·
`dumbbell-skullcrusher` · `cable-rope-skullcrusher` ·
`dumbbell-overhead-tricep-extension`

**Abdômen:** `forearm-plank` · `dead-bug`

## Composição corporal — dobras cutâneas (Jackson-Pollock 7 dobras)

Com as 7 dobras (peitoral/chest, axilar/midaxillary, tríceps, subescapular,
abdômen, ilíaca/suprailíaca, coxa) + idade, calcule direto:

```python
soma7 = peitoral + axilar + triceps + subescapular + abdomen + iliaca + coxa  # mm

# Densidade corporal (Db) — fórmula muda por sexo:
# Mulher (Jackson, Pollock & Ward 1980):
Db = 1.0970 - 0.00046971 * soma7 + 0.00000056 * soma7**2 - 0.00012828 * idade
# Homem (Jackson & Pollock 1978):
Db = 1.112 - 0.00043499 * soma7 + 0.00000055 * soma7**2 - 0.00028826 * idade

# Siri (1961) — converte densidade em %GC, mesma fórmula pros dois sexos:
percentual_gc = (495 / Db) - 450
```

Exige idade — sem ela não dá pra calcular. Cheque o resultado contra a
faixa plausível antes de reportar: mulheres treinadas ~14-20%, fitness
~21-24%, média ~25-31%; homens treinados ~6-13%, fitness ~14-17%, média
~18-24%. Número muito fora disso, re-confira a conta.

## Protocolo de acentuação

Rode antes de considerar QUALQUER payload pronto (criação ou edição):

1. **Grep de primeira passada:**
   ```
   grep -Eio '\b(nao|voce|atencao|periodizacao|disponivel|disponiveis|gluteo|gluteos|quadriceps|exercicio|exercicios|tecnica|tecnico|habito|historico|unico|unica|orgao|maximo|minimo|medio|rapido|facil|dificil|ultimo|ultima|musculo|musculos|biceps|triceps|flexao|extensao|rotacao|resistencia|execucao|repeticao|repeticoes|serie|series|frequencia|periodo|evolucao|avaliacao|circunferencia|sessao|sessoes|horario|duracao|articulacao|padrao|padroes|dicionario|continua|forca|so|ja|esta|pe|pes|chao|bulgaro|cientifica|maquina|versao|referencia|proporcao|direcao|elevacao|pelvica|pelvico|dobradica|estacionario|frances|coordenacao|adaptacao|tensao|ativacao|correcao)\b' <arquivo>
   ```
   Trate cada acerto como suspeito, não confirmado — `so`/`esta`/`ja`/`e`
   têm forma correta SEM acento em outro sentido gramatical (ler a frase
   antes de trocar).
2. **Releitura completa manual** — o grep tem buracos conhecidos (já
   deixou passar "avanço", "pé", "chão", "francês", "estacionário" numa
   sessão real). Leia o texto visível do payload do início ao fim depois
   do grep.
3. **Nunca acentue identificadores** — `movement_slug`, `day_id`, chaves
   do dict são ASCII de propósito. Só o VALOR de texto que o aluno lê
   (`name`, `reps_spec`, `rir_spec`, `note`, `title`, `label`, `guidance`)
   leva acento.
4. Depois de corrigir, revalide com `schema.validate_payload(payload)` e
   rode a suíte antes de publicar de verdade.
