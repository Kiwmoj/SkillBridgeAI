# Stops the server and ngrok tunnel started by start_public.ps1.
$root = Split-Path -Parent $PSScriptRoot
$pidFile = Join-Path $root '.public-pids'
if (-not (Test-Path $pidFile)) { Write-Host 'Nothing to stop (no .public-pids file).'; return }
foreach ($id in Get-Content $pidFile) {
    $proc = Get-Process -Id $id -ErrorAction SilentlyContinue
    if ($proc) { Stop-Process -Id $id -Force; Write-Host "Stopped $($proc.ProcessName) (PID $id)" }
}
Remove-Item $pidFile
