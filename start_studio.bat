@echo off
title Studio Yofamo
cd /d "%~dp0studio"

where node >nul 2>nul
if errorlevel 1 (
  echo Node.js belum terpasang. Install versi LTS dari https://nodejs.org lalu jalankan file ini lagi.
  pause
  exit /b 1
)

rem Mesin video HyperFrames (Kai) di folder project: dipasang sekali kalau Node.js 22+
pushd "%~dp0"
if not exist node_modules\hyperframes (
  for /f "tokens=1 delims=." %%v in ('node -p "process.versions.node"') do set NODEMAJOR=%%v
  call :cekNode
)
popd

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
exit /b 0

:cekNode
if %NODEMAJOR% GEQ 22 (
  echo Memasang mesin video HyperFrames untuk Kai, sekali saja...
  call npm install --no-audit --no-fund
  call npx hyperframes browser ensure
) else (
  echo Catatan: Node.js versi %NODEMAJOR%. Grafis gerak Kai butuh Node.js 22+. Kai memakai mesin ffmpeg dulu.
)
exit /b 0
