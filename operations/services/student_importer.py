import csv
import logging
from datetime import date

from django.db import transaction

from shared_support.phone_numbers import normalize_phone_number
from shared_support.validators import validate_file_security
from students.models import HealthIssueStatus, Student, StudentGender, StudentStatus

logger = logging.getLogger('octobox.students')

_UPDATE_FIELDS = ['full_name', 'email', 'gender', 'birth_date', 'health_issue_status', 'cpf', 'status', 'notes']


def _emit_progress(job_id, count, failed_item=None):
    if not job_id:
        return
    try:
        from shared_support.background_jobs import update_job_progress
        update_job_progress(job_id, count, failed_item=failed_item)
    except Exception:
        logger.exception('background-job progress emit failed for job %s', job_id)


def _build_error_row(line_idx, student_obj, exc):
    return {
        'line': line_idx,
        'phone': student_obj.phone,
        'name': student_obj.full_name,
        'error': str(exc),
    }


def _flush_create(batch, created_count, error_rows, job_id=None):
    """batch is a list of (line_idx, Student) tuples."""
    objects = [obj for _, obj in batch]
    try:
        Student.objects.bulk_create(objects)
        created_count += len(objects)
        _emit_progress(job_id, len(objects))
        return created_count, error_rows
    except Exception:
        for line_idx, student_obj in batch:
            try:
                with transaction.atomic():
                    student_obj.save()
                created_count += 1
                _emit_progress(job_id, 1)
            except Exception as row_err:
                err = _build_error_row(line_idx, student_obj, row_err)
                error_rows.append(err)
                _emit_progress(job_id, 1, failed_item=err)
        return created_count, error_rows


def _flush_update(batch, updated_count, error_rows, job_id=None):
    """batch is a list of (line_idx, Student) tuples."""
    objects = [obj for _, obj in batch]
    try:
        Student.objects.bulk_update(objects, _UPDATE_FIELDS)
        updated_count += len(objects)
        _emit_progress(job_id, len(objects))
        return updated_count, error_rows
    except Exception:
        for line_idx, student_obj in batch:
            try:
                with transaction.atomic():
                    student_obj.save(update_fields=_UPDATE_FIELDS)
                updated_count += 1
                _emit_progress(job_id, 1)
            except Exception as row_err:
                err = _build_error_row(line_idx, student_obj, row_err)
                error_rows.append(err)
                _emit_progress(job_id, 1, failed_item=err)
        return updated_count, error_rows


class StudentImporter:
    def __init__(self, batch_size=500):
        self.batch_size = batch_size

    def import_from_file(self, file_path, delimiter=',', job_id=None):
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
                        _emit_progress(job_id, 1)
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
                        to_update.append((row_idx, s))
                    else:
                        s = Student(phone=phone, **student_data)
                        to_create.append((row_idx, s))

                    if len(to_create) >= self.batch_size:
                        created_count, error_rows = _flush_create(to_create, created_count, error_rows, job_id=job_id)
                        to_create = []

                    if len(to_update) >= self.batch_size:
                        updated_count, error_rows = _flush_update(to_update, updated_count, error_rows, job_id=job_id)
                        to_update = []

                if to_create:
                    created_count, error_rows = _flush_create(to_create, created_count, error_rows, job_id=job_id)
                if to_update:
                    updated_count, error_rows = _flush_update(to_update, updated_count, error_rows, job_id=job_id)

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
