# Starts SkillBridge AI on http://127.0.0.1:8012 and exposes it publicly via ngrok.
# The ngrok authtoken stays in %LOCALAPPDATA%\ngrok\ngrok.yml (never in this repo).
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$port = 8012
$pidFile = Join-Path $root '.public-pids'

$ngrok = (Get-Command ngrok -ErrorAction SilentlyContinue).Source
if (-not $ngrok) {
    $ngrok = Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\Ngrok.Ngrok*\ngrok.exe" -ErrorAction SilentlyContinue |
        Select-Object -First 1 -ExpandProperty FullName
}
if (-not $ngrok) { throw 'ngrok not found. Install it with: winget install Ngrok.Ngrok' }

$python = Join-Path $root '.venv\Scripts\python.exe'
$listening = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
$pids = @()
if ($listening) {
    Write-Host "Port $port already in use; reusing the running server."
} else {
    $app = Start-Process $python -ArgumentList '-m', 'uvicorn', 'apps.backend.main:app', '--host', '127.0.0.1', '--port', $port `
        -WorkingDirectory $root -WindowStyle Minimized -PassThru
    $pids += $app.Id
    $ok = $false
    foreach ($i in 1..30) {
        Start-Sleep 1
        try { Invoke-RestMethod "http://127.0.0.1:$port/api/v1/health" | Out-Null; $ok = $true; break } catch {}
    }
    if (-not $ok) { throw "Server did not become healthy on port $port." }
}

$tunnel = Start-Process $ngrok -ArgumentList 'http', $port -WindowStyle Minimized -PassThru
$pids += $tunnel.Id
$pids | Set-Content $pidFile

$url = $null
foreach ($i in 1..20) {
    Start-Sleep 1
    try {
        $url = ((Invoke-RestMethod 'http://127.0.0.1:4040/api/tunnels').tunnels |
            Where-Object { $_.public_url -like 'https*' } | Select-Object -First 1).public_url
        if ($url) { break }
    } catch {}
}
if (-not $url) { throw 'ngrok did not report a public URL. Check the minimized ngrok window.' }

Write-Host ''
Write-Host "SkillBridge AI is public at: $url" -ForegroundColor Green
Write-Host 'Stop everything with: .\scripts\stop_public.ps1'
