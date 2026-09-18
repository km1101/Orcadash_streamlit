@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\streamlit.exe" (
  echo Creating virtual environment...
  py -3 -m venv .venv
  call .venv\Scripts\activate.bat
  python -m pip install --upgrade pip
  python -m pip install -r requirements.txt
) else (
  call .venv\Scripts\activate.bat
)
echo Starting Orcadash with: %CD%\.venv\Scripts\python.exe
.venv\Scripts\streamlit.exe run streamlit_app\app.py
endlocal
