[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
New-Item -ItemType Directory -Path (Join-Path $PSScriptRoot 'logs') -Force | Out-Null
function Start-IndependentService([string]$Role,[string]$NodeExecutable = '') {
    # WMI creates the service outside the launcher's Windows job object.
    $python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
    $entry = Join-Path $PSScriptRoot 'utils\service_entry.py'
    $command = '"{0}" -X utf8 "{1}" {2}' -f $python,$entry,$Role
    if ($NodeExecutable) { $command += ' --node "{0}"' -f $NodeExecutable }
    $startup = New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ShowWindow=[uint16]0}
    $created = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine=$command;CurrentDirectory=$PSScriptRoot;ProcessStartupInformation=$startup}
    if ($created.ReturnValue -ne 0) { throw "Independent service startup failed: $($created.ReturnValue)" }
    return Get-Process -Id $created.ProcessId -ErrorAction Stop
}
function Invoke-OmniPostStartup {
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$env:PYTHONUTF8 = '1'
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path $PSScriptRoot '.browsers'
New-Item -ItemType Directory -Path (Join-Path $PSScriptRoot 'logs') -Force | Out-Null
$statePath = Join-Path $PSScriptRoot 'logs\local-processes.json'
$managedRoots = @{}
if (Test-Path -LiteralPath $statePath) {
    $previous = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
    foreach ($entry in $previous) {
        $live = Get-Process -Id $entry.Id -ErrorAction SilentlyContinue
        if ($live -and $live.StartTime -and $live.StartTime.ToUniversalTime().Ticks -eq ([datetime]$entry.StartTime).ToUniversalTime().Ticks) {
            $managedRoots[[int]$entry.Id] = $true
        }
    }
}
if ($managedRoots.Count -gt 0) {
    for ($check = 0; $check -lt 6; $check++) {
        $parents = @{}
        foreach ($processInfo in (Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId)) {
            $parents[[int]$processInfo.ProcessId] = [int]$processInfo.ParentProcessId
        }
        $ownedPorts = $true
        foreach ($port in @(5409,5173)) {
            $listener = Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue | Select-Object -First 1
            $belongs = $false
            if ($listener) {
                $ownerId = [int]$listener.OwningProcess
                $visited = @{}
                while ($ownerId -gt 0 -and -not $visited.ContainsKey($ownerId)) {
                    $visited[$ownerId] = $true
                    if ($managedRoots.ContainsKey($ownerId)) { $belongs = $true; break }
                    if (-not $parents.ContainsKey($ownerId)) { break }
                    $ownerId = $parents[$ownerId]
                }
            }
            if (-not $belongs) { $ownedPorts = $false }
        }
        if ($ownedPorts) {
            try {
                $api = Invoke-WebRequest -Uri 'http://127.0.0.1:5409/local/status' -UseBasicParsing -TimeoutSec 2
                $web = Invoke-WebRequest -Uri 'http://127.0.0.1:5173/' -UseBasicParsing -TimeoutSec 2
                if ($api.StatusCode -eq 200 -and ($api.Content | ConvertFrom-Json).data.running -eq $true -and $web.StatusCode -eq 200) {
                    Write-Output 'OmniPost is already running. Opening the existing management console.'
                    return
                }
            } catch { }
        }
        Start-Sleep -Milliseconds 500
    }
    throw 'Recorded OmniPost services are not ready. Use stop.cmd, then start.cmd to recover.'
}
foreach ($port in @(5409,5173)) {
    if (Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue) { throw "Port $port is already in use." }
}
$started = @()
try {
    $pythonPath = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
    $backend = Start-IndependentService -Role 'backend'
    $started += $backend
    $nodePath = (Get-Command node.exe -ErrorAction Stop).Source
    $frontend = Start-IndependentService -Role 'frontend' -NodeExecutable $nodePath
    $started += $frontend
    @($started | ForEach-Object { [pscustomobject]@{Id=$_.Id;StartTime=$_.StartTime.ToUniversalTime().ToString('o')} }) | ConvertTo-Json | Set-Content -LiteralPath $statePath -Encoding UTF8
    $ready = $false
    for ($attempt=0; $attempt -lt 30; $attempt++) {
        try {
            $api = Invoke-WebRequest -Uri 'http://127.0.0.1:5409/getAccounts' -UseBasicParsing -TimeoutSec 2
            $web = Invoke-WebRequest -Uri 'http://127.0.0.1:5173/' -UseBasicParsing -TimeoutSec 2
            if ($api.StatusCode -eq 200 -and $web.StatusCode -eq 200) { $ready=$true; break }
        } catch { Start-Sleep -Milliseconds 500 }
    }
    if (-not $ready) { throw 'Startup check failed. See logs directory.' }
    Write-Output 'OmniPost ready: http://127.0.0.1:5173/'
} catch {
    foreach ($process in $started) { if (-not $process.HasExited) { Stop-Process -Id $process.Id -ErrorAction SilentlyContinue } }
    throw
}
}
$startupLock = $null
$lockPath = Join-Path $PSScriptRoot 'logs\startup.lock'
for ($lockAttempt = 0; $lockAttempt -lt 120; $lockAttempt++) {
    try {
        $startupLock = [System.IO.File]::Open($lockPath, [System.IO.FileMode]::OpenOrCreate, [System.IO.FileAccess]::ReadWrite, [System.IO.FileShare]::None)
        break
    } catch [System.IO.IOException] { Start-Sleep -Milliseconds 250 }
}
if (-not $startupLock) { throw 'Another startup is still running. Please try again shortly.' }
try { Invoke-OmniPostStartup } finally { $startupLock.Dispose() }
