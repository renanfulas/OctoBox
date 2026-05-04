"""
ARQUIVO: descoberta e classificacao das fontes do conhecimento interno.

POR QUE ELE EXISTE:
- limita o RAG a arquivos seguros e relevantes do repositorio.
- aplica a hierarquia de autoridade documental do projeto como peso de retrieval.

O QUE ESTE ARQUIVO FAZ:
1. percorre somente caminhos permitidos.
2. classifica cada arquivo por tipo e peso de autoridade.
3. evita logs, bancos, ambientes e artefatos binarios.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from .models import KnowledgeSourceKind


ALLOWED_EXTENSIONS = {'.md', '.py', '.html', '.js', '.css', '.json', '.txt'}
INCLUDE_ROOTS = [
    Path('README.md'),
    Path('docs'),
    Path('.specs/codebase'),
    Path('access'),
    Path('api'),
    Path('auditing'),
    Path('catalog'),
    Path('communications'),
    Path('config'),
    Path('dashboard'),
    Path('finance'),
    Path('guide'),
    Path('integrations'),
    Path('jobs'),
    Path('model_support'),
    Path('onboarding'),
    Path('operations'),
    Path('quick_sales'),
    Path('shared_support'),
    Path('students'),
    Path('student_app'),
    Path('student_identity'),
    Path('templates'),
    Path('tests'),
    Path('static/js'),
    Path('static/css'),
]
SKIP_PARTS = {
    '.git',
    '.omx',
    '.venv',
    '__pycache__',
    'node_modules',
    'staticfiles',
    'tmp',
    'backups',
}
MAX_FILE_BYTES = 300_000


@dataclass(slots=True)
class SourceDocument:
    relative_path: str
    title: str
    source_kind: str
    authority_score: int
    content: str
    line_count: int
    metadata: dict
    checksum: str
    extension: str


def iter_project_sources(base_dir: Path) -> list[SourceDocument]:
    discovered: list[SourceDocument] = []
    seen_paths: set[str] = set()
    for root in INCLUDE_ROOTS:
        candidate = base_dir / root
        if not candidate.exists():
            continue
        if candidate.is_file():
            source = _read_source(base_dir=base_dir, file_path=candidate)
            if source:
                discovered.append(source)
                seen_paths.add(source.relative_path)
            continue

        for file_path in candidate.rglob('*'):
            if not file_path.is_file():
                continue
            if any(part in SKIP_PARTS for part in file_path.parts):
                continue
            source = _read_source(base_dir=base_dir, file_path=file_path)
            if not source or source.relative_path in seen_paths:
                continue
            discovered.append(source)
            seen_paths.add(source.relative_path)
    return sorted(discovered, key=lambda item: item.relative_path)


def _read_source(*, base_dir: Path, file_path: Path) -> SourceDocument | None:
    if file_path.suffix.lower() not in ALLOWED_EXTENSIONS:
        return None
    try:
        if file_path.stat().st_size > MAX_FILE_BYTES:
            return None
    except OSError:
        return None

    relative_path = file_path.relative_to(base_dir).as_posix()
    if any(part in SKIP_PARTS for part in Path(relative_path).parts):
        return None

    try:
        raw = file_path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        return None

    content = raw.strip()
    if not content:
        return None

    source_kind, authority_score = classify_source(relative_path)
    title = _infer_title(relative_path, content)
    checksum = hashlib.sha1(content.encode('utf-8')).hexdigest()
    return SourceDocument(
        relative_path=relative_path,
        title=title,
        source_kind=source_kind,
        authority_score=authority_score,
        content=content,
        line_count=len(content.splitlines()),
        metadata={'extension': file_path.suffix.lower()},
        checksum=checksum,
        extension=file_path.suffix.lower(),
    )


def classify_source(relative_path: str) -> tuple[str, int]:
    if relative_path == 'README.md':
        return KnowledgeSourceKind.README, 95
    if relative_path.startswith('docs/architecture/'):
        return KnowledgeSourceKind.DOC, 90
    if relative_path.startswith('docs/plans/'):
        return KnowledgeSourceKind.DOC, 85
    if relative_path.startswith('docs/reference/'):
        return KnowledgeSourceKind.DOC, 80
    if relative_path.startswith('docs/rollout/'):
        return KnowledgeSourceKind.DOC, 75
    if relative_path.startswith('docs/experience/'):
        return KnowledgeSourceKind.DOC, 70
    if relative_path.startswith('docs/diagnostics/') or relative_path.startswith('docs/reports/'):
        return KnowledgeSourceKind.DOC, 60
    if relative_path.startswith('docs/history/'):
        return KnowledgeSourceKind.DOC, 50
    if relative_path.startswith('docs/coaching/'):
        return KnowledgeSourceKind.DOC, 85
    if relative_path.startswith('docs/'):
        return KnowledgeSourceKind.DOC, 68
    if relative_path.startswith('.specs/codebase/'):
        return KnowledgeSourceKind.SPEC, 78
    if relative_path.startswith('tests/'):
        return KnowledgeSourceKind.TEST, 98
    if relative_path.endswith('.py'):
        return KnowledgeSourceKind.CODE, 100
    if relative_path.startswith('templates/') or relative_path.endswith('.html'):
        return KnowledgeSourceKind.TEMPLATE, 88
    if relative_path.startswith('static/js/') or relative_path.startswith('static/css/'):
        return KnowledgeSourceKind.FRONTEND, 84
    return KnowledgeSourceKind.OTHER, 55


def _infer_title(relative_path: str, content: str) -> str:
    if relative_path.endswith('.md'):
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith('#'):
                return stripped.lstrip('#').strip()[:255]
    return Path(relative_path).name[:255]

