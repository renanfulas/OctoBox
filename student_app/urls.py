from django.urls import include, path

from .views import (
    StudentHomeView,
    StudentManifestView,
    StudentOfflineView,
    StudentServiceWorkerView,
    StudentSettingsView,
    StudentWorkoutView,
)


urlpatterns = [
    path('auth/', include('student_identity.urls')),
    path('', StudentHomeView.as_view(), name='student-app-home'),
    path('treino/', StudentWorkoutView.as_view(), name='student-app-workout'),
    path('configuracoes/', StudentSettingsView.as_view(), name='student-app-settings'),
    path('manifest.webmanifest', StudentManifestView.as_view(), name='student-app-manifest'),
    path('sw.js', StudentServiceWorkerView.as_view(), name='student-app-sw'),
    path('offline/', StudentOfflineView.as_view(), name='student-app-offline'),
]
