import csv
import logging
from datetime import date

from django.db import transaction

from shared_support.phone_numbers import normalize_phone_number
from shared_support.validators import validate_file_security
from students.models import HealthIssueStatus, Student, StudentGender, StudentStatus

logger = logging.getLogger('octobox.students')

_UPDATE_FIELDS = ['full_name', 'email', 'gender', 'birth_date', 'health_issue_status', 'cpf', 'status', 'notes']


def _flush_create(batch, created_count, error_rows):
    """Attempt bulk_create; fall back to per-row savepoints on constraint error."""
    try:
        Student.objects.bulk_create(batch)
        return created_count + len(batch), error_rows
    except Exception:
        for student_obj in batch:
            try:
                with transaction.atomic():
                    student_obj.save()
                created_count += 1
            except Exception as row_err:
                error_rows.append({'phone': student_obj.phone, 'name': student_obj.full_name, 'error': str(row_err)})
        return created_count, error_rows


def _flush_update(batch, updated_count, error_rows):
    """Attempt bulk_update; fall back to per-row savepoints on error."""
    try:
        Student.objects.bulk_update(batch, _UPDATE_FIELDS)
        return updated_count + len(batch), error_rows
    except Exception:
        for student_obj in batch:
            try:
                with transaction.atomic():
                    student_obj.save(update_fields=_UPDATE_FIELDS)
                updated_count += 1
            except Exception as row_err:
                error_rows.append({'phone': student_obj.phone, 'name': student_obj.full_name, 'error': str(row_err)})
        return updated_count, error_rows


class StudentImporter:
    def __init__(self, batch_size=500):
        self.batch_size = batch_size

    def import_from_file(self, file_path, delimiter=','):
        created_count = 0
        updated_count = 0
        skipped_count = 0
        error_rows = []

        try:
            validate_file_security(file_path, max_size_mb=15, allowed_mimes=['text/csv', 'text/plain'])

            with open(file_path, encoding='utf-8-sig', newline='') as csv_file:
                reader = csv.DictReader(csv_file, delimiter=delimiter)

                existing_student_map = {p: i for p, i in Student.objects.values_list('phone', 'id').iterator()}

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

                    if phone in existing_student_map:
                        s = Student(id=existing_student_map[phone], phone=phone, **student_data)
                        to_update.append(s)
                    else:
                        s = Student(phone=phone, **student_data)
                        to_create.append(s)

                    if len(to_create) >= self.batch_size:
                        created_count, error_rows = _flush_create(to_create, created_count, error_rows)
                        to_create = []

                    if len(to_update) >= self.batch_size:
                        updated_count, error_rows = _flush_update(to_update, updated_count, error_rows)
                        to_update = []

                if to_create:
                    created_count, error_rows = _flush_create(to_create, created_count, error_rows)
                if to_update:
                    updated_count, error_rows = _flush_update(to_update, updated_count, error_rows)

        except Exception as e:
            logger.error(f"Failed to import students from {file_path}: {str(e)}", exc_info=True)
            raise e

        return {
            'success': created_count,
            'updated': updated_count,
            'skipped': skipped_count,
            'errors': len(error_rows),
            'error_rows': error_rows,
            'total': created_count + updated_count + skipped_count + len(error_rows),
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
