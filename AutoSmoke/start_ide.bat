@echo off
chcp 65001 >nul
setlocal EnableExtensions

cd /d "%~dp0"
echo AutoSmoke IDE Launcher
echo ----------------------

set "SMOKE_ROOT=%CD%"
set "PORT=5000"
set "PYTHONIOENCODING=utf-8"
set "AUTOSMOKE_ROOT=%SMOKE_ROOT%"

if not exist logs mkdir logs
if not exist runtime mkdir runtime

echo [1] Stop old AutoSmoke IDE processes...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'python.exe' -and $_.CommandLine -like '*autosmoke_web_ide.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"

timeout /t 1 /nobreak >nul

echo [2] Clean stale PID lock...
if exist runtime\web_ide.pid del /q runtime\web_ide.pid >nul 2>nul

echo [3] Choose Python...
set "PY_EXE=C:\Users\Administrator\.workbuddy\binaries\python\versions\3.13.12\python.exe"
if not exist "%PY_EXE%" set "PY_EXE=python"
echo     Python: %PY_EXE%

echo [4] Start IDE on port %PORT%...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$env:PYTHONIOENCODING='utf-8'; $env:AUTOSMOKE_ROOT='%SMOKE_ROOT%'; Start-Process -FilePath '%PY_EXE%' -ArgumentList 'autosmoke_web_ide.py','--port','%PORT%','--no-debug' -WorkingDirectory '%SMOKE_ROOT%' -WindowStyle Hidden -RedirectStandardOutput '%SMOKE_ROOT%\logs\web_ide_%PORT%.out.log' -RedirectStandardError '%SMOKE_ROOT%\logs\web_ide_%PORT%.err.log'"

echo [5] Wait for server...
set "READY="
for /l %%i in (1,1,20) do (
  powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "try { $r=Invoke-WebRequest -Uri 'http://127.0.0.1:%PORT%/api/ide/status' -UseBasicParsing -TimeoutSec 1; if ($r.StatusCode -eq 200) { exit 0 } } catch { exit 1 }"
  if not errorlevel 1 (
    set "READY=1"
    goto :OPEN
  )
  timeout /t 1 /nobreak >nul
)

:OPEN
if defined READY (
  echo [6] IDE is ready.
  start http://localhost:%PORT%
) else (
  echo [6] IDE did not respond yet. Check logs:
  echo     logs\web_ide_%PORT%.out.log
  echo     logs\web_ide_%PORT%.err.log
)

echo.
echo Access: http://localhost:%PORT%
echo.
pause
