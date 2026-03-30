# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Backend API for Waste-to-Energy processing calculations focused on New Jersey county data. Supports HTL (Hydrothermal Liquefaction), Fermentation, Combustion, and Anaerobic Digestion processes. Currently mid-migration from Flask to FastAPI.

## Package Manager: UV

This project uses **UV** — do not use `pip` or `python -m venv` directly.

```bash
uv sync                          # Install all dependencies
uv add <package>                 # Add a dependency
uv add --dev <package>           # Add a dev dependency
uv run <command>                 # Run any command in the managed environment
```

## Running the Application

**FastAPI (active development target):**
```bash
uv run uvicorn app.main:app --reload --port 5000
```

**Flask (legacy, still functional):**
```bash
uv run python wsgi.py
```

**Docker:**
```bash
docker build -t waste-energy-api .
docker run -p 5000:5000 waste-energy-api
```

## Development Commands

```bash
# Tests
uv run pytest                        # All tests
uv run pytest tests/test_htl.py      # Single test file
uv run pytest --cov=app              # With coverage

# Code quality
uv run ruff check .                  # Lint
uv run black .                       # Format
uv run mypy app/                     # Type check
```

## Architecture: Dual-App Migration State

The codebase has **two parallel app structures** during the Flask → FastAPI migration:

### FastAPI (new — `app/main.py`)
Entry point for production. Uses:
- `app/routers/` — FastAPI `APIRouter` handlers (htl, combustion, fermentation, health, v2_example)
- `app/models/` — Pydantic request/response models for each processing type
- `app/middleware/` — Error handling, performance monitoring, rate limiting, security headers

### Flask (legacy — `wsgi.py` → `app/__init__.py`)
Still functional fallback. Uses:
- `app/blueprints/` — Flask Blueprint route handlers
- `app/blueprints/trial.py` — Temporary test blueprint (marked for removal)

### Shared Service Layer (`app/services/`)
Both Flask blueprints and FastAPI routers call the **same service functions**. Services contain all business logic and scientific calculations:
- `htl_service.py` — Working. Uses `exposan.htl.create_model` for HTL calculations, `chaospy` for distributions.
- `combustion_service.py` — Needs fixing (broken endpoints).
- `fermentation_service.py` — Needs fixing (broken endpoints).

### Data Layer (`app/data/`)
CSV files per processing type (e.g., `htl/htl_data.csv`, `fermentation/fermentation_data.csv`). Services load these at module import time using `os.path` relative to the service file's `__file__`.

## API Structure

All endpoints under `/api/v1/`. Each processing type has two endpoint patterns:
- `GET /<type>/county?county_name=<name>` — Looks up NJ county data from CSV, then runs calculation
- `GET /<type>/calc?<params>` — Direct calculation from provided mass/input values

FastAPI docs available at `/docs` (Swagger) and `/redoc` when the app is running.

## Key Scientific Dependencies

- `exposan` — Core HTL modeling (pinned to specific git commit in pyproject.toml)
- `biosteam`, `biorefineries`, `thermosteam` — Biorefinery process simulation
- `qsdsan` — Quantitative sustainable design for sanitation
- `chaospy` — Statistical distributions for uncertainty analysis
- `scipy`, `numpy`, `pandas` — Numerical computation and data handling

## Migration Status

See `guides/migration.md` for the full phased migration plan. Current state:
- Phase 1 (HTL + FastAPI foundation): Structurally complete but tracking checklist is outdated
- Phase 2 (Fix combustion & fermentation): Pending
- Phase 3 (Polish & optimization): Pending

The FastAPI middleware stack (`app/middleware/`) and health/monitoring endpoints (`/health`, `/ready`, `/metrics`) were added ahead of the migration plan schedule.
