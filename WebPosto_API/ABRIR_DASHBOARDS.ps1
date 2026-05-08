# Abrir todos os dashboards no navegador

$baseFolder = "C:\Users\mlisb\OneDrive\ProjetosAntigravy\LOGOS SPACE\Api_WebPosto\WebPosto_API"

Write-Host "Abrindo dashboards..." -ForegroundColor Green
Write-Host ""

# Admin Dashboard (CRUD)
Write-Host "1. Admin Dashboard (CRUD)..." -ForegroundColor Cyan
Start-Process "$baseFolder\admin-dashboard.html"
Start-Sleep -Seconds 1

# Vendas Dashboard (Relatorios)
Write-Host "2. Vendas Dashboard (Relatorios)..." -ForegroundColor Cyan
Start-Process "$baseFolder\vendas-dashboard.html"
Start-Sleep -Seconds 1

# Diagnostico (Testes)
Write-Host "3. Diagnostico (Testes)..." -ForegroundColor Cyan
Start-Process "$baseFolder\diagnostico.html"

Write-Host ""
Write-Host "✅ Dashboards abertos!" -ForegroundColor Green
Write-Host ""
Write-Host "Certifique-se que a API esta rodando em:" -ForegroundColor Yellow
Write-Host "  http://localhost:5000/health" -ForegroundColor Yellow
