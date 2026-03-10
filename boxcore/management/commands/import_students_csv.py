"""
ARQUIVO: comando interno para importação de alunos por CSV.

POR QUE ELE EXISTE:
- Reduz cadastro manual e serve como ponte de entrada da base inicial de alunos.

O QUE ESTE ARQUIVO FAZ:
1. Lê um CSV de alunos.
2. Valida campos mínimos.
3. Atualiza ou cria aluno usando WhatsApp como chave.
4. Converte status, data e demais campos leves de forma controlada.

PONTOS CRITICOS:
- O WhatsApp é a chave de deduplicação; mudar isso muda a lógica de importação.
- Validações erradas aqui podem gerar duplicidade ou dados incorretos em massa.
"""

import csv
from datetime import date

from django.core.management.base import BaseCommand, CommandError

from boxcore.models import HealthIssueStatus, Student, StudentGender, StudentStatus


class Command(BaseCommand):
    help = 'Importa alunos por CSV usando WhatsApp como chave de deduplicação.'

    def add_arguments(self, parser):
        parser.add_argument('csv_path', help='Caminho para o arquivo CSV.')
        parser.add_argument(
            '--delimiter',
            default=',',
            help='Delimitador do CSV. Use ";" para planilhas exportadas em formato brasileiro.',
        )

    def handle(self, *args, **options):
        csv_path = options['csv_path']
        delimiter = options['delimiter']
        created_count = 0
        updated_count = 0
        skipped_count = 0

        try:
            with open(csv_path, encoding='utf-8-sig', newline='') as csv_file:
                reader = csv.DictReader(csv_file, delimiter=delimiter)
                if not reader.fieldnames:
                    raise CommandError('O arquivo CSV está vazio ou sem cabeçalho.')

                for row_number, row in enumerate(reader, start=2):
                    full_name = (row.get('full_name') or '').strip()
                    phone = (row.get('whatsapp') or row.get('phone') or '').strip()

                    if not full_name or not phone:
                        skipped_count += 1
                        self.stderr.write(
                            self.style.WARNING(
                                f'Linha {row_number}: ignorada por falta de nome ou WhatsApp.'
                            )
                        )
                        continue

                    # O WhatsApp e a chave de deduplicacao da importacao inicial.
                    defaults = {
                        'full_name': full_name,
                        'email': (row.get('email') or '').strip(),
                        'gender': self._parse_gender(row.get('gender')),
                        'birth_date': self._parse_date(row.get('birth_date')),
                        'health_issue_status': self._parse_health_issue_status(row.get('health_issue_status')),
                        'cpf': (row.get('cpf') or '').strip(),
                        'status': self._parse_status(row.get('status')),
                        'notes': (row.get('notes') or '').strip(),
                    }

                    # update_or_create evita cadastro duplicado quando o WhatsApp ja existe.
                    student, created = Student.objects.update_or_create(
                        phone=phone,
                        defaults=defaults,
                    )

                    if created:
                        created_count += 1
                        self.stdout.write(self.style.SUCCESS(f'Criado: {student.full_name}'))
                    else:
                        updated_count += 1
                        self.stdout.write(self.style.SUCCESS(f'Atualizado: {student.full_name}'))
        except FileNotFoundError as exc:
            raise CommandError(f'Arquivo não encontrado: {csv_path}') from exc

        self.stdout.write(
            self.style.SUCCESS(
                f'Importação finalizada. Criados: {created_count}, atualizados: {updated_count}, ignorados: {skipped_count}.'
            )
        )

    def _parse_date(self, value):
        raw_value = (value or '').strip()
        if not raw_value:
            return None
        try:
            return date.fromisoformat(raw_value)
        except ValueError as exc:
            raise CommandError(
                f'Data inválida no CSV: {raw_value}. Use o formato AAAA-MM-DD.'
            ) from exc

    def _parse_status(self, value):
        raw_value = (value or '').strip().lower()
        valid_statuses = {choice for choice, _ in StudentStatus.choices}
        if not raw_value:
            return StudentStatus.ACTIVE

        # Falha explícita é melhor do que importar silenciosamente um status inválido.
        if raw_value not in valid_statuses:
            raise CommandError(
                f'Status inválido: {raw_value}. Use um destes valores: {", ".join(sorted(valid_statuses))}.'
            )
        return raw_value

    def _parse_gender(self, value):
        raw_value = (value or '').strip().lower()
        if not raw_value:
            return ''

        aliases = {
            'masculino': StudentGender.MALE,
            'male': StudentGender.MALE,
            'm': StudentGender.MALE,
            'feminino': StudentGender.FEMALE,
            'female': StudentGender.FEMALE,
            'f': StudentGender.FEMALE,
        }
        if raw_value not in aliases:
            raise CommandError('Genero invalido no CSV. Use Masculino/Feminino ou male/female.')
        return aliases[raw_value]

    def _parse_health_issue_status(self, value):
        raw_value = (value or '').strip().lower()
        if not raw_value:
            return ''

        aliases = {
            'sim': HealthIssueStatus.YES,
            'yes': HealthIssueStatus.YES,
            'y': HealthIssueStatus.YES,
            'nao': HealthIssueStatus.NO,
            'no': HealthIssueStatus.NO,
            'n': HealthIssueStatus.NO,
        }
        if raw_value not in aliases:
            raise CommandError('Problema de saude invalido no CSV. Use Sim/Nao ou yes/no.')
        return aliases[raw_value]