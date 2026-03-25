# scripts/clean_history.ps1
# OctoBox Security Hardening - History Purge Script (PowerShell)

Write-Host "--- OctoBox History Purge ---" -ForegroundColor Cyan

# 1. Ensure git-filter-repo is installed
if (-not (Get-Command git-filter-repo -ErrorAction SilentlyContinue)) {
    Write-Host "git-filter-repo not found. Installing via pip..." -ForegroundColor Yellow
    pip install git-filter-repo
}

# 2. Add backups/ to .gitignore if not already there
$gitignore = ".gitignore"
$rules = @("backups/", "*.sqlite3", "*.dump", "snapshots/", ".coverage*")
foreach ($rule in $rules) {
    if (-not (Select-String -Path $gitignore -Pattern [regex]::Escape($rule) -Quiet)) {
        Write-Host "Adding $rule to .gitignore..."
        Add-Content -Path $gitignore -Value $rule
    }
}

# 3. Commit .gitignore change
git add .gitignore
git commit -m "security: ensure .gitignore blocks backups and artifacts"

# 4. Perform History Purge
Write-Host "Purging sensitive paths from history..." -ForegroundColor Cyan
# This will remove the files from all commits in the current branch
# Using python -m git_filter_repo as it is more reliable on some systems
python -m git_filter_repo --path backups/ --path snapshots/ --path-glob "*.sqlite3" --path-glob "*.dump" --invert-paths --force

# 5. Cleanup
Write-Host "Running aggressive garbage collection..." -ForegroundColor Green
git reflog expire --expire=now --all
git gc --prune=now --aggressive

Write-Host "--- HISTORY PURGE COMPLETE ---" -ForegroundColor Green
Write-Host "NEXT STEP: You MUST manually run the following to update the remote server:" -ForegroundColor Cyan
Write-Host "git push origin --force --all" -ForegroundColor Cyan
Write-Host "WARNING: This will rewrite history for all team members!" -ForegroundColor Red
