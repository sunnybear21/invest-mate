@echo off
cd /d "%~dp0"
call venv\Scripts\activate.bat
streamlit run apps\app_main.py
pause
