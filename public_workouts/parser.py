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

import json
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser

from django.utils.text import slugify

from .dashboard import day_full_label
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
    # (label, url) por `.var-link` dentro de `.ex-var` — normalmente 1, mas
    # bruno.html tem um caso real com 2 (hack squat sugerindo leg press E
    # hack squat como variacao) -- lista, nunca um campo unico.
    variations: list[tuple[str, str]] = field(default_factory=list)

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
        movement = {
            'movement_slug': self.movement_slug(url=url),
            # Nome em PORTUGUES escrito pelo treinador (`.ex-name`) — antes
            # so' era usado como fallback de slug (`movement_slug` acima),
            # nunca guardado pra exibicao; o template caia pro slug em
            # ingles do MuscleWiki humanizado. Aditivo (schema.py) — nunca
            # quebra payload ja publicado sem este campo.
            'name': self.name,
            'reps_spec': self.reps_spec() if reps_spec is None else reps_spec,
            'rir_spec': self.rir_spec() if rir_spec is None else rir_spec,
            'is_tracked': self.has_tracker,
            'load_type': 'free',
            'load_value': None,
            'reference_url': url if url is not None else self.wiki_url,
        }
        if self.variations:
            movement['variations'] = [{'label': label, 'reference_url': variation_url} for label, variation_url in self.variations]
        return movement

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
        self._pending_variation_url: str | None = None  # href do .var-link em captura

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
            elif 'var-link' in classes and href:
                # `.ex-var` pode ter mais de um `.var-link` (bruno.html tem
                # 1 caso real com 2) -- guarda o href aqui, o texto (nome da
                # variacao) vem via captura normal, fechado em </a> abaixo.
                self._pending_variation_url = href
                self._start_capture('var_link')
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

        if tag == 'a' and self._capture == 'var_link':
            label = self._end_capture()
            if label and self._pending_variation_url:
                self._current_ex.variations.append((label, self._pending_variation_url))
            self._pending_variation_url = None
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


class _CardioTabParser(HTMLParser):
    """Extrai `#tab-cardio` (aba dedicada de cardio semanal — juliana/bruno/
    henrique/johnespanha/thaislima; ver docstring do modulo pra decisao de
    so' cobrir ESTE formato, nao o cardio embutido por dia de franciele/
    milene, formato diferente demais pra unificar nesta fatia).

    So' captura `.c-card` (sessao de cardio): `.c-head` vira `title` (texto
    direto do head, sem o `.km-badge` filho) + `badge` (texto do
    `.km-badge`); `.c-row` vira um item de `details` (label/value); `.c-note`
    vira `note`. Ignora `.cardio-week` (resumo semanal) de proposito — e'
    so' um resumo do que ja esta nos `.c-card`s, o template deriva a visao
    compacta a partir da lista de `sessions`, sem duplicar dado no payload.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.sessions: list[dict] = []

        self._tab_depth = 0
        self._card_depth = 0
        self._current_session: dict | None = None
        self._capture: str | None = None
        self._buffer: list[str] = []
        self._in_row = False
        self._row_parts: list[str] = []

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

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        classes = (attrs_dict.get('class') or '').split()

        if self._tab_depth == 0:
            if tag == 'div' and attrs_dict.get('id') == 'tab-cardio':
                self._tab_depth = 1
            return

        if tag == 'div':
            self._tab_depth += 1
            if self._card_depth == 0:
                if 'c-card' in classes:
                    self._card_depth = 1
                    self._current_session = {'title': '', 'badge': '', 'details': [], 'note': ''}
                return
            self._card_depth += 1
            if 'c-head' in classes:
                self._start_capture('head')
            elif 'c-row' in classes:
                self._in_row = True
                self._row_parts = []
            elif 'c-note' in classes:
                self._start_capture('note')
            return

        if self._card_depth == 0:
            return
        if tag == 'span':
            if 'km-badge' in classes:
                # `.km-badge` e' o ULTIMO filho de `.c-head` nos 5 clientes
                # reais com esta aba (texto do head sempre vem antes) --
                # fecha a captura de 'head' aqui (vira `title`) e comeca uma
                # nova captura so' pro badge, em vez de misturar os dois
                # textos no mesmo buffer.
                if self._capture == 'head':
                    self._current_session['title'] = self._end_capture()
                self._start_capture('badge')
            elif self._in_row:
                self._start_capture('row-part')

    def handle_endtag(self, tag: str) -> None:
        if tag == 'span':
            if self._capture == 'badge':
                self._current_session['badge'] = self._end_capture()
            elif self._capture == 'row-part':
                self._row_parts.append(self._end_capture())
            return

        if tag != 'div':
            return

        if self._card_depth == 0:
            if self._tab_depth > 0:
                self._tab_depth -= 1
            return

        if self._capture == 'head':
            self._current_session['title'] = self._end_capture()
        elif self._capture == 'note':
            self._current_session['note'] = self._end_capture()

        if self._in_row:
            self._in_row = False
            if len(self._row_parts) >= 2:
                self._current_session['details'].append({'label': self._row_parts[0], 'value': self._row_parts[1]})
            self._row_parts = []

        self._card_depth -= 1
        self._tab_depth -= 1
        if self._card_depth == 0 and self._current_session is not None:
            if self._current_session['title']:
                self.sessions.append(self._current_session)
            self._current_session = None


# Modalidades reais de cardio vistas nos clientes com `.c-card` embutido
# por dia (franciele/rafael/giovanna/johnespanha) -- coach SEMPRE precisa
# nomear a modalidade pra prescrever cardio (não dá pra prescrever "faça
# cardio" sem dizer o quê), então isso funciona como sinal positivo
# confiável. Existe porque `.c-head` sozinho NÃO basta: giovanna reusa a
# MESMA marcação (`.c-card`+`.c-head`) pra notas de orientação do dia de
# CrossFit ("Orientação do dia", "Regra prática", "Estratégia" — nenhuma
# delas é cardio) e rafael pra cards de refeição (fora de `.session`,
# nunca chegam aqui, mas o princípio de "não confiar só em `.c-head`" é o
# mesmo). Case-insensitive, substrings sem acento pra cobrir as duas
# grafias.
_CARDIO_TITLE_KEYWORDS = (
    'corrid', 'esteira', 'bike', 'bicicl', 'eliptic', 'remo', 'natac',
    'caminhad', 'trote', 'hiit', 'liss', 'cardio', 'zona', 'sprint', 'pedal',
)


def _looks_like_cardio_title(title: str) -> bool:
    lowered = title.lower()
    return any(keyword in lowered for keyword in _CARDIO_TITLE_KEYWORDS)


class _EmbeddedStageParser(HTMLParser):
    """Extrai `.c-card` embutido DENTRO de cada `.session` (franciele.html/
    rafael.html: sem aba dedicada `#tab-cardio`). `_CardioTabParser` so'
    cobre a aba dedicada (juliana/bruno/henrique/johnespanha/thaislima) de
    proposito — formato difernte demais pra unificar (ver docstring do
    modulo/_CardioTabParser). Esta classe fecha essa lacuna documentada,
    reusando a MESMA extracao de `.c-card` (c-head/km-badge/c-row/c-note),
    so' que disparada por "dentro de uma sessao" em vez de "dentro de
    `#tab-cardio`".

    Classificação em 2 passos — nenhum dos dois sozinho basta:
    1. Estrutural: todo card de cardio observado tem `.c-head` (título +
       `.km-badge`) como primeiro filho; card de mobilidade/ativação/
       coordenação é só uma lista de `.c-row` SEM `.c-head`. Sem
       `.c-head` → vira movimento auxiliar direto (ver abaixo), nunca
       cardio.
    2. Com `.c-head`, ainda precisa CONFIRMAR que é cardio de verdade —
       giovanna.html reusa a MESMA marcação (`.c-card`+`.c-head`) pra
       notas de orientação do dia de CrossFit ("Orientação do dia", "Regra
       prática", "Estratégia" — nenhuma é cardio) nos dias de força, só a
       de sábado ("Corrida 4-5 km") é cardio de verdade. `.stage-title`
       também não ajuda aqui (rafael.html não tem NENHUM, giovanna.html
       também não usa "Etapa N"). O sinal que sobra e que É confiável:
       `_looks_like_cardio_title` — o treinador SEMPRE precisa nomear a
       modalidade pra prescrever cardio (não dá pra prescrever "faça
       cardio" sem dizer correr/pedalar/etc.), então o título é onde essa
       modalidade aparece. Card com `.c-head` cujo título NÃO bate nenhuma
       modalidade conhecida é DESCARTADO por completo (nem cardio, nem
       movimento auxiliar) — não existe campo no schema pra "nota de
       orientação do dia", e chutar isso como cardio ou como exercício
       seria pior que não mostrar nada.

    Cardio confirmado vira entrada de `cardio_sessions()` (agregado do
    PROGRAMA inteiro, dedup por identidade de conteúdo com os dias
    mesclados num detail "Dias" — franciele repete o mesmo `.c-card` em
    ter/qui/sex, uma sessão só no payload, mas dizendo em quais dias vale).
    Sem `.c-head` → cada `.c-row` vira um MOVIMENTO leve (sem wiki-btn) no
    `auxiliary_blocks_by_day` daquele dia, prependado aos blocos de
    "Etapa 2 - Força" (que continua exclusivamente pelo `.ex`/
    _ProgramHTMLParser, nunca se mistura com `.c-card`).

    PONTOS CRITICOS:
    - Slug do movimento auxiliar usa a DESCRICAO da linha (`rpartition(' -
      ')` pra separar da dica de reps no final), nunca o `.c-lbl` (grupo
      muscular) — o mesmo `.c-lbl` ("Padrão", "Escapular", "Glúteo médio")
      se repete no mesmo dia com descricoes diferentes; slugar pelo label
      colidiria.
    - So' entra em jogo dentro de `.session` — `.c-card` de uma aba
      dedicada `#tab-cardio` (fora de qualquer `.session`) nunca aciona
      esta classe (`_session_depth` fica 0 o tempo todo la fora), entao
      nunca duplica/conflita com `_CardioTabParser` pros clientes que já
      tem aba dedicada (mesmo quando o card embutido é redundante com ela,
      como em johnespanha — `build_program_payload_from_html` prioriza a
      aba dedicada quando ela existe, nunca concatena os dois).
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.auxiliary_blocks_by_day: dict[str, list[dict]] = {}
        # (day_id, card) por OCORRENCIA -- sem dedup ainda (precisa saber de
        # QUAIS dias cada card veio antes de juntar; ver cardio_sessions()).
        self._cardio_occurrences: list[tuple[str, dict]] = []

        self._session_depth = 0
        self._current_day_id: str | None = None

        self._card_depth = 0
        self._current_card: dict | None = None
        self._card_is_cardio = False
        self._capture: str | None = None
        self._buffer: list[str] = []
        self._in_row = False
        self._row_parts: list[str] = []

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

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        classes = (attrs_dict.get('class') or '').split()

        if tag != 'div':
            if self._card_depth == 0:
                return
            if tag == 'span':
                if 'km-badge' in classes:
                    if self._capture == 'head':
                        self._current_card['title'] = self._end_capture()
                    self._start_capture('badge')
                elif self._in_row:
                    self._start_capture('row-part')
            return

        if self._session_depth == 0:
            if 'session' in classes:
                self._session_depth = 1
                self._current_day_id = attrs_dict.get('id') or ''
            return

        self._session_depth += 1

        if self._card_depth == 0:
            if 'c-card' in classes:
                self._card_depth = 1
                self._current_card = {'title': '', 'badge': '', 'details': [], 'note': ''}
                self._card_is_cardio = False  # decidido abaixo, so' se aparecer um `.c-head`
            return

        self._card_depth += 1
        if 'c-head' in classes:
            self._start_capture('head')
            self._card_is_cardio = True
        elif 'c-row' in classes:
            self._in_row = True
            self._row_parts = []
        elif 'c-note' in classes:
            self._start_capture('note')

    def handle_endtag(self, tag: str) -> None:
        if tag == 'span':
            if self._capture == 'badge':
                self._current_card['badge'] = self._end_capture()
            elif self._capture == 'row-part':
                self._row_parts.append(self._end_capture())
            return

        if tag != 'div':
            return
        if self._session_depth == 0:
            return

        if self._card_depth > 0:
            if self._capture == 'head':
                self._current_card['title'] = self._end_capture()
            elif self._capture == 'note':
                self._current_card['note'] = self._end_capture()

            if self._in_row:
                self._in_row = False
                if len(self._row_parts) >= 2:
                    self._current_card['details'].append({'label': self._row_parts[0], 'value': self._row_parts[1]})
                self._row_parts = []

            self._card_depth -= 1
            if self._card_depth == 0:
                self._close_card()

        self._session_depth -= 1
        if self._session_depth == 0:
            self._current_day_id = None

    def _close_card(self) -> None:
        card = self._current_card
        self._current_card = None
        if card is None:
            return

        if self._card_is_cardio:
            if card['title'] and self._current_day_id and _looks_like_cardio_title(card['title']):
                self._cardio_occurrences.append((self._current_day_id, card))
            # `.c-head` presente mas titulo nao bate nenhuma modalidade de
            # cardio conhecida (ex.: nota de orientacao do dia em
            # giovanna.html) -- descartado por completo, nunca vira
            # movimento auxiliar (nao e' um exercicio) nem cardio (chute).
            return

        movements = []
        for detail in card['details']:
            description, separator, reps_hint = detail['value'].rpartition(' - ')
            if not separator:
                description = detail['value']
                reps_hint = ''
            movements.append({
                'movement_slug': slugify(description) or 'exercicio-sem-nome',
                'name': description,
                'reps_spec': reps_hint,
                'rir_spec': '',
                'is_tracked': False,
                'load_type': 'free',
                'load_value': None,
                'reference_url': None,
            })
        if movements and self._current_day_id:
            self.auxiliary_blocks_by_day.setdefault(self._current_day_id, []).append({'movements': movements})

    def cardio_sessions(self) -> list[dict]:
        """Agrupa as ocorrências de `.c-card` de cardio por IDENTIDADE de
        conteúdo (título/badge/details/note) e injeta um detail "Dias" na
        frente com os dias da semana em que aquele card apareceu. Sem isso,
        2+ ocorrências idênticas em dias diferentes (franciele repete o
        mesmo card em ter/qui/sex) viravam 1 sessão sem dizer em quais dias
        ela vale (achado do Renan: "cardio ficou sem explicação de dias") —
        `_CardioTabParser` (aba dedicada) não tem esse conceito de "dia",
        então esse detail só existe pro cardio embutido por dia."""
        grouped: dict[tuple, dict] = {}
        order: list[tuple] = []
        for day_id, card in self._cardio_occurrences:
            key = (card['title'], card['badge'], tuple((d['label'], d['value']) for d in card['details']), card['note'])
            if key not in grouped:
                grouped[key] = {'card': card, 'day_ids': []}
                order.append(key)
            if day_id not in grouped[key]['day_ids']:
                grouped[key]['day_ids'].append(day_id)

        sessions = []
        for key in order:
            entry = grouped[key]
            card = dict(entry['card'])
            day_labels = [day_full_label(day_id) for day_id in entry['day_ids']]
            card['details'] = [{'label': 'Dias', 'value': _join_natural_pt(day_labels)}] + list(card['details'])
            sessions.append(card)
        return sessions


def _join_natural_pt(items: list[str]) -> str:
    """['Terça', 'Quinta', 'Sexta'] -> 'Terça, Quinta e Sexta' — juncao
    natural em portugues (ultimo item com "e", nao virgula)."""
    if len(items) == 1:
        return items[0]
    return ', '.join(items[:-1]) + ' e ' + items[-1]


def parse_embedded_stage_content(html: str) -> tuple[dict[str, list[dict]], list[dict]]:
    """HTML legado -> (blocos auxiliares por dia, sessões de cardio embutidas)
    a partir de `.c-card` DENTRO de cada `.session` (formato franciele/
    rafael — sem aba dedicada `#tab-cardio`, ver docstring de
    _EmbeddedStageParser). Vazio pros outros clientes (sem `.c-card` dentro
    de `.session`)."""
    parser = _EmbeddedStageParser()
    parser.feed(html)
    return parser.auxiliary_blocks_by_day, parser.cardio_sessions()


class _PeriodizationTabParser(HTMLParser):
    """Extrai `#tab-period`: `weeks_table` (`.period-tbl table`),
    `volume_table` (`table.vol-tbl`) e `note` (`.vnote`). O grafico
    (`chart`) NAO vem daqui — ja e' JSON pronto num `<script
    type="application/json" id="period-chart-data">` em outro ponto do
    HTML, extraido por `_extract_chart_json` sem precisar de parsing de
    tabela nenhum."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.weeks_table: list[dict] = []
        self.volume_table: list[dict] = []
        self.note = ''

        self._tab_depth = 0
        self._table_kind: str | None = None  # 'weeks' | 'volume' | None
        self._in_row = False
        self._in_header_row = False
        self._row_cells: list[str] = []
        self._capture: str | None = None
        self._buffer: list[str] = []
        self._in_vnote = False

    def _start_capture(self) -> None:
        self._capture = 'cell'
        self._buffer = []

    def _end_capture(self) -> str:
        text = ''.join(self._buffer).strip()
        self._capture = None
        self._buffer = []
        return text

    def handle_data(self, data: str) -> None:
        if self._capture is not None:
            self._buffer.append(data)
        elif self._in_vnote:
            self._buffer.append(data)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        classes = (attrs_dict.get('class') or '').split()

        if self._tab_depth == 0:
            if tag == 'div' and attrs_dict.get('id') == 'tab-period':
                self._tab_depth = 1
            return

        if tag == 'div':
            self._tab_depth += 1
            if 'period-tbl' in classes:
                self._table_kind = 'weeks'
            elif 'vnote' in classes:
                self._in_vnote = True
                self._buffer = []
            return

        if tag == 'table':
            if 'vol-tbl' in classes:
                self._table_kind = 'volume'
            return

        if self._table_kind is None:
            return

        if tag == 'tr':
            self._in_row = True
            self._row_cells = []
        elif tag == 'th' and self._in_row:
            self._in_header_row = True
        elif tag in ('td', 'th') and self._in_row:
            self._start_capture()

    def handle_endtag(self, tag: str) -> None:
        if tag in ('td', 'th') and self._capture == 'cell':
            self._row_cells.append(self._end_capture())
            return

        if tag == 'tr' and self._in_row:
            self._in_row = False
            if not self._in_header_row and self._row_cells:
                self._append_row(self._row_cells)
            self._in_header_row = False
            self._row_cells = []
            return

        if tag == 'table':
            if self._table_kind == 'volume':
                self._table_kind = None
            return

        if tag == 'div':
            if self._in_vnote:
                self.note = ''.join(self._buffer).strip()
                self._in_vnote = False
                self._buffer = []
            if self._table_kind == 'weeks':
                self._table_kind = None
            self._tab_depth -= 1

    def _append_row(self, cells: list[str]) -> None:
        if self._table_kind == 'weeks':
            week, focus, reps, guidance = (cells + ['', '', '', ''])[:4]
            self.weeks_table.append({'week': week, 'focus': focus, 'reps': reps, 'guidance': guidance})
        elif self._table_kind == 'volume':
            muscle_group, sets_per_week, frequency, where = (cells + ['', '', '', ''])[:4]
            self.volume_table.append({
                'muscle_group': muscle_group, 'sets_per_week': sets_per_week,
                'frequency': frequency, 'where': where,
            })


_CHART_JSON_RE = re.compile(
    r'<script[^>]*id=["\']period-chart-data["\'][^>]*>(.*?)</script>', re.DOTALL,
)


def _extract_chart_json(html: str) -> list[dict]:
    match = _CHART_JSON_RE.search(html)
    if not match:
        return []
    try:
        data = json.loads(match.group(1))
    except (ValueError, TypeError):
        return []
    return data if isinstance(data, list) else []


def parse_cardio_tab(html: str) -> dict | None:
    """`#tab-cardio` (formato juliana/bruno/henrique/johnespanha/thaislima)
    -> `{'sessions': [...]}` pronto pro schema, ou None se o HTML nao tem
    essa aba (a maioria dos clientes — cardio embutido por dia ou ausente,
    ver docstring de _CardioTabParser)."""
    parser = _CardioTabParser()
    parser.feed(html)
    if not parser.sessions:
        return None
    return {'sessions': parser.sessions}


def parse_periodization_tab(html: str) -> dict | None:
    """`#tab-period` -> `{'weeks_table', 'volume_table', 'note', 'chart'}`
    pronto pro schema, ou None se o HTML nao tem essa aba."""
    parser = _PeriodizationTabParser()
    parser.feed(html)
    if not parser.weeks_table:
        return None
    return {
        'weeks_table': parser.weeks_table,
        'volume_table': parser.volume_table,
        'note': parser.note,
        'chart': _extract_chart_json(html),
    }


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
    docstring do módulo).

    `cardio`/`periodization` são aditivos (schema.py) e OPCIONAIS — ficam de
    fora do payload quando o HTML não tem a aba correspondente (formato de
    aba dedicada, ver docstring de _CardioTabParser/_PeriodizationTabParser).
    Clientes sem aba dedicada (franciele/rafael) têm cardio e etapas
    auxiliares (mobilidade/ativação/coordenação) EMBUTIDOS por dia — ver
    _EmbeddedStageParser: os blocos auxiliares entram no `days` ANTES do
    bloco de Força de cada dia (mesma ordem do HTML), e o cardio embutido
    só vira `cardio.sessions` quando não existe aba dedicada (nunca compete
    com ela — ver PONTOS CRÍTICOS de _EmbeddedStageParser)."""
    days, skipped = parse_legacy_html(html)
    auxiliary_blocks_by_day, embedded_cardio_sessions = parse_embedded_stage_content(html)
    for day in days:
        auxiliary_blocks = auxiliary_blocks_by_day.get(day['day_id'])
        if auxiliary_blocks:
            day['blocks'] = auxiliary_blocks + day['blocks']
    payload = {
        'schema_version': SCHEMA_VERSION,
        'program_id': program_id,
        'program_label': program_label,
        'started_on': started_on,
        'weeks': weeks,
        'accent_variant': accent_variant,
        'days': days,
    }
    cardio = parse_cardio_tab(html)
    if cardio is None and embedded_cardio_sessions:
        cardio = {'sessions': embedded_cardio_sessions}
    if cardio is not None:
        payload['cardio'] = cardio
    periodization = parse_periodization_tab(html)
    if periodization is not None:
        payload['periodization'] = periodization
    return payload, skipped


__all__ = [
    'SkippedExercise',
    'build_program_payload_from_html',
    'parse_cardio_tab',
    'parse_embedded_stage_content',
    'parse_legacy_html',
    'parse_periodization_tab',
]
