"""
ARQUIVO: comando CLI para consulta direta ao RAG interno.

POR QUE ELE EXISTE:
- permite que agentes de AI (Claude, Codex, Gemini) consultem o RAG do repositorio
  diretamente do terminal, sem depender de HTTP ou servidor rodando.
- funciona 100% offline com busca lexical; nao requer nenhuma chave de API.

O QUE ESTE ARQUIVO FAZ:
1. recebe uma pergunta como argumento de linha de comando.
2. executa search_project_knowledge() contra o banco local.
3. imprime resultado como JSON estruturado (--json) ou leitura humana (default).

COMO USAR (agente de AI):
    python manage.py search_project_knowledge "como funciona o intake?" --json --limit 5

COMO USAR (humano):
    python manage.py search_project_knowledge "arquitetura do OctoBox"
    python manage.py search_project_knowledge "finance queue" --limit 3

PONTOS CRITICOS:
- o banco precisa ter sido indexado antes via: python manage.py ingest_project_knowledge
- sem embeddings ativos, a busca retorna resultados lexicais (excelentes para docs e codigo).
- com embeddings ativos, o resultado inclui semantic_score alem do lexical_score.
"""

from __future__ import annotations

import json

from django.core.management.base import BaseCommand

from knowledge.retrieval import search_project_knowledge


class Command(BaseCommand):
    help = 'Consulta o RAG interno do projeto. Uso: python manage.py search_project_knowledge "pergunta" [--limit N] [--json]'

    def add_arguments(self, parser):
        parser.add_argument(
            'question',
            type=str,
            help='Pergunta ou termo de busca (ex: "como funciona o intake?").',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=5,
            help='Numero maximo de resultados (default: 5, max util: 10).',
        )
        parser.add_argument(
            '--json',
            action='store_true',
            dest='output_json',
            help='Retorna saida como JSON estruturado (ideal para consumo por agentes de AI).',
        )

    def handle(self, *args, **options):
        question = options['question'].strip()
        limit = max(1, min(options['limit'], 20))
        output_json = options['output_json']

        if not question:
            self.stderr.write(self.style.ERROR('Pergunta nao pode ser vazia.'))
            return

        hits = search_project_knowledge(question=question, limit=limit)

        if output_json:
            self._print_json(question=question, hits=hits)
        else:
            self._print_human(question=question, hits=hits)

    def _print_json(self, *, question: str, hits) -> None:
        output = {
            'question': question,
            'total': len(hits),
            'results': [
                {
                    'rank': index,
                    'path': hit.path,
                    'title': hit.title,
                    'heading': hit.heading,
                    'start_line': hit.start_line,
                    'end_line': hit.end_line,
                    'score': hit.score,
                    'lexical_score': hit.lexical_score,
                    'semantic_score': hit.semantic_score,
                    'authority_score': hit.authority_score,
                    'source_kind': hit.source_kind,
                    'reasons': hit.reasons,
                    'preview': hit.preview,
                    'content': hit.content,
                }
                for index, hit in enumerate(hits, start=1)
            ],
        }
        self.stdout.write(json.dumps(output, ensure_ascii=False, indent=2))

    def _print_human(self, *, question: str, hits) -> None:
        self.stdout.write(self.style.SUCCESS(f'\nRAG — Pergunta: "{question}"'))
        self.stdout.write(self.style.SUCCESS(f'Resultados: {len(hits)}\n'))

        if not hits:
            self.stdout.write(self.style.WARNING('Nenhum resultado encontrado. O indice esta vazio ou a pergunta nao tem correspondencia.'))
            self.stdout.write('Execute: python manage.py ingest_project_knowledge')
            return

        for index, hit in enumerate(hits, start=1):
            heading_label = f' :: {hit.heading}' if hit.heading else ''
            self.stdout.write(
                self.style.HTTP_INFO(
                    f'[{index}] {hit.path}{heading_label} '
                    f'(linhas {hit.start_line}-{hit.end_line}) '
                    f'[score={hit.score} | auth={hit.authority_score}]'
                )
            )
            self.stdout.write(f'    {hit.preview}')
            self.stdout.write(f'    razoes: {", ".join(hit.reasons)}')
            self.stdout.write('')
