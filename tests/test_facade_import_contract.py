"""
ARQUIVO: contrato de importacao dos modulos que vao virar fachada (Fase 0 do split).

POR QUE ELE EXISTE:
- docs/plans/split-arquivos-grandes-plano.md, Fase 0, item 1 e ADR-1. O split
  transforma estes cinco modulos em fachadas que so reexportam; se a fachada
  esquecer um nome, quem faz `from public_workouts.services import X` quebra so
  quando aquela linha roda (muitas vezes um import tardio dentro de view).
- Este teste falha na hora se um nome que hoje se importa daqui sumir ou mudar
  de natureza (classe virar funcao, excecao deixar de ser excecao).

COMO A LISTA FOI GERADA (main 6a0c8ca0, 21/10/2026), CONGELADA AQUI DE PROPOSITO:
- todo nome publico definido no proprio modulo (classe, funcao, constante,
  excecao), menos `logger`, que e detalhe interno de cada arquivo;
- mais todo nome que o repositorio importa do modulo em codigo (`from X import Y`
  ou `X.Y`), mesmo privado ou reexportado: e o que os chamadores usam hoje.
- Alvos de `patch('modulo.nome')` NAO entram: o ADR-2 manda move-los para o
  modulo novo no mesmo PR do split, e quem os vigia e
  tests/test_facade_patch_guard.py.

COMO MANTER:
- Nome novo num destes modulos nao exige mudanca aqui (o contrato so protege o
  que ja existia).
- Remover um nome de proposito (fora de PR de split) = tirar a linha daqui no
  mesmo PR, com o motivo na descricao. Num PR de split, nunca.
"""

from __future__ import annotations

import importlib
import inspect

import pytest


CLASS = 'class'
EXCEPTION = 'exception'
FUNCTION = 'function'
CONSTANT = 'constant'


IMPORT_CONTRACT: dict[str, dict[str, str]] = {
    'public_workouts.services': {
        'activate_program_version': FUNCTION,
        'active_correction_successor': FUNCTION,
        'approve_and_publish_draft': FUNCTION,
        'assessment_profile': FUNCTION,
        'AssessmentValueError': EXCEPTION,
        'build_movement_label_lookup': FUNCTION,
        'build_report': FUNCTION,
        'build_student_package': FUNCTION,
        'build_weekly_review': FUNCTION,
        'correct_load': FUNCTION,
        'create_program_draft': FUNCTION,
        'export_account_data': FUNCTION,
        'flag_movements_against_restrictions': FUNCTION,
        'generate_ai_draft_for_subscription': FUNCTION,
        'get_active_meal_plan': FUNCTION,
        'get_active_program': FUNCTION,
        'get_training_profile': FUNCTION,
        'has_presencial_skinfold_assessment': FUNCTION,
        'is_known_plan_slug': FUNCTION,
        'list_assessments': FUNCTION,
        'list_load_history': FUNCTION,
        'list_program_versions': FUNCTION,
        'LoadCorrectionConflictError': EXCEPTION,
        'LoadCorrectionNotFoundError': EXCEPTION,
        'LoadValueError': EXCEPTION,
        'NutritionIntakeValidationError': EXCEPTION,
        'parse_skinfold_note': FUNCTION,
        'ProgramDraftReviewError': EXCEPTION,
        'publish_meal_plan': FUNCTION,
        'publish_program': FUNCTION,
        'record_assessment': FUNCTION,
        'record_load': FUNCTION,
        'reject_program_draft': FUNCTION,
        'require_nutrition_tier': FUNCTION,
        'resolve_assessment_profile': FUNCTION,
        'save_nutrition_profile': FUNCTION,
        'save_training_profile': FUNCTION,
        'serialize_training_profile': FUNCTION,
        'skinfold_body_fat': FUNCTION,
        'SKINFOLD_KEYS': CONSTANT,
        'TrainingIntakeValidationError': EXCEPTION,
        'UnknownPlanSlugError': EXCEPTION,
        # Privado, mas importado por tests/test_public_workout_access_split.py.
        '_validate_plan_slug': FUNCTION,
    },
    'public_workouts.models': {
        'PublicWorkoutAccount': CLASS,
        'PublicWorkoutAcquisitionSession': CLASS,
        'PublicWorkoutAssessment': CLASS,
        'PublicWorkoutCampaignSpend': CLASS,
        'PublicWorkoutCheckoutLead': CLASS,
        'PublicWorkoutExperiment': CLASS,
        'PublicWorkoutExperimentAssignment': CLASS,
        'PublicWorkoutExperimentStatus': CLASS,
        'PublicWorkoutExperimentVariant': CLASS,
        'PublicWorkoutFunnelEvent': CLASS,
        'PublicWorkoutGuaranteeModel': CLASS,
        'PublicWorkoutLoadLog': CLASS,
        'PublicWorkoutLoadLogAchievementKind': CLASS,
        'PublicWorkoutLoadLogSetRole': CLASS,
        'PublicWorkoutLocalStorageBackup': CLASS,
        'PublicWorkoutLoginToken': CLASS,
        'PublicWorkoutMealPlan': CLASS,
        'PublicWorkoutMealPlanDelivery': CLASS,
        'PublicWorkoutMetricSnapshot': CLASS,
        'PublicWorkoutMovement': CLASS,
        'PublicWorkoutMovementEquipment': CLASS,
        'PublicWorkoutMovementModality': CLASS,
        'PublicWorkoutMovementStatus': CLASS,
        'PublicWorkoutNutritionProfile': CLASS,
        'PublicWorkoutOutboxMessage': CLASS,
        'PublicWorkoutOutboxStatus': CLASS,
        'PublicWorkoutPayment': CLASS,
        'PublicWorkoutPaymentNotice': CLASS,
        'PublicWorkoutPaymentStatus': CLASS,
        'PublicWorkoutPhysicalRestrictionTag': CLASS,
        'PublicWorkoutProfessional': CLASS,
        'PublicWorkoutProfessionalRole': CLASS,
        'PublicWorkoutProgram': CLASS,
        'PublicWorkoutProgramDelivery': CLASS,
        'PublicWorkoutProgramDraft': CLASS,
        'PublicWorkoutProgramDraftSource': CLASS,
        'PublicWorkoutProgramDraftStatus': CLASS,
        'PublicWorkoutPushSubscription': CLASS,
        'PublicWorkoutRefundRequest': CLASS,
        'PublicWorkoutRefundRequestStatus': CLASS,
        'PublicWorkoutRestAlert': CLASS,
        'PublicWorkoutRestAlertStatus': CLASS,
        'PublicWorkoutStaffCredential': CLASS,
        'PublicWorkoutSubscription': CLASS,
        'PublicWorkoutSubscriptionEvent': CLASS,
        'PublicWorkoutSubscriptionStatus': CLASS,
        'PublicWorkoutTestimonial': CLASS,
        'PublicWorkoutTier': CLASS,
        'PublicWorkoutTrainingExperience': CLASS,
        'PublicWorkoutTrainingGoal': CLASS,
        'PublicWorkoutTrainingLocation': CLASS,
        'PublicWorkoutTrainingProfile': CLASS,
        'PublicWorkoutTrainingSession': CLASS,
        'PublicWorkoutTrainingSet': CLASS,
        'PublicWorkoutTrainingSetRevision': CLASS,
        'PublicWorkoutWaitlistEntry': CLASS,
        'PublicWorkoutWaitlistStatus': CLASS,
        'PublicWorkoutWeeklyReviewCache': CLASS,
        'PublicWorkoutWorkItem': CLASS,
        'PublicWorkoutWorkItemStatus': CLASS,
        'PublicWorkoutWorkItemType': CLASS,
    },
    'student_app.views.public_workout_views': {
        'PublicWorkoutDetailView': CLASS,
        'PublicWorkoutDownloadPdfView': CLASS,
        'PublicWorkoutExportDataView': CLASS,
        'PublicWorkoutLocalStorageBackupView': CLASS,
        'PublicWorkoutMealPlanView': CLASS,
        'PublicWorkoutOnboardingCompleteView': CLASS,
        'PublicWorkoutPackageView': CLASS,
        'PublicWorkoutPreviewView': CLASS,
        'PublicWorkoutRecordAssessmentView': CLASS,
        'PublicWorkoutRecordLoadView': CLASS,
        'PublicWorkoutSignOutView': CLASS,
        'PublicWorkoutTemplatePreviewView': CLASS,
        'PublicWorkoutWeeklyReviewView': CLASS,
        # Reexportados hoje (vem de public_workout_pwa, public_workout_access e
        # public_workouts.catalog) e importados daqui por student_app/views/
        # __init__.py, comandos e testes.
        'PublicWorkoutManifestView': CLASS,
        'PublicWorkoutOfflineView': CLASS,
        'PublicWorkoutServiceWorkerView': CLASS,
        'PUBLIC_WORKOUT_LIBRARY': CONSTANT,
        'PUBLIC_WORKOUT_OWNER_COOKIE': CONSTANT,
        # Privado e reexportado, mas tests/test_public_workout_access_split.py
        # confere que e o mesmo objeto de public_workout_access.
        '_get_public_workout_entry': FUNCTION,
    },
    'student_identity.public_workout_views': {
        'PublicWorkoutAccountSignOutView': CLASS,
        'PublicWorkoutAccountView': CLASS,
        'PublicWorkoutAnalyticsAccessMixin': CLASS,
        'PublicWorkoutBillingPortalView': CLASS,
        'PublicWorkoutCheckoutReturnView': CLASS,
        'PublicWorkoutColdSignupView': CLASS,
        'PublicWorkoutCustomCheckoutView': CLASS,
        'PublicWorkoutFunnelAnalyticsLoginView': CLASS,
        'PublicWorkoutFunnelAnalyticsLogoutView': CLASS,
        'PublicWorkoutFunnelAnalyticsView': CLASS,
        'PublicWorkoutFunnelEventView': CLASS,
        'PublicWorkoutGoogleCallbackView': CLASS,
        'PublicWorkoutGoogleStartView': CLASS,
        'PublicWorkoutJullyAnalyticsView': CLASS,
        'PublicWorkoutJullyLandingView': CLASS,
        'PublicWorkoutLandingView': CLASS,
        'PublicWorkoutLoginView': CLASS,
        'PublicWorkoutNutritionIntakeView': CLASS,
        'PublicWorkoutPrivacyView': CLASS,
        'PublicWorkoutRefundRequestView': CLASS,
        'PublicWorkoutSubscribeView': CLASS,
        'PublicWorkoutTermsView': CLASS,
        'PublicWorkoutTrainingIntakeView': CLASS,
        # Privado, mas importado por student_identity/test_public_workout_oauth.py.
        '_build_public_workout_google_provider': FUNCTION,
    },
    'public_workouts.templatetags.public_workouts_extras': {
        # `register` e o que o Django procura no {% load public_workouts_extras %}.
        'register': CONSTANT,
        'current_period_phase': FUNCTION,
        'current_period_week_number': FUNCTION,
        'cycle_summary_rows': FUNCTION,
        'day_short': FUNCTION,
        'dict_get': FUNCTION,
        'glossary_highlight': FUNCTION,
        'guided_series': FUNCTION,
        'hero_progress_chart': FUNCTION,
        'humanize_movement_slug': FUNCTION,
        'initial': FUNCTION,
        'load_chart_points': FUNCTION,
        'movement_load_display': FUNCTION,
        'movement_name': FUNCTION,
        'movement_shows_plate_calculator': FUNCTION,
        'periodization_chart_points': FUNCTION,
        'periodization_phase_banner': FUNCTION,
        'personal_record': FUNCTION,
        'personal_record_rows': FUNCTION,
        'program_summary': FUNCTION,
        'program_week_progress': FUNCTION,
        'progress_chart_for_movement': FUNCTION,
        'reps_phases': FUNCTION,
        'resolve_movement_display_name': FUNCTION,
        'share_content_for_chart': FUNCTION,
        'sibling_variations': FUNCTION,
        'todays_default_load_entry': FUNCTION,
        'todays_load_entry': FUNCTION,
        'todays_logged_idempotency_key': FUNCTION,
        'todays_logged_reps': FUNCTION,
        'todays_logged_rir': FUNCTION,
        'todays_logged_weight': FUNCTION,
        'todays_top_set_weight': FUNCTION,
        'week_overview': FUNCTION,
        'week_streak_label': FUNCTION,
        'workout_day_presentation': FUNCTION,
        'workout_day_selection': FUNCTION,
        'workout_greeting': FUNCTION,
    },
}


def _kind_of(value) -> str:
    if inspect.isclass(value):
        return EXCEPTION if issubclass(value, BaseException) else CLASS
    if inspect.isfunction(value):
        return FUNCTION
    return CONSTANT


@pytest.mark.parametrize('module_path', sorted(IMPORT_CONTRACT))
def test_facade_keeps_every_name_imported_today(module_path):
    module = importlib.import_module(module_path)
    expected = IMPORT_CONTRACT[module_path]

    missing = sorted(name for name in expected if not hasattr(module, name))
    changed = sorted(
        f'{name}: era {kind}, agora {_kind_of(getattr(module, name))}'
        for name, kind in expected.items()
        if hasattr(module, name) and _kind_of(getattr(module, name)) != kind
    )

    assert not missing, (
        f'{module_path} perdeu nomes que outros arquivos importam hoje: {missing}. '
        'Se virou fachada, reexporte-os (ADR-1 de docs/plans/split-arquivos-grandes-plano.md).'
    )
    assert not changed, f'{module_path} mudou a natureza de nomes do contrato: {changed}'


def test_templatetag_library_is_still_a_django_library():
    from django import template

    module = importlib.import_module('public_workouts.templatetags.public_workouts_extras')

    assert isinstance(module.register, template.Library)
