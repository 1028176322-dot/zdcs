@echo off
setlocal EnableExtensions

cd /d "%~dp0"

set "SMOKE_ROOT=%CD%"
set "PORT=5000"
set "PYTHONIOENCODING=utf-8"
set "AUTOSMOKE_ROOT=%SMOKE_ROOT%"
set "MAX_WAIT_SECONDS=60"

if not exist "logs" mkdir "logs"
if not exist "runtime" mkdir "runtime"

echo.
echo AutoSmoke IDE Launcher
echo ----------------------
echo Root: %SMOKE_ROOT%
echo Port: %PORT%
echo.

echo [1/6] Stop old AutoSmoke IDE processes...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'python.exe' -and $_.CommandLine -like '*autosmoke_web_ide.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" >nul 2>nul

timeout /t 1 /nobreak >nul

echo [2/6] Clean stale PID lock...
if exist "runtime\web_ide.pid" del /q "runtime\web_ide.pid" >nul 2>nul

echo [3/6] Choose Python...
set "PY_EXE=C:\Users\Administrator\.workbuddy\binaries\python\versions\3.13.12\python.exe"
if not exist "%PY_EXE%" (
  where python >nul 2>nul
  if errorlevel 1 (
    echo ERROR: python.exe was not found.
    echo Please install Python or update PY_EXE in this file.
    pause
    exit /b 1
  )
  set "PY_EXE=python"
)
echo Python: %PY_EXE%

echo [4/6] Start IDE...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$env:PYTHONIOENCODING='utf-8'; $env:AUTOSMOKE_ROOT='%SMOKE_ROOT%'; $p=Start-Process -FilePath '%PY_EXE%' -ArgumentList 'autosmoke_web_ide.py','--port','%PORT%','--no-debug' -WorkingDirectory '%SMOKE_ROOT%' -WindowStyle Hidden -RedirectStandardOutput '%SMOKE_ROOT%\logs\web_ide_%PORT%.out.log' -RedirectStandardError '%SMOKE_ROOT%\logs\web_ide_%PORT%.err.log' -PassThru; $p.Id | Set-Content -Encoding ascii '%SMOKE_ROOT%\runtime\web_ide.launcher.pid'"

echo [5/6] Wait for server...
set "READY="
for /l %%i in (1,1,%MAX_WAIT_SECONDS%) do (
  powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $r=Invoke-WebRequest -Uri 'http://127.0.0.1:%PORT%/api/ide/status' -UseBasicParsing -TimeoutSec 1; if ($r.StatusCode -eq 200) { exit 0 } } catch { exit 1 }" >nul 2>nul
  if not errorlevel 1 (
    set "READY=1"
    goto :OPEN
  )
  timeout /t 1 /nobreak >nul
)

:OPEN
echo [6/6] Open browser...
start "" "http://127.0.0.1:%PORT%/"

echo.
if defined READY (
  echo IDE is ready: http://127.0.0.1:%PORT%/
) else (
  echo WARNING: IDE did not respond within %MAX_WAIT_SECONDS% seconds.
  echo Browser was opened anyway.
  echo.
  echo Check logs:
  echo   %SMOKE_ROOT%\logs\web_ide_%PORT%.out.log
  echo   %SMOKE_ROOT%\logs\web_ide_%PORT%.err.log
)

echo.
echo If the browser page is blank, wait a few seconds and refresh.
if /i "%~1"=="nopause" exit /b 0
echo Press any key to close this launcher window.
pause >nul
