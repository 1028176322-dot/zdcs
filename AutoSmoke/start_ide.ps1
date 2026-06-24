$ErrorActionPreference = "SilentlyContinue"

# 定位到脚本所在目录（AutoSmoke 根目录）
$SmokeRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $SmokeRoot

# 日志目录
$LogDir = Join-Path $SmokeRoot "logs"
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir -Force | Out-Null }

# 清理旧 AutoSmoke IDE 进程
Get-CimInstance Win32_Process |
  Where-Object {
    $_.Name -eq "python.exe" -and
    $_.CommandLine -like "*autosmoke_web_ide.py*"
  } |
  ForEach-Object {
    Stop-Process -Id $_.ProcessId -Force
  }

Start-Sleep -Seconds 1

# 清理残留 PID 锁文件
$PidFile = Join-Path $SmokeRoot "runtime" "web_ide.pid"
if (Test-Path $PidFile) { Remove-Item $PidFile -Force }

# 启动新 IDE（使用管理 Python，不含绝对路径硬编码）
$env:PYTHONIOENCODING = "utf-8"
$env:AUTOSMOKE_ROOT = $SmokeRoot

# 从 WorkBuddy 环境取 Python 路径；找不到则用 PATH 上的 python
$PythonExe = if (Get-Command python -ErrorAction SilentlyContinue) { "python" } else { "python3" }

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$OutLog = Join-Path $LogDir "web_ide_${Timestamp}.out.log"
$ErrLog = Join-Path $LogDir "web_ide_${Timestamp}.err.log"

Start-Process `
  -FilePath "python.exe" `
  -ArgumentList "autosmoke_web_ide.py" `
  -WorkingDirectory $SmokeRoot `
  -WindowStyle Hidden `
  -RedirectStandardOutput $OutLog `
  -RedirectStandardError $ErrLog

Write-Host "✅ AutoSmoke IDE 已启动"
Write-Host "   工作目录: $SmokeRoot"
Write-Host "   输出日志: $OutLog"
Write-Host "   错误日志: $ErrLog"
Write-Host "   访问地址: http://localhost:5000"

# 等待服务器就绪后自动打开浏览器
Start-Sleep -Seconds 3
try {
    $request = [System.Net.WebRequest]::Create("http://localhost:5000/api/ide/status")
    $request.Timeout = 3000
    $response = $request.GetResponse()
    if ($response.StatusCode -eq 200) {
        Start-Process "http://localhost:5000"
        Write-Host "🌐 浏览器已打开 http://localhost:5000"
    }
    $response.Close()
} catch {
    Write-Host "⚠️  服务未就绪，请手动打开 http://localhost:5000"
}
