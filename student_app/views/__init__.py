"""
ARQUIVO: fachada publica das views do app do aluno.

POR QUE ELE EXISTE:
- preserva o contrato de importacao de `student_app.views` enquanto a implementacao vive em corredores separados.

O QUE ESTE ARQUIVO FAZ:
1. reexporta as views autenticadas, de onboarding, membership, PWA e treino publico.
2. concentra o ponto unico de importacao usado por `urls.py` e `public_urls.py`.
"""

from .membership_views import (
    StudentInviteEntryView,
    StudentMembershipPendingView,
    StudentNoActiveBoxView,
    StudentSuspendedFinancialView,
    StudentSwitchBoxView,
)
from .onboarding_views import StudentOnboardingWizardView
from .public_workout_views import (
    PublicWorkoutDetailView,
    PublicWorkoutManifestView,
    PublicWorkoutOfflineView,
    PublicWorkoutServiceWorkerView,
)
from .pwa_views import (
    StudentManifestView,
    StudentOfflineView,
    StudentPushSubscribeView,
    StudentPushUnsubscribeView,
    StudentServiceWorkerView,
)
from .shell_views import (
    StudentAddRmView,
    StudentCancelAttendanceView,
    StudentConfirmAttendanceView,
    StudentGradeView,
    StudentHomeView,
    StudentRmView,
    StudentSessionAttendeesView,
    StudentSettingsView,
    StudentUpdateRmView,
    StudentWodView,
)

__all__ = [
    'PublicWorkoutDetailView',
    'PublicWorkoutManifestView',
    'PublicWorkoutOfflineView',
    'PublicWorkoutServiceWorkerView',
    'StudentAddRmView',
    'StudentCancelAttendanceView',
    'StudentConfirmAttendanceView',
    'StudentGradeView',
    'StudentHomeView',
    'StudentInviteEntryView',
    'StudentManifestView',
    'StudentMembershipPendingView',
    'StudentNoActiveBoxView',
    'StudentOfflineView',
    'StudentOnboardingWizardView',
    'StudentPushSubscribeView',
    'StudentPushUnsubscribeView',
    'StudentRmView',
    'StudentServiceWorkerView',
    'StudentSessionAttendeesView',
    'StudentSettingsView',
    'StudentSuspendedFinancialView',
    'StudentSwitchBoxView',
    'StudentUpdateRmView',
    'StudentWodView',
]
