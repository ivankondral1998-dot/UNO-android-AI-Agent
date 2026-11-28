@echo off
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1
".venv\Scripts\python.exe" -B supervise.py audit_tests
if errorlevel 1 exit /b 1
".venv\Scripts\python.exe" -B supervise.py efficiency_tests
if errorlevel 1 exit /b 1
".venv\Scripts\python.exe" -B supervise.py safety_tests
if errorlevel 1 exit /b 1
".venv\Scripts\python.exe" -B supervise.py acceptance
if errorlevel 1 exit /b 1
".venv\Scripts\python.exe" -B supervise.py train check --corpus "UNO_RU_COMMERCIAL_CORPUS_20261126.zip" %*
if errorlevel 1 exit /b 1
".venv\Scripts\python.exe" -B supervise.py acceptance --profile "UNO_RU_COMMERCIAL_CORPUS_20261126.zip"
exit /b %ERRORLEVEL%
