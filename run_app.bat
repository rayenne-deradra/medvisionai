@echo off
REM Starts MedVisionAI with this folder's virtual environment. Double-click or run: run_app.bat
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Creating the virtual environment and installing packages - first time only, takes a few minutes...
  python -m venv .venv || (echo Python was not found. Install Python 3.12 from python.org first. & pause & exit /b 1)
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
)
".venv\Scripts\python.exe" -m streamlit run app.py
pause
