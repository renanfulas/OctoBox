from django.urls import include, path

from .views import (
    StudentHomeView,
    StudentManifestView,
    StudentMembershipPendingView,
    StudentNoActiveBoxView,
    StudentOfflineView,
    StudentServiceWorkerView,
    StudentSettingsView,
    StudentSuspendedFinancialView,
    StudentInviteEntryView,
    StudentSwitchBoxView,
    StudentWorkoutView,
)


urlpatterns = [
    path('auth/', include('student_identity.urls')),
    path('', StudentHomeView.as_view(), name='student-app-home'),
    path('aguardando-aprovacao/', StudentMembershipPendingView.as_view(), name='student-app-membership-pending'),
    path('suspenso-financeiro/', StudentSuspendedFinancialView.as_view(), name='student-app-suspended-financial'),
    path('sem-box/', StudentNoActiveBoxView.as_view(), name='student-app-no-active-box'),
    path('entrar-com-convite/', StudentInviteEntryView.as_view(), name='student-app-enter-invite'),
    path('box/switch/', StudentSwitchBoxView.as_view(), name='student-app-switch-box'),
    path('treino/', StudentWorkoutView.as_view(), name='student-app-workout'),
    path('configuracoes/', StudentSettingsView.as_view(), name='student-app-settings'),
    path('manifest.webmanifest', StudentManifestView.as_view(), name='student-app-manifest'),
    path('sw.js', StudentServiceWorkerView.as_view(), name='student-app-sw'),
    path('offline/', StudentOfflineView.as_view(), name='student-app-offline'),
]
