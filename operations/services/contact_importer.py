import csv
import io
import re
import os
from django.db import transaction
from onboarding.models import StudentIntake, IntakeSource, IntakeStatus
from shared_support.validators import validate_file_security

# 🚀 Segurança de Elite (Ghost Hardening): Resource Exhaustion Limit
# Evita que arquivos gigantes (bombas de CSV) derrubem o servidor.
MAX_IMPORT_FILE_SIZE = 50 * 1024 * 1024  # 50MB (Suficiente para ~500k contatos)

def clean_phone_number(phone_str):
    """
    Normaliza o número de telefone para salvar apenas dígitos.
    Garante o prefixo 55 (Brasil) se for um número nacional válido.
    """
    if not phone_str:
        return ""
    
    # Remove tudo que não for dígito
    digits = re.sub(r'\D', '', str(phone_str))
    
    if not digits:
        return ""

    # Cenários Brasil comum:
    # 1. Já veio com 55 + DDD + 9 dígitos = 13 dígitos
    # 2. DDD + 9 dígitos = 11 dígitos
    # 3. DDD + 8 dígitos = 10 dígitos (fixo ou antigo)
    
    if len(digits) == 11 and digits.startswith('55'):
         # Pode ser DDD=11 + 9 dígitos = 11? Não, 55 + 11 + 9 = 13.
         pass

    if len(digits) in (10, 11) and not digits.startswith('55'):
        # Adiciona o 55 (Brasil)
        digits = f"55{digits}"
        
    return digits

def sanitize_csv_formula(value):
    """
    Previne injeção de fórmulas em planilhas (Excel/Google Sheets).
    Se o valor começar com caracteres que acionam fórmulas (=, +, -, @),
    adiciona uma aspa simples (') no início para neutralizar.
    """
    if not value or not isinstance(value, str):
        return value
    
    # Caracteres perigosos que acionam execução de fórmulas em planilhas
    DANGEROUS_PREFIXES = ('=', '+', '-', '@', '\t', '\r')
    
    if value.startswith(DANGEROUS_PREFIXES):
        # A aspa simples é o padrão da indústria para dizer ao Excel: 
        # "Isso é apenas texto, não execute".
        return f"'{value}"
    
    return value

def check_duplicate_lead(phone, email=None):
    """
    Verifica se o contato já existe no StudentIntake para evitar spam.
    """
    if phone:
        if StudentIntake.objects.filter(phone=phone).exists():
            return True
    if email:
        if StudentIntake.objects.filter(email=email).exists():
            return True
    return False

def import_contacts_from_list(contact_list, source_platform='whatsapp', actor=None):
    """
    Importa contatos a partir de uma lista de dicionários (JSON ou processados).
    Deduplica e higieniza no processo usando Batch Processing (Epic 8 Performance).
    """
    report = {'success': 0, 'duplicates': 0, 'errors': 0, 'details': []}
    
    source_map = {
        'whatsapp': IntakeSource.WHATSAPP,
        'tecnofit': IntakeSource.IMPORT,
        'nextfit': IntakeSource.IMPORT,
        'ios_vcard': IntakeSource.IMPORT,
    }
    db_source = source_map.get(source_platform, IntakeSource.IMPORT)

    # 🚀 Otimização Game Dev (Latency Zero): Memory Safety
    # Em vez de carregar 1 milhão de telefones, buscamos apenas os que estão nesta lista.
    all_phones_to_check = []
    all_emails_to_check = []
    for row in contact_list:
        p = next((str(row[k]) for k in search_phone if k in row and row[k]), "")
        e = next((str(row[k]) for k in search_email if k in row and row[k]), "")
        cp = clean_phone_number(p)
        if cp: all_phones_to_check.append(cp)
        if e: all_emails_to_check.append(e.strip())

    existing_phones = set(StudentIntake.objects.filter(phone__in=all_phones_to_check).values_list('phone', flat=True))
    existing_emails = set(StudentIntake.objects.filter(email__in=all_emails_to_check).exclude(email='').values_list('email', flat=True))

    # Mapeamento Inteligente (Sinônimos Globais)
    SINONIMOS = {
        'name': ['Nome', 'Name', 'saved_name', 'public_name', 'Contato', 'First Name', 'Contact'],
        'phone': ['Telefone', 'Phone', 'phone_number', 'formatted_phone', 'Celular', 'Mobile', 'WhatsApp'],
        'email': ['Email', 'E-mail', 'Mail']
    }

    header_maps = {
        'whatsapp': {'name': 'Nome', 'phone': 'Telefone', 'email': 'Email'},
        'tecnofit': {'name': 'Nome', 'phone': 'Celular', 'email': 'E-mail'},
        'nextfit': {'name': 'Nome', 'phone': 'Telefone', 'email': 'Email'},
    }
    mapping = header_maps.get(source_platform, header_maps['whatsapp'])

    search_name = [mapping['name']] + SINONIMOS['name']
    search_phone = [mapping['phone']] + SINONIMOS['phone']
    search_email = [mapping['email']] + SINONIMOS['email']

    to_create = []
    
    for row_idx, row in enumerate(contact_list, start=1):
        name = ""
        phone = ""
        try:
            name = next((str(row[k]) for k in search_name if k in row and row[k]), "")
            phone = next((str(row[k]) for k in search_phone if k in row and row[k]), "")
            email = next((str(row[k]) for k in search_email if k in row and row[k]), "")

            name = name.strip() if name else ""
            email = email.strip() if email else ""

            # 🚀 Higienização contra Injeção de Fórmulas (Epic 8 Security)
            # Protege o Owner quando ele exportar esses dados para o Excel futuramente.
            name = sanitize_csv_formula(name)
            email = sanitize_csv_formula(email)
            
            cleaned_phone = clean_phone_number(phone)

            if not name and not cleaned_phone:
                continue

            if not cleaned_phone:
                report['errors'] += 1
                report['details'].append(f"Item {row_idx}: Telefone ausente ou inválido ({phone})")
                continue

            if not name:
                name = f"Contato Importado ({cleaned_phone[-4:]})"

            # Check duplicatas no SET em memória (O(1)) em vez do Banco (N queries)
            if cleaned_phone in existing_phones or (email and email in existing_emails):
                report['duplicates'] += 1
                continue

            # Adiciona ao buffer para criação em lote
            to_create.append(
                StudentIntake(
                    full_name=name,
                    phone=cleaned_phone,
                    email=email,
                    source=db_source,
                    status=IntakeStatus.NEW,
                    assigned_to=actor,
                    notes=f"Importado via {source_platform.upper()} (Batch Process)."
                )
            )
            
            # Marcamos como existente para evitar duplicatas dentro da própria lista de importação
            existing_phones.add(cleaned_phone)
            if email:
                existing_emails.add(email)

        except Exception as e:
            report['errors'] += 1
            report['details'].append(f"Item {row_idx} ({name or 'Sem Nome'}): {str(e)}")

    # 2. Bulk Create (Executa uma única query para o lote inteiro)
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
        if not line: continue
        
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
    Lê o stream de um arquivo CSV ou VCF e importa os contatos.
    """
    # 🚀 Segurança de Elite (Fintech Hardening): MIME & Size Validation
    # Proteção contra ataques de spoofing e exaustão de recursos.
    if hasattr(file_stream, 'name'):
        temp_path = file_stream.name
        # CSV e VCard permitidos
        allowed_mimes = ['text/csv', 'text/vcard', 'text/x-vcard', 'text/plain']
        try:
            validate_file_security(temp_path, max_size_mb=15, allowed_mimes=allowed_mimes)
        except Exception as e:
            return {'success': 0, 'duplicates': 0, 'errors': 1, 'details': [str(e)]}

    try:
        # 🚀 Segurança de Elite (Ghost Hardening): Prevent Memory Exhaustion
        file_stream.seek(0, os.SEEK_END)
        total_size = file_stream.tell()
        file_stream.seek(0)

        if total_size > MAX_IMPORT_FILE_SIZE:
             message = f"Arquivo muito grande ({total_size // (1024*1024)}MB). Limite de {MAX_IMPORT_FILE_SIZE // (1024*1024)}MB."
             return {'success': 0, 'duplicates': 0, 'errors': 1, 'details': [message]}

        raw_bytes = file_stream.read()
        try:
            decoded_content = raw_bytes.decode('utf-8-sig')
        except UnicodeDecodeError:
            decoded_content = raw_bytes.decode('latin-1')
            
        if source_platform == 'ios_vcard':
            contact_list = parse_vcard(decoded_content)
        else:
            f = io.StringIO(decoded_content)
            reader = csv.DictReader(f)
            contact_list = list(reader)
    except Exception as e:
        return {'success': 0, 'duplicates': 0, 'errors': 1, 'details': [f"Erro ao ler arquivo: {str(e)}"]}

    return import_contacts_from_list(contact_list, source_platform=source_platform, actor=actor)
