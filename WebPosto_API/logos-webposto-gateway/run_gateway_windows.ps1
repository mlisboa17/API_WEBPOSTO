param(
    [switch]$StartApi,
    [switch]$UseDocker,
    [switch]$StopApi
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$ApiPort = 8050

function Get-GatewayApiPid {
    try {
        $conn = Get-NetTCPConnection -LocalPort $ApiPort -State Listen -ErrorAction SilentlyContinue |
            Select-Object -First 1
        if ($null -ne $conn -and $null -ne $conn.OwningProcess) {
            return [int]$conn.OwningProcess
        }
    }
    catch {
        return $null
    }
    return $null
}

function Stop-GatewayApiProcess {
    $apiPid = Get-GatewayApiPid
    if ($null -eq $apiPid) {
        Write-Host "Nenhum processo escutando na porta $ApiPort foi encontrado." -ForegroundColor Yellow
        return
    }

    try {
        Stop-Process -Id $apiPid -Force -ErrorAction SilentlyContinue
        Write-Host "Processo da API encerrado com sucesso (PID: $apiPid)." -ForegroundColor Green
    }
    catch {
        Write-Host "Nao foi possivel encerrar o PID $apiPid. Continuando sem falhar." -ForegroundColor Yellow
    }
}

Write-Host "[1/4] Entrando na pasta do gateway..." -ForegroundColor Cyan
Set-Location -Path $PSScriptRoot

if ($StopApi -and -not $StartApi -and -not $UseDocker) {
    Write-Host "[2/2] Encerrando API local na porta $ApiPort..." -ForegroundColor Cyan
    Stop-GatewayApiProcess
    Write-Host "Concluido." -ForegroundColor Green
    return
}

Write-Host "[2/4] Rodando testes automatizados (sem curl)..." -ForegroundColor Cyan
python -m pytest -q --tb=line

if ($StartApi -and -not $UseDocker) {
    Write-Host "[3/4] Subindo API local na porta $ApiPort..." -ForegroundColor Cyan
    Start-Process -FilePath python -ArgumentList "-m uvicorn --app-dir . src.main:app --host 127.0.0.1 --port $ApiPort" -WindowStyle Minimized
    Start-Sleep -Seconds 2
}

if ($UseDocker) {
    Write-Host "[3/4] Subindo via Docker Compose..." -ForegroundColor Cyan
    docker compose up -d
    Start-Sleep -Seconds 2
}

Write-Host "[4/4] Testando /health com Invoke-RestMethod..." -ForegroundColor Cyan
$response = Invoke-RestMethod -Uri "http://127.0.0.1:$ApiPort/health" -Method Get
$response | ConvertTo-Json -Depth 5

if ($StartApi -and -not $UseDocker) {
    Write-Host "[cleanup] Encerrando processo local da API..." -ForegroundColor Cyan
    Stop-GatewayApiProcess
}

Write-Host "Concluido." -ForegroundColor Green
