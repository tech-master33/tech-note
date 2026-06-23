@echo off
title TechNote Installer
echo TechNote Installer
echo ==================
echo.
echo This will install TechNote and its dependencies.
echo.

:: Check winget (Windows 10+)
where winget >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: winget not found. This installer requires Windows 10 or later.
    echo Please install Git and Python manually, then run:
    echo   git clone --branch main https://github.com/tech-master33/tech-note.git
    echo   cd tech-note
    echo   pip install -r requirements.txt
    echo   python boot_64.py
    pause
    exit /b 1
)

:: Check / Install Git
where git >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Installing Git...
    winget install --silent --accept-source-agreements Git.Git
    if %ERRORLEVEL% neq 0 (
        echo ERROR: Failed to install Git. Please install it manually.
        pause
        exit /b 1
    )
    :: Add git to PATH for the current session
    for /f "tokens=*" %%i in ('where git 2^>nul') do set GIT_PATH=%%~dpi
    if defined GIT_PATH set "PATH=%PATH%;%GIT_PATH%"
)

:: Check / Install Python
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Installing Python 3.11...
    winget install --silent --accept-source-agreements Python.Python.3.11
    if %ERRORLEVEL% neq 0 (
        echo ERROR: Failed to install Python. Please install it manually.
        pause
        exit /b 1
    )
    for /f "tokens=*" %%i in ('where python 2^>nul') do set PYTHON_PATH=%%~dpi
    if defined PYTHON_PATH set "PATH=%PATH%;%PYTHON_PATH%"
)

:: Clone or Pull
if exist "tech-note\" (
    echo Updating TechNote...
    cd tech-note
    git pull origin main
) else (
    echo Downloading TechNote...
    git clone --branch main https://github.com/tech-master33/tech-note.git
    if %ERRORLEVEL% neq 0 (
        echo ERROR: Failed to download TechNote. Check your internet connection.
        pause
        exit /b 1
    )
    cd tech-note
)

:: Install Python dependencies
echo Installing dependencies...
pip install -r requirements.txt
if %ERRORLEVEL% neq 0 (
    echo WARNING: Some dependencies may not have installed correctly.
)

echo.
echo TechNote installed successfully.
set /p LAUNCH="Press Y to launch TechNote now, or any other key to exit: "
if /i "%LAUNCH%"=="Y" (
    echo Starting TechNote...
    python boot_64.py
) else (
    echo To run TechNote later, navigate to the tech-note folder and run:
    echo   python boot_64.py
)
