@echo off
rem Dev server contra o cluster Postgres local 5433 (ver memoria octobox-local-postgres-cluster)
set DATABASE_URL=postgresql://octobox_app:octobox_local@127.0.0.1:5433/octobox_control
cd /d C:\dev\OctoBox
rem Sem --noreload: o cache de template do Django 6 (ativo mesmo em DEBUG) so invalida via autoreload.
.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
