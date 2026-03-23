import csv
import io
import re
from django.db import transaction
from onboarding.models import StudentIntake, IntakeSource, IntakeStatus

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
    Deduplica e higieniza no processo.
    """
    report = {'success': 0, 'duplicates': 0, 'errors': 0, 'details': []}
    
    source_map = {
        'whatsapp': IntakeSource.WHATSAPP,
        'tecnofit': IntakeSource.IMPORT,
        'nextfit': IntakeSource.IMPORT,
        'ios_vcard': IntakeSource.IMPORT,
    }
    db_source = source_map.get(source_platform, IntakeSource.IMPORT)

    # Mapeamento Inteligente (Sinônimos Globais)
    SINONIMOS = {
        'name': ['Nome', 'Name', 'saved_name', 'public_name', 'Contato', 'First Name', 'Contact'],
        'phone': ['Telefone', 'Phone', 'phone_number', 'formatted_phone', 'Celular', 'Mobile', 'WhatsApp'],
        'email': ['Email', 'E-mail', 'Mail']
    }

    # Estrutura padrão por plataforma (Mapeamento de preferência)
    header_maps = {
        'whatsapp': {'name': 'Nome', 'phone': 'Telefone', 'email': 'Email'},
        'tecnofit': {'name': 'Nome', 'phone': 'Celular', 'email': 'E-mail'},
        'nextfit': {'name': 'Nome', 'phone': 'Telefone', 'email': 'Email'},
    }
    mapping = header_maps.get(source_platform, header_maps['whatsapp'])

    # Concatena a preferência da plataforma com os sinônimos gerais
    search_name = [mapping['name']] + SINONIMOS['name']
    search_phone = [mapping['phone']] + SINONIMOS['phone']
    search_email = [mapping['email']] + SINONIMOS['email']

    for row_idx, row in enumerate(contact_list, start=1):
        name = ""
        phone = ""
        try:
            # Extração Fuzzy: pega o primeiro que der match e tiver conteúdo
            name = next((str(row[k]) for k in search_name if k in row and row[k]), "")
            phone = next((str(row[k]) for k in search_phone if k in row and row[k]), "")
            email = next((str(row[k]) for k in search_email if k in row and row[k]), "")

            name = name.strip() if name else ""
            email = email.strip() if email else ""
            cleaned_phone = clean_phone_number(phone)

            if not name and not cleaned_phone:
                continue

            if not cleaned_phone:
                report['errors'] += 1
                report['details'].append(f"Item {row_idx}: Telefone ausente ou inválido ({phone})")
                continue

            if not name:
                name = f"Contato Importado ({cleaned_phone[-4:]})"

            if check_duplicate_lead(phone=cleaned_phone, email=email):
                report['duplicates'] += 1
                continue

            with transaction.atomic():
                StudentIntake.objects.create(
                    full_name=name,
                    phone=cleaned_phone,
                    email=email,
                    source=db_source,
                    status=IntakeStatus.NEW,
                    assigned_to=actor,
                    notes=f"Importado via {source_platform.upper()} de forma automatizada."
                )
                report['success'] += 1

        except Exception as e:
            report['errors'] += 1
            report['details'].append(f"Item {row_idx} ({name or 'Sem Nome'}): {str(e)}")

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
    try:
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
