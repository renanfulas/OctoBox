Set-Location 'C:\Users\renan\OneDrive\Documents\OctoBOX'
Get-Content '.env.homolog.local' | ForEach-Object {
  if ($_ -match '^(?!#)([^=]+)=(.*)$') {
    [System.Environment]::SetEnvironmentVariable($matches[1], $matches[2], 'Process')
  }
}
[System.Environment]::SetEnvironmentVariable('DJANGO_ENV', 'development', 'Process')
[System.Environment]::SetEnvironmentVariable('DJANGO_DEBUG', 'True', 'Process')
[System.Environment]::SetEnvironmentVariable('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1', 'Process')
[System.Environment]::SetEnvironmentVariable('DJANGO_CSRF_TRUSTED_ORIGINS', 'http://localhost:8012,http://127.0.0.1:8012', 'Process')
& '.\.venv\Scripts\python.exe' manage.py runserver 127.0.0.1:8012 --noreload
