@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul 2>&1
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

echo ===========================================
echo  Korean Hallucination Detector
echo ===========================================
echo.

where python >nul 2>nul
if errorlevel 1 goto NOPYTHON

if exist ".setup_done" goto RUN

echo First run - installing packages. This takes 5-10 minutes.
echo Please wait. Do not close this window.
echo.
if exist ".venv" rmdir /s /q ".venv"
python -m venv ".venv"
if errorlevel 1 goto VENVFAIL
call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 goto PIPFAIL
echo done> ".setup_done"
goto START

:RUN
call ".venv\Scripts\activate.bat"

:START
echo.
echo Starting. A browser window will open shortly.
echo Keep this window open. Closing it stops the app.
echo.
python app_cpu.py
echo.
echo The app has stopped.
pause
exit /b

:NOPYTHON
echo [ERROR] Python is not installed.
echo.
echo   1. Go to https://www.python.org/downloads/
echo   2. Download and run the installer
echo   3. IMPORTANT: check "Add Python to PATH" at the bottom
echo   4. Then run this file again
echo.
pause
exit /b

:VENVFAIL
echo [ERROR] Could not create the virtual environment.
echo Send this screen to the project owner.
pause
exit /b

:PIPFAIL
echo [ERROR] Package installation failed.
echo Check your internet connection and run this file again.
if exist ".setup_done" del ".setup_done"
pause
exit /b
