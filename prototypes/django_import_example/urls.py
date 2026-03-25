from django.urls import path
from . import views

app_name = "django_import_example"

urlpatterns = [
    path("upload/", views.upload_import, name="upload_import"),
    path("jobs/<int:job_id>/", views.job_status, name="job_status"),
]
