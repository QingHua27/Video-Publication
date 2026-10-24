param([ValidateRange(0,10)][int]$DelaySeconds = 0)
$ErrorActionPreference = 'Stop'
if ($DelaySeconds -gt 0) { Start-Sleep -Seconds $DelaySeconds }
$statePath = Join-Path $PSScriptRoot 'logs\local-processes.json'
if (-not (Test-Path -LiteralPath $statePath)) { Write-Output 'No recorded local processes.'; return }
$entries = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
$snapshot = @(Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId)
$targets = @{}
foreach ($entry in $entries) {
    $live = Get-Process -Id $entry.Id -ErrorAction SilentlyContinue
    if (-not $live -or -not $live.StartTime -or $live.StartTime.ToUniversalTime().Ticks -ne ([datetime]$entry.StartTime).ToUniversalTime().Ticks) { continue }
    $queue = New-Object System.Collections.Queue
    $queue.Enqueue([pscustomobject]@{Id=[int]$entry.Id;Depth=0})
    while ($queue.Count -gt 0) {
        $item = $queue.Dequeue()
        # The delayed stopper is itself a backend child; let it finish stopping both services.
        if ($item.Id -eq $PID -or $targets.ContainsKey($item.Id)) { continue }
        $owned = Get-Process -Id $item.Id -ErrorAction SilentlyContinue
        if (-not $owned -or -not $owned.StartTime) { continue }
        $targets[$item.Id] = [pscustomobject]@{Id=$owned.Id;Ticks=$owned.StartTime.ToUniversalTime().Ticks;Depth=$item.Depth}
        foreach ($child in $snapshot) {
            if ([int]$child.ParentProcessId -eq $item.Id) {
                $queue.Enqueue([pscustomobject]@{Id=[int]$child.ProcessId;Depth=$item.Depth+1})
            }
        }
    }
}
foreach ($target in @($targets.Values | Sort-Object Depth -Descending)) {
    $live = Get-Process -Id $target.Id -ErrorAction SilentlyContinue
    if ($live -and $live.StartTime -and $live.StartTime.ToUniversalTime().Ticks -eq $target.Ticks) {
        Stop-Process -Id $live.Id -ErrorAction SilentlyContinue
    }
}
Write-Output 'OmniPost local services stopped.'
