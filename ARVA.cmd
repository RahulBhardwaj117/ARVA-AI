@echo off
setlocal
cd /d "%~dp0"

if not "%~1"=="" goto run

:menu
cls
echo.
echo   ARVA AI PROJECT CONTROL
echo   =======================
echo.
echo   1. Start ARVA AI
echo   2. Quick health check
echo   3. Full verification (tests, audit, build, live events)
echo   4. Show status
echo   5. Run measured demo
echo   6. Restart
echo   7. Stop
echo   8. Factory reset
echo   Q. Quit
echo.
choice /c 12345678Q /n /m "Choose an option: "

set "ARVA_CHOICE=%errorlevel%"
set "ARVA_ACTION="
if "%ARVA_CHOICE%"=="9" exit /b 0
if "%ARVA_CHOICE%"=="8" set "ARVA_ACTION=reset"
if "%ARVA_CHOICE%"=="7" set "ARVA_ACTION=stop"
if "%ARVA_CHOICE%"=="6" set "ARVA_ACTION=restart"
if "%ARVA_CHOICE%"=="5" set "ARVA_ACTION=demo"
if "%ARVA_CHOICE%"=="4" set "ARVA_ACTION=status"
if "%ARVA_CHOICE%"=="3" set "ARVA_ACTION=verify"
if "%ARVA_CHOICE%"=="2" set "ARVA_ACTION=check"
if "%ARVA_CHOICE%"=="1" set "ARVA_ACTION=start"

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0arva.ps1" %ARVA_ACTION%
echo.
pause
goto menu

:run
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0arva.ps1" %*
exit /b %errorlevel%
