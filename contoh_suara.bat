@echo off
rem Buat contoh semua jenis suara (gratis) lalu buka foldernya. Pilih: python agents\suara\contoh_suara.py --pakai <nama>
cd /d "%~dp0"
set PY=python
if defined YOFAMO_PYTHON set PY=%YOFAMO_PYTHON%
%PY% agents\suara\contoh_suara.py
if exist suara-khas\contoh start "" "suara-khas\contoh"
echo.
echo Dengarkan file mp3-nya. Untuk memakai satu suara, ketik (ganti NAMA dengan nama di DAFTAR.txt):
echo     python agents\suara\contoh_suara.py --pakai NAMA
pause
