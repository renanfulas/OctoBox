from django.contrib import admin

from .models import (
    DayPlan,
    PlanBlock,
    PlanMovement,
    ReplicationBatch,
    SessionWorkout,
    SessionWorkoutFollowUpAction,
    SessionWorkoutOperationalMemory,
    SessionWorkoutBlock,
    SessionWorkoutMovement,
    SessionWorkoutRevision,
    StudentWorkoutView,
    StudentExerciseMax,
    WeeklyWodPlan,
    WorkoutWeeklyManagementCheckpoint,
)


@admin.register(StudentExerciseMax)
class StudentExerciseMaxAdmin(admin.ModelAdmin):
    list_display = ('student', 'exercise_label', 'one_rep_max_kg')
    search_fields = ('student__full_name', 'exercise_label', 'exercise_slug')


class SessionWorkoutMovementInline(admin.TabularInline):
    model = SessionWorkoutMovement
    extra = 1


class SessionWorkoutBlockInline(admin.StackedInline):
    model = SessionWorkoutBlock
    extra = 1


@admin.register(SessionWorkout)
class SessionWorkoutAdmin(admin.ModelAdmin):
    list_display = ('session', 'title', 'status', 'version', 'approved_at')
    search_fields = ('session__title', 'title')
    list_filter = ('status',)
    inlines = [SessionWorkoutBlockInline]


@admin.register(SessionWorkoutRevision)
class SessionWorkoutRevisionAdmin(admin.ModelAdmin):
    list_display = ('workout', 'event', 'version', 'created_at')
    search_fields = ('workout__title', 'workout__session__title')
    list_filter = ('event',)


@admin.register(SessionWorkoutBlock)
class SessionWorkoutBlockAdmin(admin.ModelAdmin):
    list_display = ('title', 'kind', 'workout', 'sort_order')
    list_filter = ('kind',)
    search_fields = ('title', 'workout__session__title')
    inlines = [SessionWorkoutMovementInline]


@admin.register(SessionWorkoutMovement)
class SessionWorkoutMovementAdmin(admin.ModelAdmin):
    list_display = ('movement_label', 'block', 'load_type', 'load_value', 'sort_order')
    list_filter = ('load_type',)
    search_fields = ('movement_label', 'movement_slug', 'block__title')


@admin.register(StudentWorkoutView)
class StudentWorkoutViewAdmin(admin.ModelAdmin):
    list_display = ('student', 'workout', 'view_count', 'last_viewed_at')
    search_fields = ('student__full_name', 'workout__title', 'workout__session__title')


@admin.register(SessionWorkoutFollowUpAction)
class SessionWorkoutFollowUpActionAdmin(admin.ModelAdmin):
    list_display = ('workout', 'action_label', 'status', 'resolved_by', 'resolved_at')
    list_filter = ('status',)
    search_fields = ('workout__title', 'workout__session__title', 'action_label', 'action_key')


@admin.register(SessionWorkoutOperationalMemory)
class SessionWorkoutOperationalMemoryAdmin(admin.ModelAdmin):
    list_display = ('workout', 'kind', 'created_by', 'created_at')
    list_filter = ('kind',)
    search_fields = ('workout__title', 'workout__session__title', 'note')


@admin.register(WorkoutWeeklyManagementCheckpoint)
class WorkoutWeeklyManagementCheckpointAdmin(admin.ModelAdmin):
    list_display = ('week_start', 'execution_status', 'responsible_role', 'closure_status', 'updated_by', 'updated_at')
    list_filter = ('execution_status', 'responsible_role', 'closure_status')
    search_fields = ('summary_note',)


@admin.register(WeeklyWodPlan)
class WeeklyWodPlanAdmin(admin.ModelAdmin):
    list_display = ('label', 'week_start', 'status', 'created_by', 'created_at')
    list_filter = ('status',)
    search_fields = ('label',)


@admin.register(DayPlan)
class DayPlanAdmin(admin.ModelAdmin):
    list_display = ('weekly_plan', 'weekday', 'sort_order')
    list_filter = ('weekday',)
    search_fields = ('weekly_plan__label',)


@admin.register(PlanBlock)
class PlanBlockAdmin(admin.ModelAdmin):
    list_display = ('title', 'kind', 'day_plan', 'timecap_min', 'rounds', 'sort_order')
    list_filter = ('kind',)
    search_fields = ('title', 'day_plan__weekly_plan__label')


@admin.register(PlanMovement)
class PlanMovementAdmin(admin.ModelAdmin):
    list_display = ('movement_label_raw', 'movement_slug', 'plan_block', 'sets', 'reps_spec', 'sort_order')
    search_fields = ('movement_label_raw', 'movement_slug', 'plan_block__title')


@admin.register(ReplicationBatch)
class ReplicationBatchAdmin(admin.ModelAdmin):
    list_display = ('weekly_plan', 'created_by', 'sessions_targeted', 'sessions_created', 'undone_at', 'created_at')
    search_fields = ('weekly_plan__label',)
