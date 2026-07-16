# TPMS-FORGE

TPMS-FORGE is the final engineering project for a web-based TPMS structure generation, slicing, toolpath planning, and Marlin G-code export platform.

中文正式名：

```text
TPMS-FORGE：面向增材制造的 TPMS 三维结构生成与打印路径规划平台
```

## Scope

V1.0 focuses on the end-to-end workflow:

```text
Upload STL/OBJ
→ Generate TPMS structure
→ Export STL
→ Slice and plan path
→ Export Marlin G-code
```

Full design documents are maintained outside this project directory:

```text
../my_docs/
```

## Tech Stack

- Frontend: Vue 3, TypeScript, Vite, Pinia, Naive UI, Three.js
- Backend: FastAPI, Python 3.12, Pydantic v2, SQLAlchemy 2.x, PostgreSQL 16
- Worker: Celery + Redis 7
- Algorithms: NumPy, SciPy, scikit-image, trimesh, shapely, networkx, meshio
- Storage: local filesystem in V1.0, abstracted through StorageService for future MinIO support. Runtime STL/OBJ/G-code data belongs in `../TPMS-FORGE-data` (configured with `STORAGE_ROOT`), outside this Git repository.
- Tooling: uv, Ruff, mypy, pytest, pre-commit, structlog

## Project Layout

```text
TPMS-FORGE/
├── frontend/          # Vue 3 frontend
├── backend/           # FastAPI backend API
├── algorithms/        # Independent algorithm package
├── worker/            # Celery worker entrypoints and task bindings
├── storage/           # Local runtime file storage, ignored by Git
├── deploy/            # Deployment assets
├── scripts/           # Development and maintenance scripts
├── tests/             # Cross-service integration tests
├── docker-compose.yml
├── pyproject.toml
├── .env.example
├── .gitignore
└── README.md
```

## Architecture Notes

- The backend submits tasks and manages metadata; it must not run long TPMS or slicing computations inside HTTP requests.
- The worker calls `algorithms.pipeline`, not scattered low-level algorithm functions.
- The database stores metadata only. STL, OBJ, G-code, preview data, and logs live in storage.
- Business code should use a storage abstraction instead of constructing storage paths directly.
- This is one repository with multiple services, not a microservice system.

## Local Development

Required tools:

- Python 3.12
- Node.js 20 LTS or newer
- Docker + Docker Compose
- uv
- pnpm

Install dependencies:

```bash
bash scripts/dev.sh install
```

Check local tools:

```bash
bash scripts/check-env.sh
```

Start infrastructure only:

```bash
docker compose up postgres redis
```

Start backend:

```bash
bash scripts/dev.sh backend
```

Start worker:

```bash
bash scripts/dev.sh worker
```

Start frontend:

```bash
bash scripts/dev.sh frontend
```

Or start everything with Docker Compose:

```bash
cp .env.example .env
bash scripts/dev.sh compose-up
```

Useful URLs:

- Frontend: http://localhost:5173
- Backend health: http://localhost:8000/api/v1/health
- Backend OpenAPI: http://localhost:8000/docs
