$taskName = "LeGranServer"
$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$scriptPath = Join-Path $projectDir "start_server_background.ps1"

# Check if task already exists
$existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "Tareja '$taskName' ja existe. Removendo..."
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}

# Create scheduled task to run on user logon
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`" -WindowStyle Hidden"
$trigger = New-ScheduledTaskTrigger -AtLogOn
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description "Servidor Flask Le Gran (correlacao, API, etc.)"

Write-Host ""
Write-Host "Servidor configurado para iniciar automaticamente ao fazer login!"
Write-Host "Acesse: http://localhost:5000"
Write-Host ""
Write-Host "Para remover: Desinstalar-TarefaAgendada -TaskName '$taskName'"
