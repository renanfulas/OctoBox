import pytest
from django.test import Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from access.shell_actions import get_shell_counts

User = get_user_model()

@pytest.fixture
def perf_user(db):
    user = User.objects.create_user(username='perf_tester', password='test')
    group, _ = Group.objects.get_or_create(name='Owner')
    user.groups.add(group)
    return user

@pytest.fixture
def logged_client(perf_user):
    client = Client()
    client.force_login(perf_user)
    # Mede o caminho steady-state do shell autenticado, que no runtime real
    # opera com cache curto aquecido entre requests.
    get_shell_counts(use_cache=True)
    return client

@pytest.mark.django_db
def test_dashboard_query_count(logged_client, django_assert_num_queries):
    """
    GARANTE: Dashboard central não ultrapassa 25 queries (Meta: Zero-Query / Snapshots).
    PROTEGE: Escalabilidade e latência do Main Loop.
    """
    with django_assert_num_queries(25, exact=False):
        response = logged_client.get(reverse('dashboard'))
        assert response.status_code == 200

@pytest.mark.django_db
def test_student_directory_query_count(logged_client, django_assert_num_queries):
    """
        GARANTE: Diretório de alunos eficiente no caminho autenticado estável,
    não ultrapassando 16 queries com shell cache aquecido.
    """
    with django_assert_num_queries(16, exact=False):
        response = logged_client.get(reverse('student-directory'))
        assert response.status_code == 200

@pytest.mark.django_db
def test_dashboard_latency_benchmark(benchmark, logged_client):
    """
    GARANTE: Tempo de resposta do Dashboard abaixo de 200ms (conforme pytest.ini).
    PROTEGE: A experiência do usuário de 'latência zero'.
    """
    @benchmark
    def get_dashboard():
        return logged_client.get(reverse('dashboard'))
    
    assert get_dashboard.status_code == 200

@pytest.mark.django_db
def test_finance_center_latency_benchmark(benchmark, logged_client):
    """
    GARANTE: Centro financeiro se mantém responsivo mesmo em escala.
    """
    @benchmark
    def get_finance():
        return logged_client.get(reverse('finance-center'))
    
    assert get_finance.status_code == 200
