@echo off
cd /d "%~dp0"
call venv\Scripts\activate.bat
python src/lucy_scanner_realtime.py %*
pause
