"""Rotas internas (staff) do corredor de treinos — fora de /treinos/ de
proposito: essas telas exigem o login proprio do Curva (staff_auth.py),
nao a sessao de aluno que vive em /treinos/ (D.000 do CORDA).

O login fica em /login/curva/ (prefixo /login/) de proposito: e' o
mesmo prefixo que RequestSecurityMiddleware ja rate-limita no scope
'login' (shared_support/security/__init__.py) e que PUBLIC_SCHEMA_PATHS
ja isenta do middleware de tenant (control/middleware.py) — reaproveita
os dois sem precisar duplicar nenhum dos dois aqui."""

from django.urls import path

from .views import (
    CoachAnalyticsView,
    CoachStudentDetailView,
    CoachStudentRosterView,
    CurvaStaffLoginView,
    CurvaStaffLogoutView,
    PublicWorkoutActivationQueueView,
)

urlpatterns = [
    path('login/curva/', CurvaStaffLoginView.as_view(), name='public-workout-staff-login'),
    path('login/curva/sair/', CurvaStaffLogoutView.as_view(), name='public-workout-staff-logout'),
    path(
        'public-workouts/ativacoes/',
        PublicWorkoutActivationQueueView.as_view(),
        name='public-workout-activation-queue',
    ),
    path('public-workouts/alunos/', CoachStudentRosterView.as_view(), name='public-workout-coach-roster'),
    # Excecao pedida pelo Renan: endereco curto em /treinos/. Nao colide com
    # o aluno (paginas do plano vivem em /renan/<slug>/) e continua exigindo
    # o login de staff do Curva -- so' o prefixo e' do corredor de treinos.
    path('treinos/coach', CoachAnalyticsView.as_view(), name='public-workout-coach-analytics'),
    path(
        'public-workouts/alunos/<int:account_id>/',
        CoachStudentDetailView.as_view(),
        name='public-workout-coach-student-detail',
    ),
]
