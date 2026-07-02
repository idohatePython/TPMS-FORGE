#!/usr/bin/env bash
set -euo pipefail

export UV_CACHE_DIR="${UV_CACHE_DIR:-.uv-cache}"

if command -v uv >/dev/null 2>&1; then
  UV_BIN="uv"
elif [ -x "$HOME/.local/bin/uv" ]; then
  UV_BIN="$HOME/.local/bin/uv"
else
  echo "uv is required. Install it or add ~/.local/bin to PATH." >&2
  exit 1
fi

case "${1:-help}" in
  install)
    "$UV_BIN" sync --dev
    corepack enable || true
    pnpm --dir frontend install
    ;;
  backend)
    "$UV_BIN" run uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
    ;;
  worker)
    "$UV_BIN" run celery -A worker.celery_app.celery_app worker --loglevel=INFO
    ;;
  frontend)
    pnpm --dir frontend dev
    ;;
  compose-up)
    docker compose up --build
    ;;
  compose-down)
    docker compose down
    ;;
  test)
    "$UV_BIN" run pytest
    ;;
  lint)
    "$UV_BIN" run ruff check .
    pnpm --dir frontend lint
    ;;
  format)
    "$UV_BIN" run ruff format .
    "$UV_BIN" run ruff check . --fix
    pnpm --dir frontend format
    ;;
  typecheck)
    "$UV_BIN" run mypy --explicit-package-bases backend algorithms worker
    pnpm --dir frontend typecheck
    ;;
  build-frontend)
    pnpm --dir frontend build
    ;;
  help|*)
    cat <<'EOF'
TPMS-FORGE development commands

  bash scripts/dev.sh install         Install dependencies
  bash scripts/dev.sh backend         Start FastAPI dev server
  bash scripts/dev.sh worker          Start Celery worker
  bash scripts/dev.sh frontend        Start Vite dev server
  bash scripts/dev.sh compose-up      Start Docker Compose services
  bash scripts/dev.sh compose-down    Stop Docker Compose services
  bash scripts/dev.sh test            Run Python tests
  bash scripts/dev.sh lint            Run Python/frontend lint
  bash scripts/dev.sh format          Format Python/frontend code
  bash scripts/dev.sh typecheck       Run Python/frontend type checks
  bash scripts/dev.sh build-frontend  Build frontend
EOF
    ;;
esac
