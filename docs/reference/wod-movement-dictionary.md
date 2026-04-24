# WOD Movement Dictionary

Dicionário canônico de movimentos para o parser de Smart Paste.

**Regras:**
- `slug` é o identificador técnico (snake_case, imutável).
- `aliases` são todas as formas que coaches usam em texto livre (PT-BR, EN, abreviações).
- Match é case-insensitive, ignora acentos.
- Parser L1 tenta match em ordem: alias exato → alias parcial → slug.
- Se nenhum alias bater, a linha vai para L2 (LLM) ou fica marcada "revisar".

---

## Formato

```
slug | aliases (separados por vírgula)
```

---

## Movimentos Olímpicos e Derivados

| slug | aliases |
|---|---|
| `power_snatch` | power snatch, p snatch, p.snatch, psnatch |
| `squat_snatch` | squat snatch, sqt snatch, full snatch, snatch |
| `hang_power_snatch` | hang power snatch, hang p snatch, hps |
| `overhead_squat` | overhead squat, ohs, ovh squat |
| `snatch_balance` | snatch balance, s balance, sn balance |
| `power_clean` | power clean, p clean |
| `squat_clean` | squat clean, sqt clean, clean |
| `hang_squat_clean` | hang squat clean, hang clean, h clean, hsc |
| `hang_power_clean` | hang power clean, hpc |
| `clean_and_jerk` | clean and jerk, c&j, cj |
| `push_jerk` | push jerk, p jerk |
| `split_jerk` | split jerk, s jerk |
| `push_press` | push press, pp, push pr |
| `shoulder_press` | shoulder press, press, strict press, sho press |
| `shoulder_to_overhead` | shoulder to overhead, s2oh, sto, s to oh |

---

## Ginástica / Calistenia

| slug | aliases |
|---|---|
| `pull_up` | pull up, pull-up, pullup, pu, c2b (chest to bar) |
| `strict_pull_up` | strict pull up, strict pu, str pull up |
| `chest_to_bar` | chest to bar, c2b, ctb |
| `bar_muscle_up` | bar muscle up, bmu, bar mu |
| `ring_muscle_up` | ring muscle up, rmu, ring mu |
| `push_up` | push up, push-up, flexão, flexao |
| `strict_push_up` | strict push up, str push up |
| `hollow_rock` | hollow rock, hollow body rock, hollow |
| `v_up` | v up, v-up, vup |
| `sit_up` | sit up, sit-up, situp, abdominal |
| `toes_to_bar` | toes to bar, t2b, toes 2 bar, toe to bar |
| `strict_toes_to_bar` | strict toes to bar, strict t2b, str t2b |
| `knees_to_elbow` | knees to elbow, k2e, kte |
| `handstand_push_up` | handstand push up, hspu, handstand pu, hpu |
| `strict_handstand_push_up` | strict handstand push up, strict hspu, str hspu |
| `handstand_walk` | handstand walk, hsw, hw |
| `ring_dip` | ring dip, rd |
| `bar_dip` | bar dip, dip |
| `rope_climb` | rope climb, rc, subida na corda, corda |
| `l_sit` | l sit, l-sit |
| `pistol_squat` | pistol squat, pistol, pistol sq |

---

## Levantamento / Força

| slug | aliases |
|---|---|
| `back_squat` | back squat, agachamento, squat, bs |
| `front_squat` | front squat, front sq, fs |
| `deadlift` | deadlift, dl, levantamento terra, terra |
| `romanian_deadlift` | romanian deadlift, rdl, stiff |
| `sumo_deadlift` | sumo deadlift, sumo dl |
| `bench_press` | bench press, supino, bench |
| `overhead_press` | overhead press, ohp |
| `lunge` | lunge, lunges, afundo, passada |
| `goblet_squat` | goblet squat, goblet |
| `thruster` | thruster, thrusters |
| `wall_ball` | wall ball, wb, wall boll |
| `dumbbell_snatch` | dumbbell snatch, db snatch, haltere snatch |
| `dumbbell_clean` | dumbbell clean, db clean |

---

## Kettlebell

| slug | aliases |
|---|---|
| `kettlebell_swing` | kettlebell swing, kbs, kb swing, swing |
| `kettlebell_swing_american` | kbs american, kbs a, kb swing americano, kbs am |
| `kettlebell_swing_russian` | kbs russian, kbs r, kb swing russo |
| `kettlebell_press` | kettlebell press, kb press |
| `turkish_get_up` | turkish get up, tgu, turco |
| `kettlebell_snatch` | kettlebell snatch, kb snatch |
| `kettlebell_clean` | kettlebell clean, kb clean |

---

## Cardio / Monoestrutural

| slug | aliases |
|---|---|
| `run` | run, corrida, rum, correr |
| `row` | row, remo, rower, rowing |
| `bike` | bike, bicicleta, assault bike, airbike |
| `ski` | ski, skierg, ski erg |
| `double_under` | double under, du, double-under |
| `single_under` | single under, su, pular corda |
| `burpee` | burpee, burpees, burpe |
| `burpee_over_bar` | burpee over bar, bob, burpee ob |
| `box_jump` | box jump, bj, salto no caixote |
| `box_jump_over` | box jump over, bjo, salto por cima |
| `step_up` | step up, step-up |
| `broad_jump` | broad jump, salto horizontal |
| `shuttle_run` | shuttle run, sr, vai e vem |
| `wall_walk` | wall walk, ww |
| `bear_crawl` | bear crawl, arrastar |

---

## Outros / Acessórios

| slug | aliases |
|---|---|
| `ghd_sit_up` | ghd sit up, ghd, ghd su |
| `back_extension` | back extension, be, extensão lombar |
| `plank` | plank, prancha |
| `superman` | superman |
| `band_pull_apart` | band pull apart, bpa |
| `face_pull` | face pull, fp |
| `hip_thrust` | hip thrust, ht |
| `glute_bridge` | glute bridge, gb, ponte glúteo |
| `calf_raise` | calf raise, panturrilha |
| `lateral_raise` | lateral raise, lr |
| `curl` | curl, rosca |
| `tricep_extension` | tricep extension, triceps, tríceps |

---

## Notas do parser

### Abreviações de carga

| Padrão no texto | Interpretação |
|---|---|
| `40/25` | carga masculino/feminino em kg |
| `65%` | porcentagem do RM |
| `70%` | porcentagem do RM |
| `Semana 2` | contexto de progressão (não é carga) |

### Formatos de set/rep

| Padrão | Significado |
|---|---|
| `3x` | 3 rounds do bloco |
| `7 rounds` | 7 rounds do bloco |
| `21/15/9` | formato piramidal (3 sub-rounds com reps decrescentes) |
| `Emom 20m` | Every Minute on the Minute, 20 minutos |
| `Amrap 16m` | As Many Rounds As Possible, 16 minutos |
| `A cada 30s por 15 x` | intervalo de 30s, 15 repetições |
| `10m`, `14m`, `15m` | timecap em minutos |

### Formato de letra para Emom

```
A 6 push jerk   → bloco A, 6 reps, movimento push jerk
B 10 a 12 t2b   → bloco B, 10-12 reps, movimento toes_to_bar
C 5 Hang clean  → bloco C, 5 reps, movimento hang_squat_clean
D 2 RC          → bloco D, 2 reps, movimento rope_climb
E rest          → bloco E, descanso (nenhum movimento)
```

### Aliases ambíguos

| Texto | Resolve para | Observação |
|---|---|---|
| `rum` | `run` | Erro de digitação comum (mobile BR) |
| `t2b` | `toes_to_bar` | Não confundir com `knees_to_elbow` |
| `bob` | `burpee_over_bar` | Contexto: "cada quebra 3 BOB" = penalidade |
| `rc` | `rope_climb` | Dentro de bloco Emom |
| `bjo` | `box_jump_over` | PT-BR abreviado |
| `bmu` / `25 pull up` | `bar_muscle_up` / `pull_up` | Separados por `/` = alternativa Rx vs scaled |
| `s balance` | `snatch_balance` | Abreviação de "snatch balance" |
| `kbs a` | `kettlebell_swing_american` | `a` = american, distingue de russian |
| `hspu` | `handstand_push_up` | `strict hspu` → `strict_handstand_push_up` |
| `wall boll` | `wall_ball` | Erro de digitação comum |

---

## Manutenção

- Adicionar novo slug: inserir linha na seção correta + adicionar aliases conhecidos.
- Nunca remover slug — marcar como `deprecated: true` e manter aliases para retrocompatibilidade.
- Novos aliases descobertos em revisões L2: adicionar aqui para que L1 resolva na próxima vez.
- Revisão trimestral: checar slugs sem aliases PT-BR e adicionar.
