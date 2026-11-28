@echo off
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1
".venv\Scripts\python.exe" -B supervise.py train test --corpus "UNO_RU_COMMERCIAL_CORPUS_20261126.zip" %*
exit /b %ERRORLEVEL%
