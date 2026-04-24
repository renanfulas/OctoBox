# WOD Paste Schema

Schema JSON canônico produzido pelo parser (L1 e L2). Ambas as camadas devolvem exatamente esta estrutura. Validado com Pydantic.

---

## Schema completo

```json
{
  "week_label": "string | null",
  "parse_warnings": [
    {
      "line_number": "integer",
      "line_text": "string",
      "message": "string"
    }
  ],
  "days": [
    {
      "weekday": "0-6 (0=seg, 1=ter, 2=qua, 3=qui, 4=sex, 5=sab, 6=dom)",
      "weekday_label": "string (Segunda, Terça, ...)",
      "blocks": [
        {
          "kind": "warmup | skill | metcon | cooldown | mobility | custom",
          "title": "string | null",
          "notes": "string | null",
          "timecap_min": "integer | null",
          "rounds": "integer | null",
          "interval_seconds": "integer | null",
          "score_type": "for_time | amrap | emom | rounds_reps | load | null",
          "format_spec": "string | null",
          "movements": [
            {
              "movement_slug": "string | null",
              "movement_label_raw": "string",
              "sets": "integer | null",
              "reps_spec": "string | null",
              "load_spec": "string | null",
              "load_rx_male_kg": "float | null",
              "load_rx_female_kg": "float | null",
              "load_percentage_rm": "float | null",
              "emom_label": "string | null",
              "notes": "string | null",
              "is_scaled_alternative": "boolean",
              "sort_order": "integer"
            }
          ],
          "sort_order": "integer"
        }
      ]
    }
  ]
}
```

---

## Definição dos campos

### Nível raiz

| Campo | Tipo | Descrição |
|---|---|---|
| `week_label` | string? | Rótulo humano da semana se presente no texto (ex: "Semana 2") |
| `parse_warnings` | array | Linhas que não foram resolvidas com confiança; nunca array vazio omitido |
| `days` | array | Um item por dia da semana encontrado no texto |

### `parse_warnings[]`

| Campo | Tipo | Descrição |
|---|---|---|
| `line_number` | int | Número da linha no texto original (1-indexed) |
| `line_text` | string | Texto exato da linha |
| `message` | string | Motivo: "movimento não reconhecido", "formato de carga ambíguo", etc. |

### `days[]`

| Campo | Tipo | Descrição |
|---|---|---|
| `weekday` | int | 0=segunda … 6=domingo |
| `weekday_label` | string | "Segunda", "Terça", etc. |
| `blocks` | array | Blocos do dia em ordem de aparição |

### `blocks[]`

| Campo | Tipo | Valores possíveis | Descrição |
|---|---|---|---|
| `kind` | string | `warmup`, `skill`, `metcon`, `cooldown`, `mobility`, `custom` | Tipo do bloco |
| `title` | string? | — | Título livre (ex: "Semana 2", "Duplas") |
| `notes` | string? | — | Notas do bloco (ex: "Cada quebra 3 BOB", "um round para cada") |
| `timecap_min` | int? | — | Timecap em minutos (ex: 10, 14, 15) |
| `rounds` | int? | — | Número de rounds fixo (ex: 3, 7, 6) |
| `interval_seconds` | int? | — | Intervalo de Emom em segundos (ex: 60 para Emom, 30 para a-cada-30s) |
| `score_type` | string? | `for_time`, `amrap`, `emom`, `rounds_reps`, `load`, null | Como o WOD é pontuado |
| `format_spec` | string? | — | Formato livre (ex: "21/15/9", "5 rounds", "a cada 30s por 15x") |
| `movements` | array | — | Movimentos do bloco |
| `sort_order` | int | — | Ordem de aparição, 0-indexed |

**Mapeamento kind → cabeçalho no texto:**

| Texto (case-insensitive) | kind |
|---|---|
| Mobilidade | `mobility` |
| Aquecimento | `warmup` |
| Skill | `skill` |
| Wod, WOD | `metcon` |
| Cooldown, Descanso ativo | `cooldown` |
| (texto livre não mapeado) | `custom` |

### `movements[]`

| Campo | Tipo | Descrição |
|---|---|---|
| `movement_slug` | string? | Slug canônico do dicionário (`wod-movement-dictionary.md`). `null` se não resolvido. |
| `movement_label_raw` | string | Texto exato como o coach escreveu. Sempre preservado. |
| `sets` | int? | Número de sets explícitos (raro — geralmente herdado do bloco) |
| `reps_spec` | string? | String de reps como aparece no texto: "10", "10 a 12", "21/15/9", "1" |
| `load_spec` | string? | String de carga como aparece no texto: "40/25", "65%", "70%" |
| `load_rx_male_kg` | float? | Extraído de `load_spec` se formato `N/M` — valor masculino |
| `load_rx_female_kg` | float? | Extraído de `load_spec` se formato `N/M` — valor feminino |
| `load_percentage_rm` | float? | Extraído de `load_spec` se formato `N%` — ex: 65.0, 70.0 |
| `emom_label` | string? | Letra do Emom: "A", "B", "C", "D", "E" (null se não for Emom) |
| `notes` | string? | Notas específicas do movimento |
| `is_scaled_alternative` | bool | `true` se este movimento é alternativa scaled (ex: "25 pull up" em "15 bmu / 25 pull up") |
| `sort_order` | int | Ordem de aparição, 0-indexed |

---

## Exemplos

### Exemplo 1 — Bloco Aquecimento simples

Texto:
```
Aquecimento
3x
10 lunges
8 front squat
20 sit up
```

JSON:
```json
{
  "kind": "warmup",
  "title": null,
  "rounds": 3,
  "timecap_min": null,
  "score_type": null,
  "format_spec": "3x",
  "movements": [
    {
      "movement_slug": "lunge",
      "movement_label_raw": "10 lunges",
      "reps_spec": "10",
      "sort_order": 0
    },
    {
      "movement_slug": "front_squat",
      "movement_label_raw": "8 front squat",
      "reps_spec": "8",
      "sort_order": 1
    },
    {
      "movement_slug": "sit_up",
      "movement_label_raw": "20 sit up",
      "reps_spec": "20",
      "sort_order": 2
    }
  ],
  "sort_order": 1
}
```

### Exemplo 2 — Bloco Emom

Texto:
```
Skill
Emom 20m
A 6 push jerk
B 10 a 12 t2b
C 5 Hang clean
D 2 RC
E rest
```

JSON:
```json
{
  "kind": "skill",
  "title": null,
  "timecap_min": 20,
  "interval_seconds": 60,
  "score_type": "emom",
  "format_spec": "Emom 20m",
  "movements": [
    {
      "movement_slug": "push_jerk",
      "movement_label_raw": "A 6 push jerk",
      "emom_label": "A",
      "reps_spec": "6",
      "sort_order": 0
    },
    {
      "movement_slug": "toes_to_bar",
      "movement_label_raw": "B 10 a 12 t2b",
      "emom_label": "B",
      "reps_spec": "10 a 12",
      "sort_order": 1
    },
    {
      "movement_slug": "hang_squat_clean",
      "movement_label_raw": "C 5 Hang clean",
      "emom_label": "C",
      "reps_spec": "5",
      "sort_order": 2
    },
    {
      "movement_slug": "rope_climb",
      "movement_label_raw": "D 2 RC",
      "emom_label": "D",
      "reps_spec": "2",
      "sort_order": 3
    },
    {
      "movement_slug": null,
      "movement_label_raw": "E rest",
      "emom_label": "E",
      "notes": "descanso",
      "reps_spec": null,
      "sort_order": 4
    }
  ],
  "sort_order": 1
}
```

### Exemplo 3 — Metcon com alternativa scaled

Texto:
```
Wod  14m
1.200 run
60 bjo
40 wall boll
15 bmu / 25 pull up
```

JSON:
```json
{
  "kind": "metcon",
  "title": null,
  "timecap_min": 14,
  "score_type": "for_time",
  "format_spec": null,
  "movements": [
    {
      "movement_slug": "run",
      "movement_label_raw": "1.200 run",
      "reps_spec": "1.200",
      "notes": "1200m",
      "sort_order": 0
    },
    {
      "movement_slug": "box_jump_over",
      "movement_label_raw": "60 bjo",
      "reps_spec": "60",
      "sort_order": 1
    },
    {
      "movement_slug": "wall_ball",
      "movement_label_raw": "40 wall boll",
      "reps_spec": "40",
      "sort_order": 2
    },
    {
      "movement_slug": "bar_muscle_up",
      "movement_label_raw": "15 bmu",
      "reps_spec": "15",
      "is_scaled_alternative": false,
      "sort_order": 3
    },
    {
      "movement_slug": "pull_up",
      "movement_label_raw": "25 pull up",
      "reps_spec": "25",
      "is_scaled_alternative": true,
      "sort_order": 4
    }
  ],
  "sort_order": 3
}
```

### Exemplo 4 — Metcon com penalidade em notas

Texto:
```
Wod
10m
21/15/9

Thruster
Pull up

Cada quebra 3 BOB
```

JSON:
```json
{
  "kind": "metcon",
  "title": null,
  "timecap_min": 10,
  "score_type": "for_time",
  "format_spec": "21/15/9",
  "notes": "Cada quebra 3 BOB",
  "movements": [
    {
      "movement_slug": "thruster",
      "movement_label_raw": "Thruster",
      "reps_spec": "21/15/9",
      "sort_order": 0
    },
    {
      "movement_slug": "pull_up",
      "movement_label_raw": "Pull up",
      "reps_spec": "21/15/9",
      "sort_order": 1
    }
  ],
  "sort_order": 3
}
```

---

## Validação Pydantic (referência)

```python
from pydantic import BaseModel
from typing import Optional
from enum import Enum

class BlockKind(str, Enum):
    warmup   = "warmup"
    skill    = "skill"
    metcon   = "metcon"
    cooldown = "cooldown"
    mobility = "mobility"
    custom   = "custom"

class ScoreType(str, Enum):
    for_time    = "for_time"
    amrap       = "amrap"
    emom        = "emom"
    rounds_reps = "rounds_reps"
    load        = "load"

class ParsedMovement(BaseModel):
    movement_slug: Optional[str] = None
    movement_label_raw: str
    sets: Optional[int] = None
    reps_spec: Optional[str] = None
    load_spec: Optional[str] = None
    load_rx_male_kg: Optional[float] = None
    load_rx_female_kg: Optional[float] = None
    load_percentage_rm: Optional[float] = None
    emom_label: Optional[str] = None
    notes: Optional[str] = None
    is_scaled_alternative: bool = False
    sort_order: int

class ParsedBlock(BaseModel):
    kind: BlockKind
    title: Optional[str] = None
    notes: Optional[str] = None
    timecap_min: Optional[int] = None
    rounds: Optional[int] = None
    interval_seconds: Optional[int] = None
    score_type: Optional[ScoreType] = None
    format_spec: Optional[str] = None
    movements: list[ParsedMovement]
    sort_order: int

class ParsedDay(BaseModel):
    weekday: int  # 0=seg ... 6=dom
    weekday_label: str
    blocks: list[ParsedBlock]

class ParseWarning(BaseModel):
    line_number: int
    line_text: str
    message: str

class WodPasteResult(BaseModel):
    week_label: Optional[str] = None
    parse_warnings: list[ParseWarning] = []
    days: list[ParsedDay]
```

---

## Contrato de falha

- Parser **nunca lança exceção** para o caller. Linhas não resolvidas → `parse_warnings`.
- `movement_slug: null` é resultado válido — significa "coach precisa revisar".
- `movement_label_raw` **sempre** preserva o texto original exato.
- Se o dia inteiro falhar, `days` contém o item mas `blocks` é array vazio; `parse_warnings` explica.
- L2 (LLM) retorna o **mesmo schema**. Se o JSON do LLM não validar contra `WodPasteResult`, o resultado é descartado e a linha vai para `parse_warnings` com mensagem "L2 não resolveu".
