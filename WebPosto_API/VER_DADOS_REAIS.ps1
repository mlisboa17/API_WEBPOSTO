# Ver dados reais sendo retornados pela API

$api = "http://localhost:5000"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Dados Reais da API" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. Financeiro
Write-Host "1. Financeiro (GET /api/v1/financeiro)" -ForegroundColor Yellow
Write-Host ""
try {
    $res = Invoke-WebRequest -Uri "$api/api/v1/financeiro?limite=10" -Method GET -UseBasicParsing
    $data = $res.Content | ConvertFrom-Json
    Write-Host ($data | ConvertTo-Json -Depth 10)
} catch {
    Write-Host "Erro: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host ""

# 2. Caixa
Write-Host "2. Caixa (GET /api/v1/caixa)" -ForegroundColor Yellow
Write-Host ""
try {
    $res = Invoke-WebRequest -Uri "$api/api/v1/caixa?limite=10" -Method GET -UseBasicParsing
    $data = $res.Content | ConvertFrom-Json
    Write-Host ($data | ConvertTo-Json -Depth 10)
} catch {
    Write-Host "Erro: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
