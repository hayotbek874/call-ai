# Makefile for STRATIX AI Chat Bot
# Shortcuts for common development and deployment tasks

.PHONY: help install run dev test lint format migrate worker beat shell clean docker-up docker-down

# Default target
help:
	@echo "STRATIX AI Chat Bot - Available commands:"
	@echo ""
	@echo "  Development:"
	@echo "    make install      - Install dependencies using Poetry"
	@echo "    make run          - Run the FastAPI server"
	@echo "    make dev          - Run with auto-reload for development"
	@echo "    make shell        - Open Python shell with app context"
	@echo ""
	@echo "  Testing & Quality:"
	@echo "    make test         - Run all tests"
	@echo "    make test-cov     - Run tests with coverage report"
	@echo "    make lint         - Run linters (ruff, mypy)"
	@echo "    make format       - Format code with ruff and black"
	@echo ""
	@echo "  Database:"
	@echo "    make migrate      - Run database migrations"
	@echo "    make migrate-new  - Create new migration (usage: make migrate-new MSG='description')"
	@echo "    make seed         - Seed database with initial data"
	@echo ""
	@echo "  Background Tasks:"
	@echo "    make worker       - Start Celery worker"
	@echo "    make beat         - Start Celery beat scheduler"
	@echo "    make flower       - Start Flower monitoring"
	@echo ""
	@echo "  Docker:"
	@echo "    make docker-up    - Start all services with Docker Compose"
	@echo "    make docker-down  - Stop all Docker services"
	@echo "    make docker-build - Build Docker images"
	@echo "    make docker-logs  - Show Docker logs"
	@echo ""
	@echo "  Cleanup:"
	@echo "    make clean        - Remove cache and build artifacts"

# ==================== Development ====================

install:
	@echo "Installing dependencies..."
	poetry install
	@echo "Installing pre-commit hooks..."
	poetry run pre-commit install || true

run:
	@echo "Starting FastAPI server..."
	poetry run uvicorn src.main:app --host 0.0.0.0 --port 8000

dev:
	@echo "Starting FastAPI server in development mode..."
	poetry run uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

shell:
	@echo "Opening Python shell..."
	poetry run python -i -c "from src.core.config import settings; from src.db.session import *; print('Settings and DB session loaded')"

# ==================== Testing & Quality ====================

test:
	@echo "Running tests..."
	poetry run pytest tests/ -v

test-cov:
	@echo "Running tests with coverage..."
	poetry run pytest tests/ -v --cov=src --cov-report=term-missing --cov-report=html

test-unit:
	@echo "Running unit tests..."
	poetry run pytest tests/unit/ -v

test-integration:
	@echo "Running integration tests..."
	poetry run pytest tests/integration/ -v

lint:
	@echo "Running linters..."
	poetry run ruff check src/ tests/
	poetry run mypy src/ --ignore-missing-imports

format:
	@echo "Formatting code..."
	poetry run ruff check src/ tests/ --fix
	poetry run ruff format src/ tests/

# ==================== Database ====================

migrate:
	@echo "Running database migrations..."
	poetry run alembic upgrade head

migrate-new:
	@echo "Creating new migration..."
	@if [ -z "$(MSG)" ]; then \
		echo "Usage: make migrate-new MSG='migration description'"; \
		exit 1; \
	fi
	poetry run alembic revision --autogenerate -m "$(MSG)"

migrate-down:
	@echo "Rolling back last migration..."
	poetry run alembic downgrade -1

migrate-history:
	@echo "Showing migration history..."
	poetry run alembic history

seed:
	@echo "Seeding database..."
	poetry run python scripts/seed_db.py

# ==================== Background Tasks ====================

worker:
	@echo "Starting Celery worker..."
	poetry run celery -A src.workers.celery_app worker --loglevel=info

beat:
	@echo "Starting Celery beat..."
	poetry run celery -A src.workers.celery_app beat --loglevel=info

flower:
	@echo "Starting Flower monitoring..."
	poetry run celery -A src.workers.celery_app flower --port=5555

# ==================== Docker ====================

docker-up:
	@echo "Starting Docker services..."
	docker-compose up -d

docker-down:
	@echo "Stopping Docker services..."
	docker-compose down

docker-build:
	@echo "Building Docker images..."
	docker-compose build

docker-logs:
	@echo "Showing Docker logs..."
	docker-compose logs -f

docker-shell:
	@echo "Opening shell in app container..."
	docker-compose exec app /bin/bash

docker-clean:
	@echo "Cleaning Docker resources..."
	docker-compose down -v --rmi local

# ==================== Production ====================

prod-up:
	@echo "Starting production services..."
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

prod-down:
	@echo "Stopping production services..."
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml down

# ==================== Utilities ====================

sync-products:
	@echo "Syncing products from API..."
	poetry run python scripts/sync_products.py

clean:
	@echo "Cleaning up..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .coverage htmlcov/ 2>/dev/null || true
	@echo "Cleanup complete!"

# ==================== Git Hooks ====================

pre-commit:
	@echo "Running pre-commit checks..."
	poetry run pre-commit run --all-files
