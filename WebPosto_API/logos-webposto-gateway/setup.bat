@echo off
REM Logos WebPosto Gateway - Quick Start Script (Windows)

echo.
echo 🚀 Logos Gateway API - Setup Rápido (Windows)
echo =============================================
echo.

REM Verificar Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python não encontrado. Instale Python 3.12+.
    exit /b 1
)

echo ✅ Python encontrado: & python --version
echo.

REM Criar venv
if not exist "venv" (
    echo 📦 Criando ambiente virtual...
    python -m venv venv
)

REM Ativar venv
echo 🔌 Ativando ambiente virtual...
call venv\Scripts\activate.bat

REM Instalar dependências
echo 📚 Instalando dependências...
pip install -r requirements.txt

REM Copiar .env
if not exist ".env" (
    echo 📝 Copiando .env.example para .env...
    copy .env.example .env
)

echo.
echo ✅ Setup completo!
echo.
echo Próximos passos:
echo   1. docker compose up -d          # Inicia API + Valkey
echo   2. curl http://localhost:8050/ready   # Testa endpoint
echo   3. pytest tests/ -v              # Roda testes
echo.
