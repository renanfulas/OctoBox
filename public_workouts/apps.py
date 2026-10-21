from django.apps import AppConfig


class PublicWorkoutsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'public_workouts'

    def ready(self):
        from . import checks  # noqa: F401
