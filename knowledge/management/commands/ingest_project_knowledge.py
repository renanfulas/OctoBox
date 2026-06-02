"""
ARQUIVO: comando de ingestao do conhecimento interno do projeto.

POR QUE ELE EXISTE:
- atualiza o indice do RAG interno a partir dos documentos e arquivos seguros do repositorio.

O QUE ESTE ARQUIVO FAZ:
1. descobre arquivos elegiveis.
2. quebra arquivos em chunks explainable.
3. sincroniza documentos ativos e inativos.

SCHEMA:
- `knowledge` e um app SHARED: indexa no schema public, uma vez (nao por box).
- uso normal: python manage.py ingest_project_knowledge   (sem flags).
- --schema/--box continuam como escape hatch, normalmente desnecessarios.
"""

from django.core.management.base import BaseCommand, CommandError

from knowledge.indexing import sync_project_knowledge
from knowledge.schema_access import KnowledgeSchemaError, force_utf8_io, knowledge_schema


class Command(BaseCommand):
    help = 'Indexa documentos e codigo seguro do repositorio para o RAG interno (app tenant; usa --schema/--box).'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Regera chunks mesmo sem mudanca de checksum.')
        parser.add_argument(
            '--with-embeddings',
            action='store_true',
            help='Tenta gerar embeddings para os chunks usando a feature flag e a chave configurada.',
        )
        parser.add_argument('--schema', default=None, help='Schema de tenant a indexar (ex.: box_ragprobe).')
        parser.add_argument('--box', default=None, help='Slug do box a indexar (vira box_<slug>).')

    def handle(self, *args, **options):
        force_utf8_io()
        try:
            with knowledge_schema(schema=options.get('schema'), box=options.get('box')):
                result = sync_project_knowledge(
                    force=bool(options['force']),
                    with_embeddings=bool(options['with_embeddings']) or None,
                )
        except KnowledgeSchemaError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(
            self.style.SUCCESS(
                'Knowledge index atualizado: '
                f'{result["indexed_documents"]} documentos processados, '
                f'{result["regenerated_chunks"]} chunks regenerados, '
                f'{result["embeddings_regenerated"]} embeddings regenerados.'
            )
        )
