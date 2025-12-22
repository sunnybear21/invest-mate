@echo off
cd /d "%~dp0"
call venv\Scripts\activate.bat
cd apps
streamlit run trading_journal_app.py
pause
