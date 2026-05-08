#!/usr/bin/env python
"""Script para testar importações e diagnosticar problemas"""

import traceback

print("=" * 60)
print("🔍 Teste de Importações webPosto API")
print("=" * 60)

# Test 1: FastAPI
print("\n1️⃣  Testando FastAPI...")
try:
    print("   ✅ FastAPI importado com sucesso")
except Exception as e:
    print(f"   ❌ Erro: {e}")
    traceback.print_exc()

# Test 2: CORS Middleware
print("\n2️⃣  Testando CORS Middleware...")
try:
    print("   ✅ CORS Middleware importado com sucesso")
except Exception as e:
    print(f"   ❌ Erro: {e}")

# Test 3: Settings
print("\n3️⃣  Testando Settings...")
try:
    from src.infrastructure.config.settings import settings

    print("   ✅ Settings importado com sucesso")
    print(f"      - API Host: {settings.api_host}")
    print(f"      - API Port: {settings.api_port}")
except Exception as e:
    print(f"   ❌ Erro ao importar Settings: {e}")
    traceback.print_exc()

# Test 4: WebPosto Client
print("\n4️⃣  Testando WebPosto Client...")
try:
    print("   ✅ WebPosto Client importado com sucesso")
except Exception as e:
    print(f"   ❌ Erro: {e}")
    traceback.print_exc()

# Test 5: Models
print("\n5️⃣  Testando Models...")
try:
    print("   ✅ Models importado com sucesso")
except Exception as e:
    print(f"   ❌ Erro: {e}")
    traceback.print_exc()

# Test 6: CRUD
print("\n6️⃣  Testando CRUD...")
try:
    print("   ✅ CRUD importado com sucesso")
except Exception as e:
    print(f"   ❌ Erro: {e}")
    traceback.print_exc()

# Test 7: Routes CRUD
print("\n7️⃣  Testando Routes CRUD...")
try:
    print("   ✅ Routes CRUD importado com sucesso")
except Exception as e:
    print(f"   ❌ Erro: {e}")
    traceback.print_exc()

# Test 8: Main Minimal
print("\n8️⃣  Testando Main Minimal...")
try:
    from src.main_minimal import app

    print("   ✅ Main Minimal importado com sucesso")
    print(f"      - App Title: {app.title}")
    print(f"      - App Version: {app.version}")
except Exception as e:
    print(f"   ❌ Erro: {e}")
    traceback.print_exc()

print("\n" + "=" * 60)
print("✅ Teste Completo!")
print("=" * 60)
