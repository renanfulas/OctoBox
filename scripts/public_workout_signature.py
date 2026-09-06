"""
ARQUIVO: assinatura de conteudo das paginas publicas de treino (/renan/).

POR QUE ELE EXISTE:
- as 7 paginas em templates/public_workouts/ vao ser refatoradas de HTML
  autocontido para template + CSS + JS compartilhados. A refatoracao pode
  mudar markup e classes a vontade, mas NAO pode mudar o conteudo que o
  aluno le nem o contrato de dados que o tracker grava no localStorage.
- sem uma baseline explicita, um exercicio perdido no meio de 600 KB de
  HTML so aparece quando o aluno abre o treino na academia.

O QUE ESTE ARQUIVO FAZ:
1. renderiza cada plano publico e extrai uma assinatura normalizada:
   ids, data-key, hrefs, texto visivel e contagem de blocos semanticos.
2. grava/compara essa assinatura contra tests/golden/public_workouts/.

PONTOS CRITICOS:
- classes CSS ficam DE FORA da assinatura de proposito: elas mudam nas
  fases 2 e 3. O que nao pode mudar e o conteudo, nao o vestuario.
- os data-key sao o contrato do localStorage do aluno. Se um data-key
  some ou muda, o historico de carga daquele exercicio fica orfao.
- usa so html.parser da stdlib — o projeto nao tem BeautifulSoup/lxml.

USO:
    python scripts/public_workout_signature.py write    # grava a baseline
    python scripts/public_workout_signature.py check    # compara e sai !=0
"""

from __future__ import annotations

import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
GOLDEN_DIR = BASE_DIR / 'tests' / 'golden' / 'public_workouts'

# Blocos que carregam significado de treino. A contagem deles e a defesa
# barata contra "sumiu uma sessao inteira" — o texto pega o resto.
SEMANTIC_BLOCKS = ('session', 'ex', 'tracker', 'c-card', 'dp', 'sets-tbl', 'wk-box')

# Conteudo que nao e texto lido pelo aluno.
SKIPPED_CONTENT_TAGS = frozenset({'script', 'style', 'title'})

_WHITESPACE = re.compile(r'\s+')


def _normalize_text(value: str) -> str:
    return _WHITESPACE.sub(' ', value).strip()


class _SignatureParser(HTMLParser):
    """Extrai a assinatura de conteudo de uma pagina publica de treino."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: list[str] = []
        self.data_keys: list[str] = []
        self.hrefs: list[str] = []
        self.text: list[str] = []
        self.data_islands: list[str] = []
        self.block_counts: dict[str, int] = {name: 0 for name in SEMANTIC_BLOCKS}
        self._skip_depth = 0
        self._in_data_island = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {name: (value or '') for name, value in attrs}

        if tag in SKIPPED_CONTENT_TAGS:
            self._skip_depth += 1
            # <script type="application/json"> carrega CONTEUDO (a
            # periodizacao que o aluno le no grafico). Antes esses dados
            # eram um `const` dentro do <script>, invisiveis para a
            # assinatura; agora entram.
            if tag == 'script' and attributes.get('type') == 'application/json':
                self._in_data_island = True

        element_id = attributes.get('id')
        # Ids de <script>/<style> sao infraestrutura, nao conteudo — mesma
        # razao pela qual href de <link> fica de fora.
        if element_id and tag not in SKIPPED_CONTENT_TAGS:
            self.ids.append(element_id)

        data_key = attributes.get('data-key')
        if data_key:
            self.data_keys.append(data_key)

        # So <a href>: sao os links que o aluno clica (MuscleWiki, outros
        # treinos). <link rel=stylesheet|manifest|icon> e infraestrutura e
        # muda a cada refatoracao de CSS — nao e conteudo.
        if tag == 'a':
            href = attributes.get('href')
            if href:
                self.hrefs.append(href)

        # Classes nao entram na assinatura, mas a CONTAGEM dos blocos
        # semanticos entra: e o que pega "sumiu um exercicio".
        classes = attributes.get('class', '').split()
        for name in SEMANTIC_BLOCKS:
            if name in classes:
                self.block_counts[name] += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in SKIPPED_CONTENT_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1
            if tag == 'script':
                self._in_data_island = False

    def handle_data(self, data: str) -> None:
        if self._in_data_island:
            island = _normalize_text(data)
            if island:
                self.data_islands.append(island)
            return
        if self._skip_depth > 0:
            return
        normalized = _normalize_text(data)
        if normalized:
            self.text.append(normalized)


def build_signature(html: str) -> dict[str, object]:
    parser = _SignatureParser()
    parser.feed(html)
    parser.close()
    return {
        'ids': parser.ids,
        'data_keys': parser.data_keys,
        'hrefs': parser.hrefs,
        'text': parser.text,
        'data_islands': parser.data_islands,
        'block_counts': parser.block_counts,
    }


def _render_plan(slug: str) -> str:
    """Renderiza a pagina publica pela view real, nao pelo arquivo cru.

    Passar pela view e o ponto: a fase 1 move a injecao de <head> e do
    service worker para dentro do template, e a assinatura precisa
    enxergar a saida final, nao o arquivo em disco.
    """
    from django.test import Client

    response = Client().get(f'/renan/{slug}')
    if response.status_code != 200:
        raise SystemExit(f'/renan/{slug} respondeu {response.status_code}, esperado 200')
    return response.content.decode('utf-8')


def iter_slugs() -> tuple[str, ...]:
    from student_app.views.public_workout_views import PUBLIC_WORKOUT_LIBRARY

    return tuple(PUBLIC_WORKOUT_LIBRARY)


def signature_for(slug: str) -> dict[str, object]:
    return build_signature(_render_plan(slug))


def golden_path(slug: str) -> Path:
    return GOLDEN_DIR / f'{slug}.json'


def write_all() -> int:
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    for slug in iter_slugs():
        signature = signature_for(slug)
        golden_path(slug).write_text(
            json.dumps(signature, ensure_ascii=False, indent=2) + '\n',
            encoding='utf-8',
        )
        counts = signature['block_counts']
        print(
            f'{slug:<12} {len(signature["text"]):>5} textos '
            f'{len(signature["hrefs"]):>4} links '
            f'{len(signature["data_keys"]):>4} data-key '
            f'{counts["ex"]:>3} exercicios'
        )
    return 0


def check_all() -> int:
    failures = 0
    for slug in iter_slugs():
        path = golden_path(slug)
        if not path.exists():
            print(f'FALTA baseline para {slug}: {path}')
            failures += 1
            continue

        expected = json.loads(path.read_text(encoding='utf-8'))
        actual = signature_for(slug)
        if expected == actual:
            print(f'ok   {slug}')
            continue

        failures += 1
        print(f'DIFF {slug}')
        for field in ('ids', 'data_keys', 'hrefs', 'text'):
            removed = [item for item in expected[field] if item not in actual[field]]
            added = [item for item in actual[field] if item not in expected[field]]
            for item in removed[:5]:
                print(f'  - {field}: {item[:120]}')
            for item in added[:5]:
                print(f'  + {field}: {item[:120]}')
        if expected['block_counts'] != actual['block_counts']:
            print(f'  ! block_counts: {expected["block_counts"]} -> {actual["block_counts"]}')
    return 1 if failures else 0


def main(argv: list[str]) -> int:
    import os

    import django

    sys.path.insert(0, str(BASE_DIR))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
    django.setup()

    # setup_test_environment() e o que injeta 'testserver' em ALLOWED_HOSTS.
    # Sem isso o Client leva 400 do CommonMiddleware antes de chegar na view.
    from django.test.utils import setup_test_environment

    setup_test_environment()

    command = argv[1] if len(argv) > 1 else 'check'
    if command == 'write':
        return write_all()
    if command == 'check':
        return check_all()
    print(__doc__)
    return 2


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
