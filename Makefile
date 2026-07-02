UV := UV_CACHE_DIR=.uv-cache uv

.PHONY: help install dev-backend dev-worker dev-frontend compose-up compose-down test lint format typecheck

help:
	@echo "TPMS-FORGE development commands"
	@echo "  make install       Install Python and frontend dependencies"
	@echo "  make dev-backend   Start FastAPI development server"
	@echo "  make dev-worker    Start Celery worker"
	@echo "  make dev-frontend  Start Vite frontend server"
	@echo "  make compose-up    Start Docker Compose services"
	@echo "  make compose-down  Stop Docker Compose services"
	@echo "  make test          Run backend/integration tests"
	@echo "  make lint          Run Ruff and frontend lint"
	@echo "  make format        Format Python and frontend code"
	@echo "  make typecheck     Run Python and frontend type checks"

install:
	$(UV) sync --dev
	corepack enable
	pnpm --dir frontend install

dev-backend:
	$(UV) run uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000

dev-worker:
	$(UV) run celery -A worker.celery_app.celery_app worker --loglevel=INFO

dev-frontend:
	pnpm --dir frontend dev

compose-up:
	docker compose up --build

compose-down:
	docker compose down

test:
	$(UV) run pytest

lint:
	$(UV) run ruff check .
	pnpm --dir frontend lint

format:
	$(UV) run ruff format .
	$(UV) run ruff check . --fix
	pnpm --dir frontend format

typecheck:
	$(UV) run mypy --explicit-package-bases backend algorithms worker
	pnpm --dir frontend typecheck
