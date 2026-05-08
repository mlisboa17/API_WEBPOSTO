# Um comando que sobe a API Logos (imagem raiz Dockerfile).
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

Write-Host ">>> Build + up (docker-compose.logos.yml)..." -ForegroundColor Cyan
docker compose -f docker-compose.logos.yml up --build -d

Write-Host ">>> Aguardando health..." -ForegroundColor Cyan
$ok = $false
for ($i = 0; $i -lt 30; $i++) {
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:8000/auditoria/health" -UseBasicParsing -TimeoutSec 3
        if ($r.StatusCode -eq 200) { $ok = $true; break }
    } catch { }
    Start-Sleep -Seconds 2
}

if (-not $ok) {
    Write-Host "Health nao respondeu. Logs:" -ForegroundColor Red
    docker compose -f docker-compose.logos.yml logs --tail 80 auditoria
    exit 1
}

Write-Host "OK: http://localhost:8000/auditoria/health" -ForegroundColor Green
Write-Host "Docs: http://localhost:8000/docs" -ForegroundColor Green
