# Script para testar todos os endpoints da API

$api = "http://localhost:5000"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Testando Endpoints da API" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Cores
function Print-Test {
    param([string]$endpoint, [string]$method)
    Write-Host "Testando: $method $endpoint" -ForegroundColor Yellow
}

function Print-Success {
    param([string]$msg)
    Write-Host "  ✅ $msg" -ForegroundColor Green
}

function Print-Error {
    param([string]$msg)
    Write-Host "  ❌ $msg" -ForegroundColor Red
}

# 1. Health
Print-Test "$api/health" "GET"
try {
    $res = Invoke-WebRequest -Uri "$api/health" -Method GET -UseBasicParsing -ErrorAction Stop
    Print-Success "Health: $($res.StatusCode) OK"
} catch {
    Print-Error "Health: $($_.Exception.Response.StatusCode)"
}

Write-Host ""

# 2. CRUD Endpoints
$endpoints = @(
    @{method="GET"; url="/api/v1/financeiro"; name="Listar Financeiro"},
    @{method="GET"; url="/api/v1/caixa"; name="Listar Caixa"},
    @{method="GET"; url="/api/v1/auditoria"; name="Listar Auditoria"},
    @{method="POST"; url="/sync/financeiro"; name="Sync Financeiro"}
)

foreach ($ep in $endpoints) {
    Print-Test "$api$($ep.url)" "$($ep.method)"
    try {
        $res = Invoke-WebRequest -Uri "$api$($ep.url)" -Method $ep.method -UseBasicParsing -ErrorAction Stop
        Print-Success "$($ep.name): $($res.StatusCode) OK"
    } catch {
        $statusCode = $_.Exception.Response.StatusCode.Value__
        Print-Error "$($ep.name): $statusCode"
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Teste Concluido" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
