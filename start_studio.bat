@echo off
title Studio Yofamo
cd /d "%~dp0studio"

where node >nul 2>nul
if errorlevel 1 (
  echo Node.js belum terpasang. Install versi LTS dari https://nodejs.org lalu jalankan file ini lagi.
  pause
  exit /b 1
)

if not exist node_modules (
  echo Menyiapkan Studio Yofamo untuk pertama kali, tunggu sebentar...
  call npm install --no-audit --no-fund
  if errorlevel 1 (
    echo Gagal memasang paket. Cek koneksi internet lalu coba lagi.
    pause
    exit /b 1
  )
)

echo Studio Yofamo berjalan di http://127.0.0.1:3210  (tutup jendela ini untuk berhenti)
start "" cmd /c "timeout /t 6 /nobreak >nul & start http://127.0.0.1:3210"
call npm run dev
pause
