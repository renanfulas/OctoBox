"""Rotas internas (staff) do corredor de treinos — fora de /treinos/ de
proposito: essas telas exigem o login proprio do Curva (staff_auth.py),
nao a sessao de aluno que vive em /treinos/ (D.000 do CORDA).

O login fica em /login/curva/ (prefixo /login/) de proposito: e' o
mesmo prefixo que RequestSecurityMiddleware ja rate-limita no scope
'login' (shared_support/security/__init__.py) e que PUBLIC_SCHEMA_PATHS
ja isenta do middleware de tenant (control/middleware.py) — reaproveita
os dois sem precisar duplicar nenhum dos dois aqui."""

from django.urls import path

from .views import CurvaStaffLoginView, CurvaStaffLogoutView, PublicWorkoutActivationQueueView

urlpatterns = [
    path('login/curva/', CurvaStaffLoginView.as_view(), name='public-workout-staff-login'),
    path('login/curva/sair/', CurvaStaffLogoutView.as_view(), name='public-workout-staff-logout'),
    path(
        'public-workouts/ativacoes/',
        PublicWorkoutActivationQueueView.as_view(),
        name='public-workout-activation-queue',
    ),
]
