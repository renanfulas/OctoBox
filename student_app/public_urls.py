"""
ARQUIVO: rotas publicas de treino em modo PWA.

POR QUE ELE EXISTE:
- separa os links publicos sem login do fluxo autenticado do app do aluno.

O QUE ESTE ARQUIVO FAZ:
1. publica os treinos publicos em /renan/.
2. expõe manifest, service worker e fallback offline do PWA publico.

PONTOS CRITICOS:
- as rotas precisam continuar simples porque os links sao compartilhados diretamente com os alunos.
- qualquer mudanca de slug aqui quebra URLs publicas ja distribuidas.
"""

from django.urls import path, re_path

from .views import (
    PublicWorkoutAssessmentsView,
    PublicWorkoutDetailView,
    PublicWorkoutDownloadPdfView,
    PublicWorkoutExportDataView,
    PublicWorkoutLocalStorageBackupView,
    PublicWorkoutManifestView,
    PublicWorkoutMealPlanView,
    PublicWorkoutOfflineView,
    PublicWorkoutPackageView,
    PublicWorkoutRecordAssessmentView,
    PublicWorkoutRecordLoadView,
    PublicWorkoutServiceWorkerView,
    PublicWorkoutSignOutView,
    PublicWorkoutTemplatePreviewView,
    PublicWorkoutWeeklyReviewView,
)


urlpatterns = [
    path('sw.js', PublicWorkoutServiceWorkerView.as_view(), name='public-workout-sw'),
    path('offline/', PublicWorkoutOfflineView.as_view(), name='public-workout-offline'),
    path('<slug:plan_slug>/manifest.webmanifest', PublicWorkoutManifestView.as_view(), name='public-workout-manifest'),
    path('<slug:plan_slug>/avaliacoes.json', PublicWorkoutAssessmentsView.as_view(), name='public-workout-assessments'),
    path(
        '<slug:plan_slug>/backup-carga',
        PublicWorkoutLocalStorageBackupView.as_view(),
        name='public-workout-backup-carga',
    ),
    path('<slug:plan_slug>/carga', PublicWorkoutRecordLoadView.as_view(), name='public-workout-record-load'),
    path('<slug:plan_slug>/pacote.json', PublicWorkoutPackageView.as_view(), name='public-workout-package'),
    path('<slug:plan_slug>/nutricao.json', PublicWorkoutMealPlanView.as_view(), name='public-workout-meal-plan'),
    path(
        '<slug:plan_slug>/revisao-semanal',
        PublicWorkoutWeeklyReviewView.as_view(),
        name='public-workout-weekly-review',
    ),
    path(
        '<slug:plan_slug>/avaliacoes',
        PublicWorkoutRecordAssessmentView.as_view(),
        name='public-workout-record-assessment',
    ),
    path('<slug:plan_slug>/meus-dados.json', PublicWorkoutExportDataView.as_view(), name='public-workout-export-data'),
    path('<slug:plan_slug>/treino.pdf', PublicWorkoutDownloadPdfView.as_view(), name='public-workout-download-pdf'),
    path('<slug:plan_slug>/sair', PublicWorkoutSignOutView.as_view(), name='public-workout-signout'),
    path(
        '<slug:plan_slug>/preview-b3',
        PublicWorkoutTemplatePreviewView.as_view(),
        name='public-workout-preview-b3',
    ),
    re_path(r'^(?P<plan_slug>[-a-z0-9]+)/?$', PublicWorkoutDetailView.as_view(), name='public-workout-detail'),
]
