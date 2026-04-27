from django.apps import AppConfig


class StudentIdentityConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'student_identity'
    verbose_name = 'Student Identity'

    def ready(self):
        from student_identity.listeners import connect_student_identity_listeners
        connect_student_identity_listeners()
