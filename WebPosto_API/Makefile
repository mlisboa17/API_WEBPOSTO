.PHONY: help install test lint format run docker-up docker-down clean migrations migrate

help:
	@echo "webposto-service - Available commands:"
	@echo "  install          - Install dependencies"
	@echo "  test             - Run tests with coverage"
	@echo "  test-unit        - Run only unit tests"
	@echo "  test-integration - Run only integration tests"
	@echo "  lint             - Run linters (black, isort, flake8, mypy)"
	@echo "  format           - Format code (black, isort)"
	@echo "  run              - Run application locally"
	@echo "  docker-up        - Start Docker containers"
	@echo "  docker-down      - Stop Docker containers"
	@echo "  migrations       - Create new migration"
	@echo "  migrate          - Run migrations"
	@echo "  clean            - Remove cache and build files"

install:
	poetry install

test:
	pytest --cov=src --cov-report=html

test-unit:
	pytest tests/unit --cov=src

test-integration:
	pytest tests/integration

lint:
	black --check src tests
	isort --check-only src tests
	flake8 src tests
	mypy src

format:
	black src tests
	isort src tests

run:
	poetry run python -m src.main

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f app

migrations:
	alembic revision --autogenerate

migrate:
	alembic upgrade head

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .mypy_cache -exec rm -rf {} +
	find . -type d -name htmlcov -exec rm -rf {} +
	rm -rf .coverage
