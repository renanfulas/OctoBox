from django.urls import include, path

from .views import (
    StudentConfirmAttendanceView,
    StudentGradeView,
    StudentHomeView,
    StudentManifestView,
    StudentMembershipPendingView,
    StudentNoActiveBoxView,
    StudentOnboardingWizardView,
    StudentOfflineView,
    StudentRmView,
    StudentServiceWorkerView,
    StudentSettingsView,
    StudentSuspendedFinancialView,
    StudentInviteEntryView,
    StudentSwitchBoxView,
    StudentWodView,
)


urlpatterns = [
    path('auth/', include('student_identity.urls')),
    path('', StudentHomeView.as_view(), name='student-app-home'),
    path('onboarding/', StudentOnboardingWizardView.as_view(), name='student-app-onboarding'),
    path('grade/', StudentGradeView.as_view(), name='student-app-grade'),
    path('aguardando-aprovacao/', StudentMembershipPendingView.as_view(), name='student-app-membership-pending'),
    path('suspenso-financeiro/', StudentSuspendedFinancialView.as_view(), name='student-app-suspended-financial'),
    path('sem-box/', StudentNoActiveBoxView.as_view(), name='student-app-no-active-box'),
    path('entrar-com-convite/', StudentInviteEntryView.as_view(), name='student-app-enter-invite'),
    path('box/switch/', StudentSwitchBoxView.as_view(), name='student-app-switch-box'),
    path('presenca/confirmar/', StudentConfirmAttendanceView.as_view(), name='student-app-confirm-attendance'),
    path('wod/', StudentWodView.as_view(), name='student-app-wod'),
    path('treino/', StudentWodView.as_view(), name='student-app-workout'),
    path('rm/', StudentRmView.as_view(), name='student-app-rm'),
    path('configuracoes/', StudentSettingsView.as_view(), name='student-app-settings'),
    path('manifest.webmanifest', StudentManifestView.as_view(), name='student-app-manifest'),
    path('sw.js', StudentServiceWorkerView.as_view(), name='student-app-sw'),
    path('offline/', StudentOfflineView.as_view(), name='student-app-offline'),
]
