# Testar conexao com API webPosto real

$baseUrl = if ($env:WEBPOSTO_BASE_URL) { $env:WEBPOSTO_BASE_URL } else { "https://web.qualityautomacao.com.br" }
$apiKey = $env:WEBPOSTO_API_KEY
if (-not $apiKey) { Write-Error "Defina WEBPOSTO_API_KEY no ambiente ou .env"; exit 1 }

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Testando Conexao com webPosto API" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Base URL: $baseUrl" -ForegroundColor Yellow
Write-Host "API Key: $apiKey" -ForegroundColor Yellow
Write-Host ""

# 1. Testar /api/v1/financeiro/titulos-receber
Write-Host "1. Testando GET /api/v1/financeiro/titulos-receber" -ForegroundColor Yellow
try {
    $url = "$baseUrl/api/v1/financeiro/titulos-receber?CHAVE=$apiKey&skip=0&limit=5"
    Write-Host "   URL: $url" -ForegroundColor Gray
    $res = Invoke-WebRequest -Uri $url -Method GET -UseBasicParsing -TimeoutSec 10
    Write-Host "   ✅ Status: $($res.StatusCode)" -ForegroundColor Green
    Write-Host "   Resposta:" -ForegroundColor Green
    $res.Content | ConvertFrom-Json | ConvertTo-Json -Depth 3 | Write-Host
} catch {
    Write-Host "   ❌ Erro: $($_.Exception.Message)" -ForegroundColor Red
    if ($_.Exception.Response) {
        Write-Host "   Status: $($_.Exception.Response.StatusCode.Value__)" -ForegroundColor Red
        Write-Host "   Resposta: $($_.Exception.Response.Content)" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host ""

# 2. Testar /api/v1/caixa
Write-Host "2. Testando GET /api/v1/caixa" -ForegroundColor Yellow
try {
    $url = "$baseUrl/api/v1/caixa?CHAVE=$apiKey&skip=0&limit=5"
    Write-Host "   URL: $url" -ForegroundColor Gray
    $res = Invoke-WebRequest -Uri $url -Method GET -UseBasicParsing -TimeoutSec 10
    Write-Host "   ✅ Status: $($res.StatusCode)" -ForegroundColor Green
    Write-Host "   Resposta:" -ForegroundColor Green
    $res.Content | ConvertFrom-Json | ConvertTo-Json -Depth 3 | Write-Host
} catch {
    Write-Host "   ❌ Erro: $($_.Exception.Message)" -ForegroundColor Red
    if ($_.Exception.Response) {
        Write-Host "   Status: $($_.Exception.Response.StatusCode.Value__)" -ForegroundColor Red
        Write-Host "   Resposta: $($_.Exception.Response.Content)" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
