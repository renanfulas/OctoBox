"""
ARQUIVO: parser determinístico de HTML legado -> payload de PublicWorkoutProgram
(Onda A2 do CORDA, docs/plans/public-workouts-produtizacao-corda.md).

POR QUE ELE EXISTE:
- migra os 10 programas de consultoria reais (HTML legado em
  templates/public_workouts/<slug>.html) para o payload que
  public_workouts/schema.py já valida (contrato congelado da Onda S0).
- **Decisão de arquitetura**: o plano original chamava isso de "parser de
  IA", mas a extração não precisa de LLM. `movement_slug` já é resolvido
  deterministicamente desde a Onda A0 (musclewiki.movement_slug_from_url,
  via o href do `<a class="wiki-btn">`), e `reps_spec`/`rir_spec` do schema
  são texto livre SEM validação de formato — o HTML já tem, por exercício,
  um resumo condensado escrito pelo próprio treinador
  (`<div class="gym-reps">`) que serve quase verbatim. Usar um LLM aqui
  trocaria uma extração 100% determinística e testável por um risco de
  "chute plausível" de reps/RIR — pior justamente onde não pode errar
  (10 clientes pagantes reais).

PONTOS CRÍTICOS:
- `program_id`/`program_label`/`started_on`/`weeks`/`accent_variant` vêm de
  fora (do management command), nunca advinhados do HTML — são decisões de
  negócio, não dado extraível.
- Ordem de `days` = ordem de aparição das `<div class="session">` no HTML,
  nunca reordenado (a primeira sessão de alguns clientes não é "seg").
- Combo de exercício (biset/superset) tem DOIS formatos de HTML distintos:
  "inline" (1 `.ex`, o `<a class="gym-wiki">` aponta pra um exercício
  diferente do `<a class="wiki-btn">` — sinaliza 2 movimentos dentro do
  mesmo bloco) e "wrapped" (`<div class="biset-wrap">` envolvendo 2 `.ex`
  irmãos, cada um já completo e autocontido). Os dois viram 2 `movement`s
  dentro do MESMO `block` do schema — nunca um "exercício composto".
- Alternativa "OU" (`<div class="or-divider">` seguido de um `.ex`): o
  schema não modela "escolha entre A e B" — o `.ex` depois do divisor é
  **excluído do payload** e reportado como pulado. Incluir ingenuamente
  seria erro real de prescrição (aluno instruído a fazer os dois).
- `.ex` sem `<a class="wiki-btn">` (inserção de cardio solta, exercício sem
  link, ou vaga genuinamente aberta tipo "Acessório livre — o que precisar
  naquela semana") cai num slug via `slugify(nome)` — `services.
  _ensure_movements_exist` já cria isso como `PublicWorkoutMovement`
  `pending` sem bloquear `publish_program` (Onda A1). Revisar esses casos
  no `PublicWorkoutMovementAdmin` é o fluxo esperado, não um bug a evitar
  aqui.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from html.parser import HTMLParser

from django.utils.text import slugify

from .musclewiki import movement_slug_from_url

SCHEMA_VERSION = 1


@dataclass
class SkippedExercise:
    """Bloco `.ex` deliberadamente fora do payload — sempre reportado, nunca silencioso."""

    day_id: str
    name: str
    reason: str


@dataclass
class _SetRow:
    kind_text: str  # texto visível do <span class="st ...">, ex. "Top Set", "Top 1", "Preparatória"
    is_top: bool  # classe contém "st-t"
    series: str
    reps: str
    note: str


@dataclass
class _ExerciseNode:
    name: str = ''
    wiki_url: str | None = None
    gym_wiki_url: str | None = None
    gym_reps: str = ''
    note_text: str = ''
    rows: list[_SetRow] = field(default_factory=list)
    has_tracker: bool = False
    day_id: str = ''

    def _is_flat_table(self) -> bool:
        # franciele.html e' o unico dos 10 programas cuja sets-tbl nao tem a
        # coluna "Tipo" (sem <span class="st ...">) -- so' 1 linha por
        # exercicio, sem ramp de prep/feeder/top. Nesse formato as celulas
        # sao (series+reps combinados, RIR, descanso), nao (series, reps,
        # nota) -- ver _row_reps_spec/_row_rir_spec.
        return bool(self.rows) and not any(row.kind_text for row in self.rows)

    def _last_top_row(self) -> _SetRow | None:
        top_rows = [row for row in self.rows if row.is_top]
        if top_rows:
            return top_rows[-1]
        if self._is_flat_table():
            return self.rows[-1]
        return None

    def reps_spec(self) -> str:
        if self.gym_reps:
            return self.gym_reps
        if self.rows:
            flat = self._is_flat_table()
            return ' → '.join(_row_reps_spec(row, flat=flat) for row in self.rows if row.reps)
        return self.note_text.strip()

    def rir_spec(self) -> str:
        top_row = self._last_top_row()
        if top_row is None:
            return ''
        return _row_rir_spec(top_row, flat=self._is_flat_table())

    def movement_slug(self, *, url: str | None = None) -> str:
        target_url = url if url is not None else self.wiki_url
        if target_url:
            slug = movement_slug_from_url(target_url)
            if slug:
                return slug
        return slugify(self.name) or 'movimento-sem-nome'

    def to_movement_dict(self, *, url: str | None = None, reps_spec: str | None = None, rir_spec: str | None = None) -> dict:
        return {
            'movement_slug': self.movement_slug(url=url),
            'reps_spec': self.reps_spec() if reps_spec is None else reps_spec,
            'rir_spec': self.rir_spec() if rir_spec is None else rir_spec,
            'is_tracked': self.has_tracker,
            'load_type': 'free',
            'load_value': None,
            'reference_url': url if url is not None else self.wiki_url,
        }

    def is_biset_inline(self) -> bool:
        return bool(self.gym_wiki_url) and self.gym_wiki_url != self.wiki_url

    def to_block_dict(self) -> dict:
        if self.is_biset_inline():
            if len(self.rows) >= 2:
                # `gym_reps` descreve os DOIS movimentos juntos (ex. "2× 45-60s
                # → 2× 12-15") — reps_spec/rir_spec por movimento vem da linha
                # individual dele na sets-tbl, nunca do resumo compartilhado.
                flat = self._is_flat_table()
                primary, secondary = self.rows[0], self.rows[1]
                movements = [
                    self.to_movement_dict(
                        url=self.wiki_url, reps_spec=_row_reps_spec(primary, flat=flat), rir_spec=_row_rir_spec(primary, flat=flat),
                    ),
                    self.to_movement_dict(
                        url=self.gym_wiki_url, reps_spec=_row_reps_spec(secondary, flat=flat), rir_spec=_row_rir_spec(secondary, flat=flat),
                    ),
                ]
            else:
                # Não deu pra mapear linha->movimento com confiança — os dois
                # movimentos entram com o mesmo reps_spec/rir_spec agregado em
                # vez de adivinhar qual linha é de qual.
                movements = [
                    self.to_movement_dict(url=self.wiki_url),
                    self.to_movement_dict(url=self.gym_wiki_url),
                ]
            return {'movements': movements}
        return {'movements': [self.to_movement_dict()]}


_BARE_RIR_NUMBER_RE = re.compile(r'^\d+(-\d+)?$')


def _row_rir_spec(row: _SetRow, *, flat: bool = False) -> str:
    # Tabela "flat" (franciele.html, sem coluna Tipo): as 3 celulas sao
    # (series+reps, RIR, descanso) -- o RIR mora em `reps`, nao em `note`
    # (que aqui e' o descanso, fora do schema).
    source = row.reps if flat else row.note
    text = source.strip()
    if text in ('—', '-', ''):
        return ''
    if _BARE_RIR_NUMBER_RE.match(text):
        # Formato "RIR" como coluna própria (rafael.html, e franciele em
        # modo flat): o valor já É o número/faixa ("1-2"), sem o texto "RIR"
        # na frente — normaliza pra ficar igual ao formato "RIR 1-2 · ..."
        # que os outros programas usam.
        return f'RIR {text}'
    return text


def _row_reps_spec(row: _SetRow, *, flat: bool = False) -> str:
    if flat:
        # Tabela "flat" (franciele.html): a 1a celula ja e' a especificacao
        # completa ("3x12"), sem ramp de tipos (Prep/Feeder/Top) pra juntar.
        return row.series
    # `row.series` já vem com o "×" incluso no próprio HTML (célula "2×",
    # "3×") — não duplicar o símbolo aqui.
    return ' '.join(part for part in (row.kind_text, row.series, row.reps) if part).strip()


class _ProgramHTMLParser(HTMLParser):
    """Varre o HTML legado inteiro, emitindo dias (com blocos) e pulados.

    Cada escopo semântico que pode conter `<div>` aninhado arbitrário
    (session/ex/biset_wrap) tem seu PRÓPRIO contador de profundidade —
    incrementado/decrementado por QUALQUER `<div>` aberto/fechado enquanto
    o escopo está ativo, nunca só pelo próprio marcador. Sem isso, o
    primeiro `</div>` interno (ex.: fechando `.sess-title`) fecharia a
    sessão inteira prematuramente. `<table>`/`<tr>`/`<td>`/`<span>`/`<a>`
    não são `<div>`, então não interferem nessa contagem — podem usar
    estado simples (não aninham entre si nesta estrutura).
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.days: list[dict] = []
        self.skipped: list[SkippedExercise] = []

        self._capture: str | None = None  # o que handle_data deve acumular agora
        self._buffer: list[str] = []

        self._session_depth = 0
        self._ex_depth = 0
        self._biset_depth = 0

        self._current_day_id: str | None = None
        self._current_day_label = ''
        self._current_day_blocks: list[dict] = []
        self._biset_group: list[_ExerciseNode] = []  # .ex acumulados dentro do .biset-wrap atual
        self._current_ex: _ExerciseNode | None = None
        self._in_table = False
        self._in_row = False
        self._current_row_cells: list[str] = []
        self._current_row_is_top = False
        self._current_row_kind_text = ''
        self._pending_alternative = False  # True logo após um .or-divider

    # ------------------------------------------------------------------
    # Infra de captura de texto
    # ------------------------------------------------------------------

    def _start_capture(self, target: str) -> None:
        self._capture = target
        self._buffer = []

    def _end_capture(self) -> str:
        text = ''.join(self._buffer).strip()
        self._capture = None
        self._buffer = []
        return text

    def handle_data(self, data: str) -> None:
        if self._capture is not None:
            self._buffer.append(data)

    # ------------------------------------------------------------------
    # Tags de abertura
    # ------------------------------------------------------------------

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        classes = (attrs_dict.get('class') or '').split()

        if tag == 'div':
            if self._session_depth == 0:
                if 'session' in classes:
                    self._session_depth = 1
                    self._current_day_id = attrs_dict.get('id') or ''
                    self._current_day_label = ''
                    self._current_day_blocks = []
                return  # fora de qualquer sessão — nav, head, etc. não interessam

            self._session_depth += 1  # qualquer outro div consome 1 nível da sessão

            if self._ex_depth == 0 and self._biset_depth == 0:
                if classes == ['ex']:
                    self._ex_depth = 1
                    self._current_ex = _ExerciseNode(day_id=self._current_day_id or '')
                elif 'biset-wrap' in classes:
                    self._biset_depth = 1
                    self._biset_group = []
                elif classes == ['or-divider']:
                    self._pending_alternative = True
                elif 'sess-title' in classes:
                    self._start_capture('sess_title')
                return

            if self._biset_depth > 0 and self._ex_depth == 0:
                self._biset_depth += 1
                if classes == ['ex']:
                    self._ex_depth = 1
                    self._current_ex = _ExerciseNode(day_id=self._current_day_id or '')
                elif classes == ['or-divider']:
                    # milene.html: o "OU" e' o exercicio alternativo ficam
                    # DENTRO do proprio .biset-wrap, nao so' no nivel da sessao.
                    self._pending_alternative = True
                return

            # A partir daqui, _ex_depth > 0 — dentro de um `.ex` de verdade.
            self._ex_depth += 1
            if self._current_ex is None:
                return
            if 'ex-name' in classes:
                self._start_capture('ex_name')
            elif 'gym-reps' in classes:
                self._start_capture('gym_reps')
            elif classes == ['ex-note']:
                self._start_capture('ex_note')
            elif 'tracker' in classes:
                self._current_ex.has_tracker = True
            return

        if self._ex_depth == 0:
            return  # <table>/<tr>/<a> fora de um .ex não interessam (nav, etc.)

        if tag == 'a':
            href = attrs_dict.get('href') or ''
            if 'wiki-btn' in classes and href and self._current_ex.wiki_url is None:
                self._current_ex.wiki_url = href
            elif 'gym-wiki' in classes and href and self._current_ex.gym_wiki_url is None:
                self._current_ex.gym_wiki_url = href
        elif tag == 'table' and 'sets-tbl' in classes:
            self._in_table = True
        elif tag == 'tr' and self._in_table:
            self._in_row = True
            self._current_row_cells = []
            self._current_row_is_top = False
            self._current_row_kind_text = ''
        elif tag == 'th' and self._in_row:
            self._in_row = False  # linha de cabeçalho — nunca vira _SetRow (ver handle_endtag de </tr>)
        elif tag == 'td' and self._in_row:
            self._start_capture('cell')
        elif tag == 'span' and self._in_row and classes[:1] == ['st']:
            self._current_row_is_top = 'st-t' in classes
            self._start_capture('cell')  # o texto do span TAMBÉM é o texto da 1ª célula

    # ------------------------------------------------------------------
    # Tags de fechamento
    # ------------------------------------------------------------------

    def handle_endtag(self, tag: str) -> None:
        if tag == 'div':
            if self._session_depth == 0:
                return

            if self._capture == 'sess_title':
                self._current_day_label = self._end_capture()
            elif self._capture == 'ex_name':
                self._current_ex.name = self._end_capture()
            elif self._capture == 'gym_reps':
                self._current_ex.gym_reps = self._end_capture()
            elif self._capture == 'ex_note':
                self._current_ex.note_text = self._end_capture()

            if self._ex_depth > 0:
                self._ex_depth -= 1
                if self._ex_depth == 0:
                    self._close_current_ex()

            if self._ex_depth == 0 and self._biset_depth > 0:
                self._biset_depth -= 1
                if self._biset_depth == 0:
                    self._flush_biset_group()

            self._session_depth -= 1
            if self._session_depth == 0:
                self._flush_day()
            return

        if self._ex_depth == 0:
            return

        if self._capture == 'cell' and tag in ('td', 'span'):
            text = self._end_capture()
            if tag == 'span':
                self._current_row_kind_text = text
            else:
                self._current_row_cells.append(text)
            return

        if tag == 'tr' and self._in_row:
            self._in_row = False
            if self._current_row_cells:  # linha de cabeçalho (só <th>) nunca chega aqui com células
                series, reps, note = (self._current_row_cells + ['', '', ''])[:3]
                self._current_ex.rows.append(_SetRow(
                    kind_text=self._current_row_kind_text,
                    is_top=self._current_row_is_top,
                    series=series,
                    reps=reps,
                    note=note,
                ))
            return
        if tag == 'table' and self._in_table:
            self._in_table = False

    # ------------------------------------------------------------------
    # Finalização de bloco/dia
    # ------------------------------------------------------------------

    def _close_current_ex(self) -> None:
        ex = self._current_ex
        self._current_ex = None
        if ex is None or not ex.name:
            return

        if self._pending_alternative:
            self._pending_alternative = False
            self.skipped.append(SkippedExercise(
                day_id=ex.day_id, name=ex.name,
                reason='alternativa "OU" — schema não modela escolha entre exercícios',
            ))
            return

        if self._biset_depth > 0:
            self._biset_group.append(ex)
            return

        self._current_day_blocks.append(ex.to_block_dict())

    def _flush_biset_group(self) -> None:
        if not self._biset_group:
            return
        movements = [ex.to_movement_dict() for ex in self._biset_group]
        self._current_day_blocks.append({'movements': movements})
        self._biset_group = []

    def _flush_day(self) -> None:
        if self._current_day_id and self._current_day_blocks:
            self.days.append({
                'day_id': self._current_day_id,
                'label': self._current_day_label or self._current_day_id,
                'blocks': self._current_day_blocks,
            })
        self._current_day_id = None
        self._current_day_blocks = []


def parse_legacy_html(html: str) -> tuple[list[dict], list[SkippedExercise]]:
    """HTML legado -> (days prontos pro payload, exercícios pulados p/ revisão).

    Função pura, sem Django ORM — só o parsing. `days` já está no formato
    `schema.py` espera (`day_id`/`label`/`blocks[].movements[]`); quem chama
    (o management command) monta o payload completo com os metadados de
    negócio (`program_id` etc.) por cima.
    """
    parser = _ProgramHTMLParser()
    parser.feed(html)
    return parser.days, parser.skipped


def build_program_payload_from_html(
    *,
    html: str,
    program_id: str,
    program_label: str,
    started_on: str,
    weeks: int,
    accent_variant: str | None,
) -> tuple[dict, list[SkippedExercise]]:
    """HTML legado -> payload pronto para `schema.assert_valid_payload`/`services.publish_program`.

    `program_id`/`program_label`/`started_on`/`weeks`/`accent_variant` vêm de
    fora sempre — são decisão de negócio, nunca advinhados do HTML (ver
    docstring do módulo)."""
    days, skipped = parse_legacy_html(html)
    payload = {
        'schema_version': SCHEMA_VERSION,
        'program_id': program_id,
        'program_label': program_label,
        'started_on': started_on,
        'weeks': weeks,
        'accent_variant': accent_variant,
        'days': days,
    }
    return payload, skipped


__all__ = ['SkippedExercise', 'build_program_payload_from_html', 'parse_legacy_html']
