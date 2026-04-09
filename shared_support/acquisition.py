"""
Contrato compartilhado de canais de aquisicao e resolucao de origem.

POR QUE ELE EXISTE:
- evita duplicacao de taxonomia entre onboarding, students e futuras camadas analiticas.
- mantem a linguagem de atribuicao pequena, estavel e reutilizavel.
"""

ACQUISITION_CHANNEL_CHOICES = (
    ('', 'Nao informado'),
    ('referral', 'Indicacao'),
    ('instagram', 'Instagram'),
    ('walk_in', 'Passei na frente'),
    ('google', 'Google'),
    ('whatsapp', 'WhatsApp'),
    ('website', 'Site'),
    ('meta_ads', 'Anuncio Meta'),
    ('event', 'Evento'),
    ('other', 'Outro'),
    ('unidentified', 'Nao identificado'),
    ('legacy', 'Legado'),
)

ACQUISITION_CHANNEL_MODEL_CHOICES = tuple(
    choice for choice in ACQUISITION_CHANNEL_CHOICES if choice[0]
)

ACQUISITION_CHANNEL_LABELS = {
    key: label for key, label in ACQUISITION_CHANNEL_MODEL_CHOICES
}

SOURCE_RESOLUTION_METHOD_CHOICES = (
    ('', 'Nao definido'),
    ('intake_auto', 'Intake automatico'),
    ('manual_form', 'Formulario manual'),
    ('manual_review', 'Revisao manual'),
    ('declared_only', 'Somente declarado'),
    ('legacy', 'Legado'),
)

SOURCE_CONFIDENCE_CHOICES = (
    ('unknown', 'Desconhecida'),
    ('high', 'Alta'),
    ('medium', 'Media'),
    ('low', 'Baixa'),
)


def normalize_acquisition_channel(value: str | None) -> str:
    normalized_value = str(value or '').strip().lower()
    if normalized_value in ACQUISITION_CHANNEL_LABELS:
        return normalized_value
    return ''


def get_acquisition_channel_label(value: str | None) -> str:
    normalized_value = normalize_acquisition_channel(value)
    if normalized_value:
        return ACQUISITION_CHANNEL_LABELS[normalized_value]
    return 'Nao informado'


__all__ = [
    'ACQUISITION_CHANNEL_CHOICES',
    'ACQUISITION_CHANNEL_LABELS',
    'ACQUISITION_CHANNEL_MODEL_CHOICES',
    'SOURCE_CONFIDENCE_CHOICES',
    'SOURCE_RESOLUTION_METHOD_CHOICES',
    'get_acquisition_channel_label',
    'normalize_acquisition_channel',
]
