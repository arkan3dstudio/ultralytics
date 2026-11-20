@echo off
setlocal
set "ROBOT_PYTHON=%~dp0..\.venv\Scripts\python.exe"
if not exist "%ROBOT_PYTHON%" (
    echo Virtualenv YOLO tidak ditemukan di folder induk.
    pause
    exit /b 1
)
"%ROBOT_PYTHON%" -B "%~dp0project_02_tracking.py" %*
set "ROBOT_RESULT=%ERRORLEVEL%"
if not "%ROBOT_RESULT%"=="0" pause
exit /b %ROBOT_RESULT%
