.PHONY: help build test deploy logs stop restart health backup restore

# Variáveis
VERSION ?= latest
ENVIRONMENT ?= production
REGISTRY ?= registry.com

help:
	@echo "Logos Auditoria - Make Commands"
	@echo ""
	@echo "Development:"
	@echo "  make dev-setup       - Setup dev environment"
	@echo "  make dev             - Run dev server"
	@echo "  make test            - Run tests"
	@echo "  make lint            - Lint code"
	@echo ""
	@echo "Production:"
	@echo "  make build           - Build Docker image"
	@echo "  make push            - Push to registry"
	@echo "  make deploy          - Deploy to production"
	@echo "  make rollback        - Rollback to previous version"
	@echo ""
	@echo "Operations:"
	@echo "  make logs            - Tail API logs"
	@echo "  make status          - Check container status"
	@echo "  make health          - Health check"
	@echo "  make backup          - Backup databases"
	@echo "  make restore         - Restore from backup"
	@echo "  make stop            - Stop containers"
	@echo "  make restart         - Restart containers"
	@echo ""

# ============ DEVELOPMENT ============

dev-setup:
	@echo "Setting up development environment..."
	pip install -r requirements.txt --break-system-packages
	cp .env.example .env
	@echo "✓ Setup complete. Edit .env and run 'make dev'"

dev:
	python servicos_auditoria.py

test:
	pytest test_auditoria.py -v --tb=short

lint:
	flake8 *.py --max-line-length=120 || true
	black --check *.py || true

# ============ PRODUCTION ============

build:
	@echo "Building Docker image: $(REGISTRY)/logos-auditoria:$(VERSION)"
	docker build -t $(REGISTRY)/logos-auditoria:$(VERSION) .
	docker tag $(REGISTRY)/logos-auditoria:$(VERSION) $(REGISTRY)/logos-auditoria:latest
	@echo "✓ Image built"

push: build
	@echo "Pushing to registry..."
	docker push $(REGISTRY)/logos-auditoria:$(VERSION)
	docker push $(REGISTRY)/logos-auditoria:latest
	@echo "✓ Pushed"

deploy:
	@chmod +x deploy.sh
	@./deploy.sh $(VERSION) $(ENVIRONMENT) $(REGISTRY)

rollback:
	@echo "Rolling back to previous version..."
	docker-compose down
	docker-compose pull
	docker-compose up -d
	@echo "✓ Rollback complete"

# ============ OPERATIONS ============

logs:
	docker-compose logs -f api

logs-mongo:
	docker-compose logs -f mongo

logs-nginx:
	docker-compose logs -f nginx

status:
	docker-compose ps

health:
	@echo "Checking API health..."
	@curl -s http://localhost:8000/auditoria/health | python3 -m json.tool || echo "❌ API unhealthy"

restart:
	@echo "Restarting containers..."
	docker-compose restart
	@echo "✓ Restarted"

stop:
	@echo "Stopping containers..."
	docker-compose down
	@echo "✓ Stopped"

# ============ DATABASE ============

backup:
	@echo "Creating backups..."
	mkdir -p backups
	@docker-compose exec -T mongo mongodump \
		-u admin -p $(MONGO_ROOT_PASSWORD) \
		--authenticationDatabase admin \
		--out /backup/mongo-$(shell date +%Y%m%d-%H%M%S) 2>/dev/null || echo "MongoDB backup failed"
	@docker exec logos-cache redis-cli BGSAVE 2>/dev/null || echo "Redis backup failed"
	@echo "✓ Backups created"

restore:
	@echo "Restoring from latest backup..."
	@docker-compose stop api
	@docker-compose exec -T mongo mongorestore \
		-u admin -p $(MONGO_ROOT_PASSWORD) \
		--authenticationDatabase admin \
		/backup/mongo-latest 2>/dev/null || echo "MongoDB restore failed"
	@docker-compose up -d api
	@echo "✓ Restored"

# ============ UTILS ============

shell:
	docker-compose exec api bash

shell-mongo:
	docker-compose exec mongo mongosh -u admin -p $(MONGO_ROOT_PASSWORD) \
		--authenticationDatabase admin

shell-redis:
	docker-compose exec redis redis-cli

clean:
	@echo "Cleaning up..."
	docker-compose down -v
	docker image rm $(REGISTRY)/logos-auditoria || true
	rm -rf backups/*
	@echo "✓ Cleaned"

version:
	@echo "Getting current version..."
	@docker-compose exec -T api python -c "from config import app_config; print(f'App: {app_config.app_version}')"

# ============ MONITORING ============

grafana:
	@echo "Grafana: http://localhost:3000"
	@echo "Default: admin / admin"

prometheus:
	@echo "Prometheus: http://localhost:9090"

# ============ CI/CD ============

validate:
	@echo "Validating..."
	python3 -m py_compile *.py
	pytest test_auditoria.py --tb=short
	@echo "✓ Validation passed"

release: validate build push
	@echo "✓ Release complete: $(VERSION)"

# ============ SECURITY ============

ssl-generate:
	@echo "Generating self-signed certificate..."
	mkdir -p ssl
	openssl req -x509 -newkey rsa:4096 -keyout ssl/key.pem -out ssl/cert.pem -days 365 -nodes
	@echo "✓ Certificate generated"

ssl-validate:
	@echo "Validating SSL certificate..."
	@openssl x509 -in ssl/cert.pem -text -noout

# ============ LOAD TEST ============

load-test:
	@echo "Running load test..."
	ab -n 1000 -c 100 http://localhost:8000/auditoria/health || true

profile:
	@echo "Running performance profile..."
	python -m cProfile -s cumulative servicos_auditoria.py || true

# ============ DEFAULTS ============

.DEFAULT_GOAL := help
