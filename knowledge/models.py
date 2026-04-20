"""
ARQUIVO: modelos persistentes do indice de conhecimento interno.

POR QUE ELE EXISTE:
- guarda uma representacao serializavel e auditavel dos documentos e chunks usados pelo RAG interno.
- mantem a indexacao como camada de leitura acima do core, em linha com a arquitetura do projeto.

O QUE ESTE ARQUIVO FAZ:
1. registra documentos indexados do repositorio.
2. registra chunks recuperaveis com metadados de contexto.
3. preserva checksums e pesos de autoridade para reindexacao segura.

PONTOS CRITICOS:
- este indice nao deve armazenar `.env`, banco, logs ou blobs binarios.
- a recuperacao precisa continuar explainable; por isso guardamos caminho, heading e linhas.
"""

from django.db import models

from model_support.base import TimeStampedModel


class KnowledgeSourceKind(models.TextChoices):
    README = 'readme', 'README'
    DOC = 'doc', 'Documento'
    CODE = 'code', 'Codigo'
    TEST = 'test', 'Teste'
    TEMPLATE = 'template', 'Template'
    FRONTEND = 'frontend', 'Front-end'
    SPEC = 'spec', 'Spec'
    OTHER = 'other', 'Outro'


class KnowledgeDocument(TimeStampedModel):
    path = models.CharField(max_length=512, unique=True)
    title = models.CharField(max_length=255, blank=True)
    source_kind = models.CharField(max_length=24, choices=KnowledgeSourceKind.choices, db_index=True)
    authority_score = models.PositiveIntegerField(default=50, db_index=True)
    checksum = models.CharField(max_length=40, db_index=True)
    line_count = models.PositiveIntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    last_indexed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['path']

    def __str__(self):
        return self.path


class KnowledgeChunk(TimeStampedModel):
    document = models.ForeignKey(KnowledgeDocument, on_delete=models.CASCADE, related_name='chunks')
    ordinal = models.PositiveIntegerField()
    heading = models.CharField(max_length=255, blank=True)
    content = models.TextField()
    content_preview = models.CharField(max_length=280, blank=True)
    token_count = models.PositiveIntegerField(default=0)
    start_line = models.PositiveIntegerField(default=1)
    end_line = models.PositiveIntegerField(default=1)
    checksum = models.CharField(max_length=40, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['document__path', 'ordinal']
        constraints = [
            models.UniqueConstraint(fields=['document', 'ordinal'], name='unique_knowledge_chunk_document_ordinal'),
        ]

    def __str__(self):
        heading = f' :: {self.heading}' if self.heading else ''
        return f'{self.document.path}#{self.ordinal}{heading}'


class KnowledgeChunkEmbedding(TimeStampedModel):
    chunk = models.OneToOneField(KnowledgeChunk, on_delete=models.CASCADE, related_name='embedding')
    model = models.CharField(max_length=64, db_index=True)
    dimensions = models.PositiveIntegerField(default=0, db_index=True)
    checksum = models.CharField(max_length=40, db_index=True)
    vector = models.BinaryField()
    norm = models.FloatField(default=0.0)
    generated_at = models.DateTimeField(db_index=True)

    class Meta:
        ordering = ['chunk__document__path', 'chunk__ordinal']
        indexes = [
            models.Index(fields=['model', 'dimensions']),
        ]

    def __str__(self):
        return f'{self.chunk} [{self.model}:{self.dimensions}]'


__all__ = [
    'KnowledgeChunk',
    'KnowledgeChunkEmbedding',
    'KnowledgeDocument',
    'KnowledgeSourceKind',
]
