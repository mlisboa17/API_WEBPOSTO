# Testar endpoints REAIS descobertos no Swagger webPosto

$baseUrl = "http://web.qualityautomacao.com.br"
$apiKey = "4d6bbe21-92b2-4052-bcb5-a82c86858fd7"
$hoje = (Get-Date).ToString("yyyy-MM-dd")
$ontem = (Get-Date).AddDays(-30).ToString("yyyy-MM-dd")

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Testando webPosto API - Endpoints Reais" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

function Testar-Endpoint {
    param([string]$nome, [string]$url)
    Write-Host "[$nome]" -ForegroundColor Yellow
    Write-Host "URL: $url" -ForegroundColor Gray
    try {
        $res = Invoke-WebRequest -Uri $url -Method GET -UseBasicParsing -TimeoutSec 15 -ErrorAction Stop
        Write-Host "✅ Status: $($res.StatusCode)" -ForegroundColor Green
        $content = $res.Content | ConvertFrom-Json -ErrorAction SilentlyContinue
        if ($content) {
            Write-Host ($content | ConvertTo-Json -Depth 3) -ForegroundColor White
        } else {
            Write-Host $res.Content -ForegroundColor White
        }
    } catch {
        $status = $_.Exception.Response.StatusCode.Value__
        Write-Host "❌ Status: $status" -ForegroundColor Red
        Write-Host "Erro: $($_.Exception.Message)" -ForegroundColor Red
    }
    Write-Host ""
}

# 1. Integração / Abastecimento (endpoint descoberto)
Testar-Endpoint "INTEGRACAO/ABASTECIMENTO" "$baseUrl/INTEGRACAO/ABASTECIMENTO?CHAVE=$apiKey&dataInicial=$ontem&dataFinal=$hoje"

# 2. Versão com path diferente
Testar-Endpoint "integracao/abastecimento (minúsculas)" "$baseUrl/integracao/abastecimento?CHAVE=$apiKey&dataInicial=$ontem&dataFinal=$hoje"

# 3. Tentar financeiro com datas
Testar-Endpoint "INTEGRACAO/FINANCEIRO" "$baseUrl/INTEGRACAO/FINANCEIRO?CHAVE=$apiKey&dataInicial=$ontem&dataFinal=$hoje"

# 4. Tentar titulos
Testar-Endpoint "INTEGRACAO/TITULOS" "$baseUrl/INTEGRACAO/TITULOS?CHAVE=$apiKey&dataInicial=$ontem&dataFinal=$hoje"

# 5. Tentar caixa
Testar-Endpoint "INTEGRACAO/CAIXA" "$baseUrl/INTEGRACAO/CAIXA?CHAVE=$apiKey&dataInicial=$ontem&dataFinal=$hoje"

# 6. Root - ver o que está disponível
Testar-Endpoint "Root API" "$baseUrl/"

# 7. API Docs
Testar-Endpoint "Swagger JSON" "$baseUrl/v3/api-docs"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "IMPORTANTE: Acesse o Swagger no navegador:" -ForegroundColor Yellow
Write-Host "http://web.qualityautomacao.com.br/webjars/swagger-ui/index.html?configUrl=/v3/api-docs/swagger-config" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
