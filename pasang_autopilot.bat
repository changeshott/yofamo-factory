@echo off
title Autopilot Yofamo
cd /d "%~dp0"
if /i "%~1"=="hapus" goto hapus

where python >nul 2>nul
if errorlevel 1 (
  echo Python tidak ditemukan. Install Python dulu lalu jalankan file ini lagi.
  pause
  exit /b 1
)

echo Memasang penjadwal Windows: autopilot Yofamo berjalan tiap jam (tanpa jendela), selama laptop menyala.
schtasks /Create /F /TN "Yofamo Autopilot" /SC HOURLY /MO 1 /ST 00:07 /TR "wscript.exe \"%~dp0autopilot.vbs\""
if errorlevel 1 (
  echo Gagal memasang jadwal. Coba klik kanan file ini lalu "Run as administrator".
  pause
  exit /b 1
)
python agents\autopilot.py nyala
python agents\upload\jadwal.py --lihat
echo.
echo Selesai. Tim akan membuat video dan menjadwalkan tayang sendiri.
echo - Lihat jadwal ^& status: Studio Yofamo, meja Uli, bagian Autopilot.
echo - Log tiap jam: folder logs\autopilot-TANGGAL.txt
echo - Matikan: tombol Matikan di Studio, atau jalankan:  pasang_autopilot.bat hapus
echo Pastikan laptop tidak tidur (Settings, System, Power: Sleep = Never saat dicas).
pause
exit /b 0

:hapus
schtasks /Delete /F /TN "Yofamo Autopilot"
python agents\autopilot.py mati
echo Autopilot dilepas dari penjadwal Windows.
pause
exit /b 0
