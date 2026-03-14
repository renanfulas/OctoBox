"""
ARQUIVO: builders puros dos relatorios do catalogo.

POR QUE ELE EXISTE:
- Tira do catalogo historico a montagem dos payloads de exportacao de alunos e financeiro.

O QUE ESTE ARQUIVO FAZ:
1. Monta payloads CSV e PDF para diretorio de alunos.
2. Monta payloads CSV e PDF para central financeira.
3. Mantem a montagem desacoplada da resposta HTTP final.

PONTOS CRITICOS:
- A leitura pesada deve continuar vindo pronta de queries ou snapshots.
"""


def build_student_directory_report(*, students, report_format):
    if report_format == 'csv':
        return {
            'format': 'csv',
            'filename': 'relatorio-alunos.csv',
            'headers': ['Nome', 'WhatsApp', 'CPF', 'Status do aluno', 'Status comercial', 'Status financeiro', 'Plano atual'],
            'rows': [
                [
                    student.full_name,
                    student.phone,
                    student.cpf,
                    student.get_status_display(),
                    student.latest_enrollment_status or '-',
                    student.latest_payment_status or '-',
                    student.latest_plan_name or '-',
                ]
                for student in students
            ],
        }

    if report_format == 'pdf':
        return {
            'format': 'pdf',
            'filename': 'relatorio-alunos.pdf',
            'title': 'Relatorio de alunos - OctoBox Control',
            'sections': [
                {
                    'title': 'Base filtrada',
                    'lines': [
                        f'{student.full_name} | WhatsApp {student.phone} | Status {student.get_status_display()} | Comercial {student.latest_enrollment_status or "-"} | Financeiro {student.latest_payment_status or "-"}'
                        for student in students[:60]
                    ]
                    or ['Nenhum aluno encontrado para o filtro atual.'],
                }
            ],
        }

    raise ValueError('Formato de exportacao nao suportado.')


def build_finance_report(*, snapshot, report_format):
    payments = snapshot['payments']
    enrollments = snapshot['enrollments']
    plans = snapshot['plans']

    if report_format == 'csv':
        return {
            'format': 'csv',
            'filename': 'relatorio-financeiro.csv',
            'headers': ['Aluno', 'Plano', 'Vencimento', 'Valor', 'Status', 'Metodo'],
            'rows': [
                [
                    payment.student.full_name,
                    payment.enrollment.plan.name if payment.enrollment else '-',
                    payment.due_date.strftime('%d/%m/%Y'),
                    payment.amount,
                    payment.get_status_display(),
                    payment.get_method_display(),
                ]
                for payment in payments.order_by('due_date', 'student__full_name')[:300]
            ],
        }

    if report_format == 'pdf':
        plan_lines = [
            f'{plan.name} | R$ {plan.price:.2f} | {plan.get_billing_cycle_display()} | ativo={"sim" if plan.active else "nao"}'
            for plan in plans[:30]
        ] or ['Nenhum plano encontrado para o filtro atual.']
        payment_lines = [
            f'{payment.student.full_name} | {payment.due_date:%d/%m/%Y} | R$ {payment.amount:.2f} | {payment.get_status_display()}'
            for payment in payments.order_by('due_date', 'student__full_name')[:45]
        ] or ['Nenhum pagamento encontrado para o filtro atual.']
        movement_lines = [
            f'{enrollment.student.full_name} | {enrollment.plan.name} | {enrollment.get_status_display()} | inicio {enrollment.start_date:%d/%m/%Y}'
            for enrollment in enrollments.order_by('-updated_at', '-created_at')[:30]
        ] or ['Nenhuma matricula encontrada para o filtro atual.']
        return {
            'format': 'pdf',
            'filename': 'relatorio-financeiro.pdf',
            'title': 'Relatorio financeiro - OctoBox Control',
            'sections': [
                {'title': 'Planos no recorte', 'lines': plan_lines},
                {'title': 'Pagamentos no recorte', 'lines': payment_lines},
                {'title': 'Movimentos de matricula', 'lines': movement_lines},
            ],
        }

    raise ValueError('Formato de exportacao nao suportado.')


__all__ = ['build_finance_report', 'build_student_directory_report']