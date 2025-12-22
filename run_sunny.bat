@echo off
cd /d "%~dp0"
call venv\Scripts\activate.bat
cd apps
streamlit run app_sunny.py
pause
