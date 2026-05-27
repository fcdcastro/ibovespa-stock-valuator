$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$logFile = Join-Path $projectDir "server.log"
$python = "python"

# Kill any existing server on port 5000
$existing = Get-NetTCPConnection -LocalPort 5000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess
if ($existing) { Stop-Process -Id $existing -Force -ErrorAction SilentlyContinue }
Start-Sleep -Seconds 1

# Start server in background
$process = Start-Process -NoNewWindow -FilePath $python -ArgumentList "server.py" -WorkingDirectory $projectDir -PassThru -RedirectStandardOutput $logFile -RedirectStandardError $logFile

Write-Host "Servidor iniciado (PID: $($process.Id)) em http://localhost:5000"
Write-Host "Log: $logFile"
Write-Host "Para encerrar: Stop-Process -Id $($process.Id) -Force"

# Keep the script running (required for scheduled task)
$process.WaitForExit()
