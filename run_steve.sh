#!/usr/bin/env bash
# Jalankan Steve (Claude Code, kuota langganan). Mac/Linux, manual atau dari crontab.
# Hasil laporan dan log tampil di Studio Yofamo (start_studio.bat).
set -u
cd "$(dirname "$0")"
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
mkdir -p logs
claude -p "/steve-analis" --model sonnet --max-turns 40 \
  --allowedTools "Bash(python agents/steve/fetch_stats.py *)" "Bash(python3 agents/steve/fetch_stats.py *)" \
                 "Bash(python agents/steve/fetch_stats.py)" "Bash(python3 agents/steve/fetch_stats.py)" \
                 "Read" "Write" "Glob" "Grep" \
  > "logs/steve-$(date +%Y-%m-%d_%H%M%S).txt" 2>&1
