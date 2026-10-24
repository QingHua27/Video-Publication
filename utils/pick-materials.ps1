param([ValidateSet('all','video','image','folder')][string]$Kind = 'all')
$ErrorActionPreference = 'Stop'
function Trace-Picker($stage) { Add-Content -LiteralPath (Join-Path $PSScriptRoot '../logs/picker.log') -Value ('{0:o} {1} {2}' -f (Get-Date),$PID,$stage) }
Trace-Picker 'starting'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
Add-Type -AssemblyName System.Windows.Forms
Trace-Picker 'forms-loaded'
if ($Kind -eq 'folder') {
    $dialog = New-Object System.Windows.Forms.FolderBrowserDialog
    $dialog.Description = '选择关联的素材文件夹（含子文件夹，只记录路径）'
    $dialog.ShowNewFolderButton = $false
} else {
$dialog = New-Object System.Windows.Forms.OpenFileDialog
$dialog.Title = '选择本地素材（只登记路径，不复制文件）'
$dialog.Multiselect = $true
$dialog.AutoUpgradeEnabled = $false
$dialog.RestoreDirectory = $true
$dialog.CheckFileExists = $true
$video = '视频文件|*.mp4;*.mov;*.avi;*.mkv;*.webm;*.m4v;*.flv;*.wmv'
$image = '图片文件|*.png;*.jpg;*.jpeg;*.webp;*.bmp;*.gif'
if ($Kind -eq 'video') { $dialog.Filter = "$video|所有文件|*.*" }
elseif ($Kind -eq 'image') { $dialog.Filter = "$image|所有文件|*.*" }
else { $dialog.Filter = "所有素材|*.mp4;*.mov;*.avi;*.mkv;*.webm;*.m4v;*.flv;*.wmv;*.png;*.jpg;*.jpeg;*.webp;*.bmp;*.gif|$video|$image|所有文件|*.*" }
}
$owner = New-Object System.Windows.Forms.Form
$owner.TopMost = $true
$owner.ShowInTaskbar = $true
$owner.Text = 'OmniPost — 选择本地素材'
$owner.StartPosition = 'CenterScreen'
$owner.Size = New-Object System.Drawing.Size(360, 120)
try {
    Trace-Picker 'showing-owner'
    $owner.Show()
    Trace-Picker 'owner-shown'
    $owner.Activate()
    [System.Windows.Forms.Application]::DoEvents()
    Trace-Picker 'showing-dialog'
    if ($dialog.ShowDialog($owner) -eq [System.Windows.Forms.DialogResult]::OK) {
        if ($Kind -eq 'folder') { ConvertTo-Json -InputObject @($dialog.SelectedPath) -Compress }
        else { ConvertTo-Json -InputObject @($dialog.FileNames) -Compress }
    } else { Write-Output '[]' }
} finally { $dialog.Dispose(); $owner.Dispose() }
