@echo off
REM webPosto API — Script para rodar no Windows
REM Copie este arquivo para a pasta raiz do projeto

echo.
echo ========================================
echo   webPosto API — Inicializador Windows
echo ========================================
echo.

REM Ir para a pasta do projeto
cd /d "%~dp0"

REM Verificar se está na pasta correta
if not exist "src\main_minimal.py" (
    echo ERRO: Nao encontrou src\main_minimal.py
    echo Certifique-se de executar este script da pasta raiz do projeto.
    pause
    exit /b 1
)

echo [1/3] Verificando dependencias...
python -m pip list | findstr /i "fastapi uvicorn pydantic" > nul
if errorlevel 1 (
    echo.
    echo AVISO: Faltam dependencias! Instalando...
    echo.
    python -m pip install fastapi uvicorn pydantic sqlalchemy httpx tenacity pydantic-settings aiosqlite structlog --break-system-packages
    if errorlevel 1 (
        echo ERRO: Falha ao instalar dependencias
        pause
        exit /b 1
    )
)

echo.
echo [2/3] Testando importacoes...
python teste_import.py
if errorlevel 1 (
    echo AVISO: Alguns modulos podem estar faltando
    echo Continuando mesmo assim...
)

echo.
echo [3/3] Iniciando API...
echo.
echo ========================================
echo   API rodando em http://localhost:5000
echo ========================================
echo.
echo Acesse:
echo   - Health:  http://localhost:5000/health
echo   - Admin:   file:///%CD%\admin-dashboard.html
echo   - Vendas:  file:///%CD%\vendas-dashboard.html
echo   - Diag:    file:///%CD%\diagnostico.html
echo.
echo Pressione CTRL+C para parar
echo.

python -m uvicorn src.main_minimal:app --host 0.0.0.0 --port 5000 --reload

pause
