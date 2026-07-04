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

## Architecture: Split Light/Heavy Services, Four Lambda Entrypoints

FastAPI is the only app (the Flask legacy app described in earlier
versions of this file — `wsgi.py`, `app/blueprints/` — has been removed).

Each service is split into a light lookup module (pandas/CSV only) and a
heavy calc module (the scientific stack):

- `app/services/{htl,combustion,fermentation}/lookup.py` — county lookups
  and unit conversion.
- `app/services/{htl,combustion,fermentation}/calc.py` — the actual
  process simulation. Model/biorefinery objects are cached per warm
  container behind a lock.
- `app/services/combustion/_chemicals.py` — combustion's chemical
  definitions, built directly with thermosteam instead of importing
  exposan/biorefineries (see `guides/lambda-restructure-design.md`).

Routers follow the same split (`app/routers/htl_lookup.py` +
`app/routers/htl_calc.py`, etc.). `app/main.py` registers all six routers
for local development (`uv run uvicorn app.main:app`). Production runs as
four separate Lambda functions instead, each with its own minimal FastAPI
app in `app/entrypoints/` and its own Dockerfile
(`Dockerfile.lambda.{light,htl,combustion,fermentation}`) — see
`guides/lambda-restructure-design.md` for the full architecture and
`guides/lambda-restructure-plan.md` for how it was built.

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
