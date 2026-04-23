"""
ARQUIVO: importador de contatos operacionais.

POR QUE ELE EXISTE:
- recebe listas externas e cria `StudentIntake` de forma segura e previsivel.
- aplica higienizacao minima para telefone e email antes da persistencia.
- protege a operacao contra duplicatas silenciosas e devolve um relatorio util.

O QUE ESTE ARQUIVO FAZ:
1. normaliza telefone e email.
2. detecta duplicatas no proprio arquivo.
3. detecta duplicatas no banco via `phone_lookup_index`.
4. importa contatos em lote com `bulk_create`.
5. devolve relatorio com sucesso, duplicatas e erros estruturados.

PONTOS CRITICOS:
- `StudentIntake` usa `bulk_create`, entao o `phone_lookup_index` precisa ser preenchido antes do insert.
- busca por telefone deve usar indice deterministico e nao o campo criptografado bruto.
- duplicata e warning operacional; o owner precisa receber contexto para agir manualmente.
"""

import csv
import io
import os
import re

from django.db import transaction

from onboarding.models import IntakeSource, IntakeStatus, StudentIntake
from shared_support.crypto_fields import generate_blind_index
from shared_support.validators import validate_file_security

# ðŸš€ SeguranÃ§a de Elite (Ghost Hardening): Resource Exhaustion Limit
# Evita que arquivos gigantes (bombas de CSV) derrubem o servidor.
MAX_IMPORT_FILE_SIZE = 50 * 1024 * 1024  # 50MB (Suficiente para ~500k contatos)
SQLITE_SAFE_LOOKUP_BATCH_SIZE = 500

SOURCE_FIELD_SYNONYMS = {
    'name': ['Nome', 'Name', 'saved_name', 'public_name', 'Contato', 'First Name', 'Contact'],
    'phone': ['Telefone', 'Phone', 'phone_number', 'formatted_phone', 'Celular', 'Mobile', 'WhatsApp'],
    'email': ['Email', 'E-mail', 'Mail'],
}

SOURCE_HEADER_MAPS = {
    'whatsapp': {'name': 'Nome', 'phone': 'Telefone', 'email': 'Email'},
    'tecnofit': {'name': 'Nome', 'phone': 'Celular', 'email': 'E-mail'},
    'nextfit': {'name': 'Nome', 'phone': 'Telefone', 'email': 'Email'},
    'ios_vcard': {'name': 'Nome', 'phone': 'Telefone', 'email': 'Email'},
}


def clean_phone_number(phone_str):
    """
    Normaliza o numero de telefone para salvar apenas digitos.
    Garante o prefixo 55 (Brasil) se for um numero nacional valido.
    """
    if not phone_str:
        return ""

    digits = re.sub(r'\D', '', str(phone_str))
    if not digits:
        return ""

    if len(digits) in (10, 11) and not digits.startswith('55'):
        digits = f"55{digits}"

    return digits


def sanitize_csv_formula(value):
    """
    Previne injecao de formulas em planilhas (Excel/Google Sheets).
    Se o valor comecar com caracteres que acionam formulas (=, +, -, @),
    adiciona uma aspa simples (') no inicio para neutralizar.
    """
    if not value or not isinstance(value, str):
        return value

    dangerous_prefixes = ('=', '+', '-', '@', '\t', '\r')
    if value.startswith(dangerous_prefixes):
        return f"'{value}"

    return value


def normalize_email(value):
    if not value:
        return ""
    return str(value).strip().lower()


def get_source_search_keys(source_platform):
    mapping = SOURCE_HEADER_MAPS.get(source_platform, SOURCE_HEADER_MAPS['whatsapp'])
    return {
        'name': [mapping['name']] + SOURCE_FIELD_SYNONYMS['name'],
        'phone': [mapping['phone']] + SOURCE_FIELD_SYNONYMS['phone'],
        'email': [mapping['email']] + SOURCE_FIELD_SYNONYMS['email'],
    }


def extract_contact_fields(row, source_platform):
    search_keys = get_source_search_keys(source_platform)
    name = next((str(row[key]) for key in search_keys['name'] if key in row and row[key]), "")
    phone = next((str(row[key]) for key in search_keys['phone'] if key in row and row[key]), "")
    email = next((str(row[key]) for key in search_keys['email'] if key in row and row[key]), "")
    return name, phone, email


def build_duplicate_detail(
    *,
    row_number,
    name,
    phone,
    normalized_phone,
    phone_lookup_index,
    email,
    normalized_email,
    reason,
    existing_intake=None,
):
    detail = {
        'row_number': row_number,
        'name': name,
        'phone': phone,
        'normalized_phone': normalized_phone,
        'phone_lookup_index': phone_lookup_index,
        'email': email,
        'normalized_email': normalized_email,
        'reason': reason,
    }
    if existing_intake is not None:
        detail['existing_intake_id'] = existing_intake.id
        detail['existing_intake_name'] = existing_intake.full_name
    return detail


def append_error_detail(report, *, row_number, name, phone, email, reason_code, reason_message):
    detail = {
        'row_number': row_number,
        'name': name,
        'phone': phone,
        'email': email,
        'reason_code': reason_code,
        'reason_message': reason_message,
    }
    report['errors'] += 1
    report['details'].append(reason_message)
    report['error_details'].append(detail)


def build_file_level_error_report(*, reason_code, reason_message):
    return {
        'success': 0,
        'duplicates': 0,
        'errors': 1,
        'details': [reason_message],
        'duplicate_details': [],
        'error_details': [{'reason_code': reason_code, 'reason_message': reason_message}],
    }


def iter_lookup_batches(values, batch_size=SQLITE_SAFE_LOOKUP_BATCH_SIZE):
    batch = []
    for value in values:
        batch.append(value)
        if len(batch) >= batch_size:
            yield batch
            batch = []
    if batch:
        yield batch


def check_duplicate_lead(phone, email=None):
    """
    Verifica se o contato ja existe no StudentIntake para evitar spam.
    """
    if phone:
        phone_lookup_index = generate_blind_index(phone)
        if phone_lookup_index and StudentIntake.objects.filter(phone_lookup_index=phone_lookup_index).exists():
            return True
    return False


def import_contacts_from_list(contact_list, source_platform='whatsapp', actor=None):
    """
    Importa contatos a partir de uma lista de dicionarios (JSON ou processados).
    Deduplica e higieniza no processo usando Batch Processing (Epic 8 Performance).
    """
    report = {
        'success': 0,
        'duplicates': 0,
        'errors': 0,
        'details': [],
        'duplicate_details': [],
        'error_details': [],
    }

    source_map = {
        'whatsapp': IntakeSource.WHATSAPP,
        'tecnofit': IntakeSource.IMPORT,
        'nextfit': IntakeSource.IMPORT,
        'ios_vcard': IntakeSource.IMPORT,
    }
    db_source = source_map.get(source_platform, IntakeSource.IMPORT)

    phone_lookup_indexes_to_check = set()
    for row in contact_list:
        _, phone, _ = extract_contact_fields(row, source_platform)
        normalized_phone = clean_phone_number(phone)
        phone_lookup_index = generate_blind_index(normalized_phone)
        if phone_lookup_index:
            phone_lookup_indexes_to_check.add(phone_lookup_index)

    existing_intakes_by_phone_index = {}
    if phone_lookup_indexes_to_check:
        for lookup_batch in iter_lookup_batches(phone_lookup_indexes_to_check):
            existing_intakes = (
                StudentIntake.objects.filter(phone_lookup_index__in=lookup_batch)
                .only('id', 'full_name', 'phone_lookup_index')
                .order_by('id')
            )
            existing_intakes_by_phone_index.update(
                {
                    intake.phone_lookup_index: intake
                    for intake in existing_intakes
                    if intake.phone_lookup_index
                }
            )

    to_create = []
    seen_phone_lookup_indexes = set()
    seen_emails = set()

    for row_idx, row in enumerate(contact_list, start=1):
        name = ""
        phone = ""
        email = ""
        try:
            name, phone, email = extract_contact_fields(row, source_platform)
            name = name.strip() if name else ""
            email = email.strip() if email else ""
            normalized_email = normalize_email(email)

            name = sanitize_csv_formula(name)
            email = sanitize_csv_formula(email)

            cleaned_phone = clean_phone_number(phone)
            phone_lookup_index = generate_blind_index(cleaned_phone)

            if not name and not cleaned_phone:
                continue

            if not cleaned_phone:
                append_error_detail(
                    report,
                    row_number=row_idx,
                    name=name,
                    phone=phone,
                    email=email,
                    reason_code='invalid_phone',
                    reason_message=f"Item {row_idx}: Telefone ausente ou invalido ({phone})",
                )
                continue

            if not name:
                name = f"Contato Importado ({cleaned_phone[-4:]})"

            duplicate_reason = ''
            existing_intake = None
            if phone_lookup_index and phone_lookup_index in seen_phone_lookup_indexes:
                duplicate_reason = 'duplicate_in_file_phone'
            elif normalized_email and normalized_email in seen_emails:
                duplicate_reason = 'duplicate_in_file_email'
            elif phone_lookup_index and phone_lookup_index in existing_intakes_by_phone_index:
                duplicate_reason = 'duplicate_in_database_phone'
                existing_intake = existing_intakes_by_phone_index[phone_lookup_index]

            if duplicate_reason:
                report['duplicates'] += 1
                report['duplicate_details'].append(
                    build_duplicate_detail(
                        row_number=row_idx,
                        name=name,
                        phone=phone,
                        normalized_phone=cleaned_phone,
                        phone_lookup_index=phone_lookup_index,
                        email=email,
                        normalized_email=normalized_email,
                        reason=duplicate_reason,
                        existing_intake=existing_intake,
                    )
                )
                continue

            to_create.append(
                StudentIntake(
                    full_name=name,
                    phone=cleaned_phone,
                    phone_lookup_index=phone_lookup_index,
                    email=email,
                    source=db_source,
                    status=IntakeStatus.NEW,
                    assigned_to=actor,
                    notes=f"Importado via {source_platform.upper()} (Batch Process).",
                )
            )

            if phone_lookup_index:
                seen_phone_lookup_indexes.add(phone_lookup_index)
            if normalized_email:
                seen_emails.add(normalized_email)

        except Exception as exc:
            append_error_detail(
                report,
                row_number=row_idx,
                name=name or 'Sem Nome',
                phone=phone,
                email=email,
                reason_code='unexpected_error',
                reason_message=f"Item {row_idx} ({name or 'Sem Nome'}): {str(exc)}",
            )

    if to_create:
        with transaction.atomic():
            StudentIntake.objects.bulk_create(to_create, batch_size=500)
            report['success'] = len(to_create)

    return report


def parse_vcard(text):
    """
    Extrai contatos de um arquivo .vcf (VCard).
    Busca o Nome (FN ou N) e Varias propriedades TEL/EMAIL.
    """
    contacts = []
    current_contact = {}
    lines = text.splitlines()
    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line.startswith('BEGIN:VCARD'):
            current_contact = {}
        elif line.startswith('FN:'):
            current_contact['Nome'] = line.split(':', 1)[1]
        elif line.startswith('N:') and 'Nome' not in current_contact:
            parts = line.split(':', 1)[1].split(';')
            if len(parts) >= 2:
                current_contact['Nome'] = f"{parts[1]} {parts[0]}".strip()
            elif len(parts) == 1:
                current_contact['Nome'] = parts[0]
        elif line.startswith('TEL'):
            parts = line.split(':', 1)
            if len(parts) > 1 and 'Telefone' not in current_contact:
                current_contact['Telefone'] = parts[1]
        elif line.startswith('EMAIL'):
            parts = line.split(':', 1)
            if len(parts) > 1 and 'Email' not in current_contact:
                current_contact['Email'] = parts[1]
        elif line.startswith('END:VCARD'):
            if current_contact:
                contacts.append(current_contact)
                current_contact = {}
    return contacts


def import_contacts_from_stream(file_stream, source_platform='whatsapp', actor=None):
    """
    Le o stream de um arquivo CSV ou VCF e importa os contatos.
    """
    if hasattr(file_stream, 'name'):
        temp_path = file_stream.name
        allowed_mimes = [
            'text/csv',
            'application/vnd.ms-excel',
            'text/vcard',
            'text/x-vcard',
            'text/plain',
        ]
        try:
            validate_file_security(temp_path, max_size_mb=15, allowed_mimes=allowed_mimes)
        except Exception as exc:
            return build_file_level_error_report(
                reason_code='file_validation_error',
                reason_message=str(exc),
            )

    try:
        file_stream.seek(0, os.SEEK_END)
        total_size = file_stream.tell()
        file_stream.seek(0)

        if total_size > MAX_IMPORT_FILE_SIZE:
            message = f"Arquivo muito grande ({total_size // (1024*1024)}MB). Limite de {MAX_IMPORT_FILE_SIZE // (1024*1024)}MB."
            return build_file_level_error_report(
                reason_code='file_too_large',
                reason_message=message,
            )

        raw_bytes = file_stream.read()
        try:
            decoded_content = raw_bytes.decode('utf-8-sig')
        except UnicodeDecodeError:
            decoded_content = raw_bytes.decode('latin-1')

        if source_platform == 'ios_vcard':
            contact_list = parse_vcard(decoded_content)
        else:
            buffer = io.StringIO(decoded_content)
            reader = csv.DictReader(buffer)
            contact_list = list(reader)
    except Exception as exc:
        message = f"Erro ao ler arquivo: {str(exc)}"
        return build_file_level_error_report(
            reason_code='file_read_error',
            reason_message=message,
        )

    return import_contacts_from_list(contact_list, source_platform=source_platform, actor=actor)
