"""
ARQUIVO: dados de apresentação do painel inicial do corredor (Início / Sua
semana) — fundação visual pedida pelo Renan pra aproximar o layout do
corredor do app do aluno de box (topbar com saudação, semana com dias
reais, resumo do programa).

POR QUE ELE EXISTE:
- fundação visual, mesma família do resto de `templates/public_workouts/workout.html`
  (Onda B3) — sem acoplar a nenhum template/view do `student_app` (D.00:
  produtos são isolados; só os TOKENS de CSS são compartilhados, nunca
  markup/lógica). Funções puras aqui, sem ORM — o mesmo padrão de
  `one_rep_max.py`/`substitutions.py`.
- `build_program_summary` é texto DETERMINÍSTICO (sem LLM) por decisão do
  Renan: monta o espaço pronto pra plugar um resumo por Haiku depois, sem
  gerar custo de API nem decisão de cache agora.

PONTOS CRÍTICOS:
- `build_week_overview` usa `day_id` como abreviação real do dia da semana
  (seg/ter/qua/qui/sex/sab/dom) — é assim que o parser determinístico da
  Onda A2 sempre gerou os 10 programas reais (nunca "dia 1/dia 2"). Não
  inventa mapeamento novo nem pede input do treinador.
- "dia completo" = existe `PublicWorkoutLoadLog` do aluno com `performed_on`
  igual à data real daquele dia da semana corrente — não tenta correlacionar
  com QUAL movimento foi registrado (mesmo critério grosso que o app do
  box usa pra streak semanal, só olha se houve ação naquela data).
- `completed_dates` entra como `set[date]` já calculado por quem chama —
  mantém esta função pura/testável sem tocar ORM (a consulta de verdade,
  `PublicWorkoutLoadLog.objects.filter(...)`, é responsabilidade de quem
  ligar isto a uma view de verdade, ainda não existe — mesmo estágio de
  "fundação, não ligado a URL" do resto de `workout.html`).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

_WEEKDAY_ORDER = ('seg', 'ter', 'qua', 'qui', 'sex', 'sab', 'dom')
_WEEKDAY_LABELS = {
    'seg': 'Seg', 'ter': 'Ter', 'qua': 'Qua', 'qui': 'Qui',
    'sex': 'Sex', 'sab': 'Sáb', 'dom': 'Dom',
}
_WEEKDAY_FULL_NAMES = {
    'seg': 'Segunda', 'ter': 'Terça', 'qua': 'Quarta', 'qui': 'Quinta',
    'sex': 'Sexta', 'sab': 'Sábado', 'dom': 'Domingo',
}
# Separadores vistos nos 10 programas reais pro prefixo "<Dia da semana><sep>"
# de day.label (schema.py) -- nunca so' hifen: bruno/johnespanha usam
# travessao "—" (em dash), franciele usa hifen "-". Ordem importa: precisa
# tentar o mais longo (" — ") antes do mais curto (" - ") pra nao cortar
# no meio de um travessao.
_DAY_LABEL_SEPARATORS = (' — ', ' – ', ' - ')


def day_short_label(day_id: str) -> str:
    """'seg' -> 'Seg' — mesma abreviacao de 3 letras de _WEEKDAY_LABELS,
    exposta pra uso fora de build_week_overview (Treino tambem quer o dia
    curto, nao so' Inicio)."""
    return _WEEKDAY_LABELS.get(day_id, day_id)


def day_keyword(*, day_id: str, label: str) -> str:
    """Extrai a "palavra-chave" do treino de `day.label`, sem o nome do dia
    duplicado (o dia curto ja aparece em `day_short_label` ao lado).

    NEM TODO `day.label` real tem o nome do dia como prefixo — juliana e
    henrique usam so' a palavra-chave pura ("Quadríceps", "Superior A"),
    sem "Segunda -"/"Terça —" na frente (conferido nos payloads publicados,
    nao adivinhado). Por isso so' remove o prefixo quando ele bate com o
    nome completo do dia (_WEEKDAY_FULL_NAMES) seguido de um dos separadores
    conhecidos — nunca corta um label que nao tem esse prefixo."""
    full_name = _WEEKDAY_FULL_NAMES.get(day_id)
    if not full_name or not label:
        return label
    if not label.lower().startswith(full_name.lower()):
        return label
    remainder = label[len(full_name):]
    for separator in _DAY_LABEL_SEPARATORS:
        if remainder.startswith(separator):
            return remainder[len(separator):]
    return label


@dataclass(frozen=True)
class WeekDay:
    day_id: str
    label: str
    date: date
    has_program: bool
    is_today: bool
    is_complete: bool


def build_week_overview(*, payload: dict, completed_dates: set, today: date | None = None) -> list[WeekDay]:
    """7 dias reais (segunda a domingo) da semana corrente de `today`.

    `has_program`: existe algum `day_id` no payload igual a este dia da
    semana (independente de qual semana do mesociclo — o programa se
    repete toda semana até o treinador publicar uma nova versão).
    """
    today = today or date.today()
    monday = today - timedelta(days=today.weekday())
    prescribed_day_ids = {day['day_id'] for day in payload.get('days', ())}

    return [
        WeekDay(
            day_id=day_id,
            label=_WEEKDAY_LABELS[day_id],
            date=day_date,
            has_program=day_id in prescribed_day_ids,
            is_today=day_date == today,
            is_complete=day_date in completed_dates,
        )
        for offset, day_id in enumerate(_WEEKDAY_ORDER)
        for day_date in (monday + timedelta(days=offset),)
    ]


def build_program_summary(payload: dict) -> dict:
    """Explicação determinística (SEM IA) do programa: o que é, pra quantos
    dias por semana foi montado, quantos exercícios tem. Contrato estável
    (`headline`/`body`) pensado pra um resumo gerado por Haiku poder
    substituir só o corpo da função depois, sem o template mudar."""
    days = payload.get('days', ())
    weeks = payload.get('weeks', 0)
    day_count = len(days)
    total_movements = sum(len(block['movements']) for day in days for block in day['blocks'])
    tracked_count = sum(
        1 for day in days for block in day['blocks'] for movement in block['movements']
        if movement.get('is_tracked')
    )

    program_label = payload.get('program_label') or 'Seu programa'
    headline = f"{program_label} · {weeks} semana{'s' if weeks != 1 else ''}"

    if day_count == 0:
        body = 'Ainda não há dias configurados neste programa.'
    else:
        body = (
            f"Montado pra rodar {day_count} dia{'s' if day_count != 1 else ''} por semana, "
            f"com {total_movements} exercício{'s' if total_movements != 1 else ''} no total"
        )
        if tracked_count:
            body += f" — {tracked_count} {'deles' if tracked_count != 1 else 'dele'} com carga acompanhada de perto"
        body += '.'

    return {'headline': headline, 'body': body}


__all__ = ['WeekDay', 'build_program_summary', 'build_week_overview', 'day_keyword', 'day_short_label']
