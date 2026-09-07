# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
#
# Register (or remove) the weekly LAMMPS upstream watch as a Windows Scheduled Task.
#
# The task runs hidden and writes to a log file -- nothing may appear on the owner's screen
# (KEEP rules/12). It runs `scripts/watch_upstream.py --weekly --pull`, which writes
# docs/watch/YYYY-WW.md and refreshes the snapshot.
#
#   .\scripts\register_watch_task.ps1 -DryRun          # print what would be registered
#   .\scripts\register_watch_task.ps1                  # register (Mondays 09:00 local)
#   .\scripts\register_watch_task.ps1 -Day Sunday -At 18:30
#   .\scripts\register_watch_task.ps1 -Remove
#
# Registering a scheduled task writes to the user's task store; -DryRun changes nothing.

[CmdletBinding()]
param(
    [string]$TaskName = "lammps-skill upstream watch",
    [string]$Python   = "$env:USERPROFILE\miniconda3\envs\lammps\python.exe",
    [string]$Day      = "Monday",
    [string]$At       = "09:00",
    [switch]$Pull,
    [switch]$Remove,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$product = Split-Path -Parent $PSScriptRoot
$script  = Join-Path $product "scripts\watch_upstream.py"
$logDir  = Join-Path (Split-Path -Parent $product) "logs"
$log     = Join-Path $logDir "watch-upstream.log"

$status = @()
function Step($name, $ok) { $script:status += "$name : $ok" }

if ($Remove) {
    if ($DryRun) {
        Step "unregister" "DRY-RUN"
    } else {
        try {
            Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction Stop
            Step "unregister" "OK"
        } catch {
            Step "unregister" "FAIL ($($_.Exception.Message))"
        }
    }
    $status | ForEach-Object { Write-Output $_ }
    if ($status -match "FAIL") { exit 1 } else { exit 0 }
}

if (-not (Test-Path $script))  { Write-Output "watch_upstream.py not found at $script"; exit 2 }
if (-not (Test-Path $Python))  { Write-Output "python not found at $Python (pass -Python <path>)"; exit 2 }

$args = "-u `"$script`" --weekly"
if ($Pull) { $args += " --pull" }
# cmd.exe wrapper so both streams reach one log file; the task itself is hidden.
$cmd = "/c `"`"$Python`" $args >> `"$log`" 2>&1`""

Write-Output "task     : $TaskName"
Write-Output "runs     : $Python $args"
Write-Output "schedule : weekly, $Day at $At"
Write-Output "log      : $log"

if ($DryRun) {
    Step "register" "DRY-RUN"
    $status | ForEach-Object { Write-Output $_ }
    exit 0
}

if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }

try {
    $action    = New-ScheduledTaskAction -Execute "$env:SystemRoot\System32\cmd.exe" -Argument $cmd -WorkingDirectory $product
    $trigger   = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $Day -At $At
    # Hidden, and only when the machine is not on battery-saver rules that would surprise the owner.
    $settings  = New-ScheduledTaskSettingsSet -Hidden -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
    $principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings `
                           -Principal $principal -Description "Weekly LAMMPS upstream watch (lammps-skill, playbook S8 / rule 23)" -Force | Out-Null
    Step "register" "OK"
} catch {
    Step "register" "FAIL ($($_.Exception.Message))"
}

$status | ForEach-Object { Write-Output $_ }
if ($status -match "FAIL") { exit 1 } else { exit 0 }
