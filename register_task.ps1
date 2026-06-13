# Registers the weekly windowless refresh in Task Scheduler (current user, no admin).
$ErrorActionPreference = "Stop"
$proj = "C:\Users\USER\OneDrive\Desktop\linkedin-content-lab"
$action  = New-ScheduledTaskAction -Execute "wscript.exe" -Argument "`"$proj\run_refresh.vbs`""
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At 7:00am
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 1)
Register-ScheduledTask -TaskName "LinkedIn Content Lab Refresh" -Action $action -Trigger $trigger `
    -Settings $settings -Description "Weekly LinkedIn Content Lab refresh (windowless via VBS)" -Force | Out-Null
$info = Get-ScheduledTask -TaskName "LinkedIn Content Lab Refresh" | Get-ScheduledTaskInfo
Write-Output ("Registered 'LinkedIn Content Lab Refresh'. Next run: " + $info.NextRunTime)
