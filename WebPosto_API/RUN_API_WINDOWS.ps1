# webPosto API - Script PowerShell para Windows
# Execute com: powershell -ExecutionPolicy Bypass -File RUN_API_WINDOWS.ps1

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  webPosto API - Inicializador Windows" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Ir para a pasta do script
Set-Location $PSScriptRoot

# Verificar se está na pasta correta
if (-not (Test-Path "src\main_minimal.py")) {
    Write-Host "ERRO: Nao encontrou src\main_minimal.py" -ForegroundColor Red
    Write-Host "Certifique-se de executar este script da pasta raiz do projeto." -ForegroundColor Red
    Read-Host "Pressione ENTER para sair"
    exit 1
}

Write-Host "[1/3] Verificando dependencias..." -ForegroundColor Yellow
$depCheck = python -m pip list | Select-String -Pattern "fastapi|uvicorn|pydantic"
if (-not $depCheck) {
    Write-Host ""
    Write-Host "AVISO: Faltam dependencias! Instalando..." -ForegroundColor Yellow
    Write-Host ""
    python -m pip install fastapi uvicorn pydantic sqlalchemy httpx tenacity pydantic-settings aiosqlite structlog --break-system-packages
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERRO: Falha ao instalar dependencias" -ForegroundColor Red
        Read-Host "Pressione ENTER para sair"
        exit 1
    }
}

Write-Host ""
Write-Host "[2/3] Testando importacoes..." -ForegroundColor Yellow
python teste_import.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "AVISO: Alguns modulos podem estar faltando" -ForegroundColor Yellow
    Write-Host "Continuando mesmo assim..." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "[3/3] Iniciando API..." -ForegroundColor Yellow
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  API rodando em http://localhost:5000" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Acesse:" -ForegroundColor Green
Write-Host "  - Health:  http://localhost:5000/health" -ForegroundColor Green
Write-Host "  - Admin:   $(Get-Location)\admin-dashboard.html" -ForegroundColor Green
Write-Host "  - Vendas:  $(Get-Location)\vendas-dashboard.html" -ForegroundColor Green
Write-Host "  - Diag:    $(Get-Location)\diagnostico.html" -ForegroundColor Green
Write-Host ""
Write-Host "Pressione CTRL+C para parar" -ForegroundColor Green
Write-Host ""

python -m uvicorn src.main_minimal:app --host 0.0.0.0 --port 5000 --reload

Read-Host "API parou. Pressione ENTER para sair"
