"""
ARQUIVO: comando de ingestao do conhecimento interno do projeto.

POR QUE ELE EXISTE:
- atualiza o indice do RAG interno a partir dos documentos e arquivos seguros do repositorio.

O QUE ESTE ARQUIVO FAZ:
1. descobre arquivos elegiveis.
2. quebra arquivos em chunks explainable.
3. sincroniza documentos ativos e inativos.
"""

from django.core.management.base import BaseCommand

from knowledge.indexing import sync_project_knowledge


class Command(BaseCommand):
    help = 'Indexa documentos e codigo seguro do repositorio para o RAG interno.'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Regera chunks mesmo sem mudanca de checksum.')
        parser.add_argument(
            '--with-embeddings',
            action='store_true',
            help='Tenta gerar embeddings para os chunks usando a feature flag e a chave configurada.',
        )

    def handle(self, *args, **options):
        result = sync_project_knowledge(
            force=bool(options['force']),
            with_embeddings=bool(options['with_embeddings']) or None,
        )

        self.stdout.write(
            self.style.SUCCESS(
                'Knowledge index atualizado: '
                f'{result["indexed_documents"]} documentos processados, '
                f'{result["regenerated_chunks"]} chunks regenerados, '
                f'{result["embeddings_regenerated"]} embeddings regenerados.'
            )
        )
