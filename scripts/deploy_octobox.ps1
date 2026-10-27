$ErrorActionPreference = 'Stop'

Write-Host @'
O deploy/rollback por SSH deste launcher foi desativado. O checkout local não é
uma fonte confiável para publicar uma release aprovada. Use o workflow
VPS Deploy (Hostgator São Paulo), disparado na branch main com o SHA completo;
o rollback operacional deve seguir docs/rollout/hostgator/rollback.md.
'@ -ForegroundColor Red
exit 2
