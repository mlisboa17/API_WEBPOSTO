.PHONY: help install dev test lint format clean run docker-up docker-down

help:
	@echo "🚀 Logos WebPosto Gateway - Makefile"
	@echo "===================================="
	@echo ""
	@echo "Targets disponíveis:"
	@echo "  make install       - Instala dependências"
	@echo "  make dev           - Instala dependências + dev tools"
	@echo "  make test          - Roda testes com pytest"
	@echo "  make test-cov      - Testes com cobertura"
	@echo "  make lint          - Roda linters (ruff, mypy)"
	@echo "  make format        - Formata código com black"
	@echo "  make clean         - Remove arquivos temporários"
	@echo "  make run           - Executa API localmente (uvicorn)"
	@echo "  make docker-build  - Constrói imagem Docker"
	@echo "  make docker-up     - Inicia docker-compose"
	@echo "  make docker-down   - Para docker-compose"
	@echo "  make docker-logs   - Mostra logs do Docker"
	@echo ""

install:
	pip install -r requirements.txt

dev: install
	pip install -e ".[dev]"

test:
	pytest tests/ -v

test-cov:
	pytest tests/ -v --cov=src --cov-report=html

lint:
	ruff check src/ tests/
	mypy src/ --strict

format:
	black src/ tests/

clean:
	find . -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -r {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -r {} + 2>/dev/null || true
	rm -rf htmlcov/
	rm -rf .coverage

run:
	python -m uvicorn src.main:app --host 0.0.0.0 --port 8050 --reload

docker-build:
	docker compose build --no-cache

docker-up:
	docker compose up -d
	@sleep 2
	@echo ""
	@echo "✅ Serviços iniciados!"
	@echo "   Gateway: http://localhost:8050"
	@echo "   Valkey:  localhost:6379"

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f logos-gateway

docker-logs-valkey:
	docker compose logs -f valkey

ready-check:
	@curl -X GET http://localhost:8050/ready || echo "Gateway não está respondendo"

health-check:
	@curl -X GET http://localhost:8050/health || echo "Health check falhou"

all-checks: ready-check health-check
	@echo "✅ Todos os checks passaram!"

