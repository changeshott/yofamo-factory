@echo off
rem Pasang mesin suara natural Yofamo (VoxCPM2 + faster-whisper) di Python terpisah: .venv-suara
rem Butuh: GPU NVIDIA (disarankan 8 GB VRAM), Python 3.12, koneksi internet (unduhan besar, sekitar 8 GB).
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Python launcher "py" tidak ada. Pasang Python 3.12: winget install Python.Python.3.12
  exit /b 1
)
py -3.12 -c "print('ok')" >nul 2>nul
if errorlevel 1 (
  echo Python 3.12 belum terpasang. Jalankan: winget install Python.Python.3.12  lalu ulangi setup_suara.bat
  exit /b 1
)
if not exist .venv-suara (
  echo Membuat .venv-suara ...
  py -3.12 -m venv .venv-suara || exit /b 1
)
set PYS=.venv-suara\Scripts\python.exe
%PYS% -m pip install --upgrade pip
echo Memasang PyTorch dengan CUDA (sekitar 3 GB) ...
%PYS% -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu128 || exit /b 1
echo Memasang VoxCPM2 dan faster-whisper ...
%PYS% -m pip install voxcpm faster-whisper soundfile || exit /b 1
%PYS% -c "import torch; print('CUDA:', torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else '')"
echo.
echo Selesai. Cek: python agents\suara\cek_gpu.py
echo Model VoxCPM2 (sekitar 5 GB) diunduh otomatis saat pertama membuat suara.
