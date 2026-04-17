"""
ARQUIVO: inspetor leve do pipeline de importacao de leads.

POR QUE ELE EXISTE:
- permite contar leads validos e parar cedo antes de decidir o trilho de processamento.

O QUE ESTE ARQUIVO FAZ:
1. inspeciona CSV e VCF em streaming.
2. conta apenas leads com telefone valido.
3. para cedo conforme a faixa declarada pelo usuario.

PONTOS CRITICOS:
- o inspetor deve reposicionar o stream para reutilizacao posterior.
- a contagem precisa ignorar linhas vazias ou sem telefone valido.
- a decisao de stop-early deve reduzir custo sem esconder arquivos acima do teto suportado.
"""

import csv
import io
from dataclasses import dataclass

from operations.models import LeadImportDeclaredRange, LeadImportSourceType
from operations.services.contact_importer import clean_phone_number


SOURCE_PHONE_KEYS = {
    LeadImportSourceType.WHATSAPP_LIST: ('Telefone', 'Phone', 'phone_number', 'formatted_phone', 'Celular', 'Mobile', 'WhatsApp'),
    LeadImportSourceType.TECNOFIT_EXPORT: ('Celular', 'Telefone', 'Phone', 'phone_number', 'formatted_phone', 'Mobile', 'WhatsApp'),
    LeadImportSourceType.NEXTFIT_EXPORT: ('Telefone', 'Phone', 'phone_number', 'formatted_phone', 'Celular', 'Mobile', 'WhatsApp'),
}

DECLARED_RANGE_STOP_AFTER = {
    LeadImportDeclaredRange.UP_TO_200: 201,
    LeadImportDeclaredRange.FROM_201_TO_500: 501,
    LeadImportDeclaredRange.FROM_501_TO_2000: 2001,
}


@dataclass(frozen=True)
class LeadImportInspectionResult:
    source_type: str
    declared_range: str
    detected_lead_count: int
    stop_after_count: int
    threshold_crossed: bool
    inspection_complete: bool


def _get_stop_after_count(*, declared_range: str) -> int:
    return DECLARED_RANGE_STOP_AFTER.get(declared_range, DECLARED_RANGE_STOP_AFTER[LeadImportDeclaredRange.FROM_501_TO_2000])


def _build_csv_phone_keys(*, source_type: str) -> tuple[str, ...]:
    return SOURCE_PHONE_KEYS.get(source_type, SOURCE_PHONE_KEYS[LeadImportSourceType.WHATSAPP_LIST])


def _extract_valid_phone_from_row(*, row: dict, source_type: str) -> str:
    for key in _build_csv_phone_keys(source_type=source_type):
        raw_value = row.get(key)
        if not raw_value:
            continue
        cleaned_phone = clean_phone_number(str(raw_value))
        if cleaned_phone:
            return cleaned_phone
    return ''


def _inspect_csv_stream(*, file_stream, source_type: str, stop_after_count: int) -> tuple[int, bool]:
    text_stream = io.TextIOWrapper(file_stream, encoding='utf-8-sig', newline='', errors='replace')
    try:
        reader = csv.DictReader(text_stream)
        detected_count = 0
        for row in reader:
            if _extract_valid_phone_from_row(row=row, source_type=source_type):
                detected_count += 1
                if detected_count >= stop_after_count:
                    return detected_count, False
        return detected_count, True
    finally:
        text_stream.detach()


def _inspect_vcf_stream(*, file_stream, stop_after_count: int) -> tuple[int, bool]:
    text_stream = io.TextIOWrapper(file_stream, encoding='utf-8-sig', newline='', errors='replace')
    try:
        detected_count = 0
        current_contact_has_phone = False
        in_vcard = False

        for raw_line in text_stream:
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith('BEGIN:VCARD'):
                in_vcard = True
                current_contact_has_phone = False
                continue
            if not in_vcard:
                continue
            if line.startswith('TEL'):
                parts = line.split(':', 1)
                if len(parts) > 1 and clean_phone_number(parts[1]):
                    current_contact_has_phone = True
                continue
            if line.startswith('END:VCARD'):
                if current_contact_has_phone:
                    detected_count += 1
                    if detected_count >= stop_after_count:
                        return detected_count, False
                in_vcard = False
                current_contact_has_phone = False

        return detected_count, True
    finally:
        text_stream.detach()


def inspect_lead_import_stream(*, file_stream, source_type: str, declared_range: str) -> LeadImportInspectionResult:
    stop_after_count = _get_stop_after_count(declared_range=declared_range)
    file_stream.seek(0)
    try:
        if source_type == LeadImportSourceType.IPHONE_VCF:
            detected_lead_count, inspection_complete = _inspect_vcf_stream(
                file_stream=file_stream,
                stop_after_count=stop_after_count,
            )
        else:
            detected_lead_count, inspection_complete = _inspect_csv_stream(
                file_stream=file_stream,
                source_type=source_type,
                stop_after_count=stop_after_count,
            )
    finally:
        file_stream.seek(0)

    return LeadImportInspectionResult(
        source_type=source_type,
        declared_range=declared_range,
        detected_lead_count=detected_lead_count,
        stop_after_count=stop_after_count,
        threshold_crossed=detected_lead_count >= stop_after_count,
        inspection_complete=inspection_complete,
    )


__all__ = ['LeadImportInspectionResult', 'inspect_lead_import_stream']
