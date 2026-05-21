"""
Factories para os 3 modelos mais criados nos testes do OctoBox.

COMO USAR EM UM TESTE:
    from tests.factories import StudentFactory, ClassSessionFactory, SessionWorkoutFactory

    # Cria com defaults gerados automaticamente
    student = StudentFactory()

    # Sobrescreve campos específicos
    session = ClassSessionFactory(title='WOD Sexta', capacity=15)

    # SubFactory compõe automaticamente — ClassSession já incluída
    workout = SessionWorkoutFactory()

COMO ADICIONAR NOVOS MODELOS:
    1. Importe o modelo.
    2. Crie uma subclasse de factory.django.DjangoModelFactory.
    3. Defina Meta.model e todos os campos obrigatórios (sem default no modelo).
    4. Use factory.Sequence para campos únicos, factory.SubFactory para FKs obrigatórias.
    5. Documente o motivo de qualquer LazyAttribute não-trivial.
"""

import factory
from django.contrib.auth import get_user_model
from django.utils import timezone

from finance.models import Payment, PaymentStatus
from operations.models import ClassSession
from student_app.models import SessionWorkout
from students.models import Student


class UserFactory(factory.django.DjangoModelFactory):
    """Usuário Django genérico. Sem privilégios de staff/superuser por padrão."""

    class Meta:
        model = get_user_model()

    username = factory.Sequence(lambda n: f'user-{n}')
    email = factory.LazyAttribute(lambda u: f'{u.username}@example.com')
    password = factory.PostGenerationMethodCall('set_password', 'senha-forte-123')


class StudentFactory(factory.django.DjangoModelFactory):
    """
    Aluno (tenant-side). phone é EncryptedCharField com unique=True —
    o Sequence garante unicidade sem risco de colisão entre testes.
    phone_lookup_index é preenchido automaticamente pelo save() do modelo.
    """

    class Meta:
        model = Student

    full_name = factory.Sequence(lambda n: f'Aluno Teste {n}')
    # Formato E.164 sem +, 13 dígitos: 55 11 9XXXX-XXXX
    phone = factory.Sequence(lambda n: f'5511900{n:06d}')


class ClassSessionFactory(factory.django.DjangoModelFactory):
    """Aula agendada. scheduled_at padrão = now() + 1 dia para evitar conflito com 'passado'."""

    class Meta:
        model = ClassSession

    title = factory.Sequence(lambda n: f'Aula Teste {n}')
    scheduled_at = factory.LazyFunction(lambda: timezone.now().replace(microsecond=0))


class SessionWorkoutFactory(factory.django.DjangoModelFactory):
    """
    WOD vinculado a uma ClassSession via OneToOneField.
    SubFactory cria a sessão automaticamente se não for passada.
    """

    class Meta:
        model = SessionWorkout

    session = factory.SubFactory(ClassSessionFactory)


class PaymentFactory(factory.django.DjangoModelFactory):
    """Pagamento simples no status PENDING. Precisa de Student obrigatoriamente."""

    class Meta:
        model = Payment

    student = factory.SubFactory(StudentFactory)
    due_date = factory.LazyFunction(lambda: timezone.now().date())
    amount = factory.Sequence(lambda n: f'{100 + n}.00')
    status = PaymentStatus.PENDING
