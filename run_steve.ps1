# Jalankan Steve (Claude Code, kuota langganan Pro). Dipanggil manual atau dari Task Scheduler.
# Hasil laporan dan log tampil di Studio Yofamo (start_studio.bat).
Set-Location -Path $PSScriptRoot

$stamp = Get-Date -Format "yyyy-MM-dd_HHmmss"
$log = "logs\steve-$stamp.txt"
New-Item -ItemType Directory -Force -Path logs | Out-Null

claude -p "/steve-analis" --model sonnet --max-turns 40 `
  --allowedTools "Bash(python agents/steve/fetch_stats.py *)" "Bash(python agents/steve/fetch_stats.py)" `
                 "PowerShell(python agents/steve/fetch_stats.py *)" "PowerShell(python agents/steve/fetch_stats.py)" `
                 "Read" "Write" "Glob" "Grep" `
  2>&1 | Out-File -FilePath $log -Encoding utf8
exit $LASTEXITCODE
