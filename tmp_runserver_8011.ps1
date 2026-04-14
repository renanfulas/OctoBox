Set-Location 'C:\Users\renan\OneDrive\Documents\OctoBOX'
Get-Content '.env.homolog.local' | ForEach-Object {
  if ($_ -match '^(?!#)([^=]+)=(.*)$') {
    [System.Environment]::SetEnvironmentVariable($matches[1], $matches[2], 'Process')
  }
}
& '.\.venv\Scripts\python.exe' manage.py runserver 127.0.0.1:8011 --noreload
