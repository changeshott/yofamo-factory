@echo off
rem Buat contoh semua jenis suara (gratis) lalu buka foldernya. Pilih: python agents\suara\contoh_suara.py --pakai NAMA
cd /d "%~dp0"
rem Pilih Python yang sama dengan pabrik: yang punya edge-tts DAN yt-dlp (python pertama di PATH bisa milik aplikasi lain)
set PY=
if defined YOFAMO_PYTHON set PY=%YOFAMO_PYTHON%
if not defined PY (
  for /f "delims=" %%p in ('py -3 -c "import edge_tts, yt_dlp, sys; print(sys.executable)" 2^>nul') do set PY=%%p
)
if not defined PY (
  for /f "delims=" %%p in ('where python 2^>nul') do (
    if not defined PY "%%p" -c "import edge_tts, yt_dlp" >nul 2>nul && set PY=%%p
  )
)
if not defined PY set PY=python
echo Python: %PY%
"%PY%" agents\suara\contoh_suara.py
if errorlevel 3 (
  echo.
  set /p JAWAB=Perbarui paket edge-tts sekarang lalu coba lagi? [Y/T] 
)
if /i "%JAWAB%"=="Y" (
  "%PY%" -m pip install -U edge-tts
  "%PY%" agents\suara\contoh_suara.py
)
if exist suara-khas\contoh start "" "suara-khas\contoh"
echo.
echo Untuk memakai satu suara (ganti NAMA dengan nama di DAFTAR.txt):
echo     "%PY%" agents\suara\contoh_suara.py --pakai NAMA
pause
