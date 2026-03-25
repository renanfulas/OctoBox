import csv
import logging
from datetime import date
from shared_support.phone_numbers import normalize_phone_number
from students.models import HealthIssueStatus, Student, StudentGender, StudentStatus

logger = logging.getLogger('octobox.students')

class StudentImporter:
    def __init__(self, batch_size=500):
        self.batch_size = batch_size

    def import_from_file(self, file_path, delimiter=','):
        created_count = 0
        updated_count = 0
        skipped_count = 0
        details = []

        try:
            # EPIC 9: Streaming read with utf-8-sig to handle Windows/Excel encoding
            with open(file_path, encoding='utf-8-sig', newline='') as csv_file:
                reader = csv.DictReader(csv_file, delimiter=delimiter)
                
                # Cache existing phones in a set for O(1) lookups
                # For 1M+ records, this might be large (~30-50MB), which is acceptable.
                # If memory is even tighter, we could use a Bloom Filter or batch-check.
                existing_phones = set(Student.objects.values_list('phone', flat=True))
                
                to_create = []
                to_update = []

                for row_idx, row in enumerate(reader, start=2):
                    full_name = (row.get('full_name') or row.get('Nome') or '').strip()
                    phone = normalize_phone_number((row.get('whatsapp') or row.get('phone') or row.get('Telefone') or row.get('Celular') or '').strip())

                    if not full_name or not phone:
                        skipped_count += 1
                        continue

                    student_data = {
                        'full_name': full_name,
                        'email': (row.get('email') or row.get('E-mail') or '').strip(),
                        'gender': self._parse_gender(row.get('gender')),
                        'birth_date': self._parse_date(row.get('birth_date')),
                        'health_issue_status': self._parse_health_issue_status(row.get('health_issue_status')),
                        'cpf': (row.get('cpf') or row.get('CPF') or '').strip(),
                        'status': self._parse_status(row.get('status')),
                        'notes': (row.get('notes') or '').strip(),
                    }

                    if phone in existing_phones:
                        s = Student(phone=phone, **student_data)
                        to_update.append(s)
                    else:
                        s = Student(phone=phone, **student_data)
                        to_create.append(s)
                        existing_phones.add(phone)

                    if len(to_create) >= self.batch_size:
                        Student.objects.bulk_create(to_create)
                        created_count += len(to_create)
                        to_create = []

                    if len(to_update) >= self.batch_size:
                        update_fields = ['full_name', 'email', 'gender', 'birth_date', 'health_issue_status', 'cpf', 'status', 'notes']
                        Student.objects.bulk_update(to_update, update_fields)
                        updated_count += len(to_update)
                        to_update = []

                # Final flush
                if to_create:
                    Student.objects.bulk_create(to_create)
                    created_count += len(to_create)
                if to_update:
                    update_fields = ['full_name', 'email', 'gender', 'birth_date', 'health_issue_status', 'cpf', 'status', 'notes']
                    Student.objects.bulk_update(to_update, update_fields)
                    updated_count += len(to_update)

        except Exception as e:
            logger.error(f"Failed to import students from {file_path}: {str(e)}", exc_info=True)
            raise e

        return {
            'success': created_count,
            'updated': updated_count,
            'skipped': skipped_count,
            'total': created_count + updated_count + skipped_count
        }

    def _parse_date(self, value):
        raw_value = (value or '').strip()
        if not raw_value: return None
        try: return date.fromisoformat(raw_value)
        except: return None

    def _parse_status(self, value):
        raw_value = (value or '').strip().lower()
        if not raw_value: return StudentStatus.ACTIVE
        for choice, _ in StudentStatus.choices:
            if raw_value == choice: return choice
        return StudentStatus.ACTIVE

    def _parse_gender(self, value):
        raw_value = (value or '').strip().lower()
        if not raw_value: return ''
        aliases = {
            'masculino': StudentGender.MALE, 'male': StudentGender.MALE, 'm': StudentGender.MALE,
            'feminino': StudentGender.FEMALE, 'female': StudentGender.FEMALE, 'f': StudentGender.FEMALE,
        }
        return aliases.get(raw_value, '')

    def _parse_health_issue_status(self, value):
        raw_value = (value or '').strip().lower()
        if not raw_value: return ''
        aliases = {
            'sim': HealthIssueStatus.YES, 'yes': HealthIssueStatus.YES, 'y': HealthIssueStatus.YES,
            'nao': HealthIssueStatus.NO, 'no': HealthIssueStatus.NO, 'n': HealthIssueStatus.NO,
        }
        return aliases.get(raw_value, '')
