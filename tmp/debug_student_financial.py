from django.test import Client
from django.contrib.auth import get_user_model
from students.models import Student
from finance.models import Payment

User = get_user_model()
user = User.objects.get(username='test_reception')
payment = Payment.objects.filter(status='overdue').select_related('student').first()
student = payment.student
client = Client(HTTP_HOST='localhost')
client.force_login(user)

resp = client.get(f'/alunos/{student.id}/financeiro/cobranca/{payment.id}/drawer/', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
print('GET STATUS', resp.status_code)
print('GET TYPE', resp.get('Content-Type'))
print('GET BODY', resp.content[:200])

resp2 = client.post(
    f'/alunos/{student.id}/financeiro/acao/',
    {
        'payment_id': str(payment.id),
        'action': 'mark-paid',
        'method': 'pix',
        'amount': str(payment.amount),
        'due_date': payment.due_date.strftime('%d/%m/%Y'),
        'reference': payment.reference or '',
        'notes': payment.notes or '',
    },
    HTTP_X_REQUESTED_WITH='XMLHttpRequest',
)
print('POST STATUS', resp2.status_code)
print('POST TYPE', resp2.get('Content-Type'))
print('POST BODY', resp2.content[:200])
