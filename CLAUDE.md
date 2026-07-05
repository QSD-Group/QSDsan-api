# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Backend API for Waste-to-Energy processing calculations focused on New Jersey county data. Supports HTL (Hydrothermal Liquefaction), Fermentation, and Combustion processes. FastAPI, run as four separate AWS Lambda functions in production behind CloudFront.

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

Each service is split into a light lookup module (pandas/CSV only) and a
heavy calc module (the scientific stack):

- `app/services/{htl,combustion,fermentation}/lookup.py` — county lookups
  and unit conversion.
- `app/services/{htl,combustion,fermentation}/calc.py` — the actual
  process simulation. Model/biorefinery objects are cached per warm
  container behind a lock (first request in a warm container builds the
  model; later requests in the same container reuse it).
- `app/services/combustion/_chemicals.py` — combustion's chemical
  definitions, built directly with plain `thermosteam.Chemical` objects
  instead of importing `exposan`/`biorefineries.cane` (those only ever
  got used to extract a handful of physical properties, so rebuilding
  them directly drops two heavy transitive dependencies from the
  combustion Lambda).

Routers follow the same split (`app/routers/htl_lookup.py` +
`app/routers/htl_calc.py`, etc.). `app/main.py` registers all six routers
for local development (`uv run uvicorn app.main:app`). Production runs as
four separate Lambda functions instead, each with its own minimal FastAPI
app in `app/entrypoints/` and its own Dockerfile
(`Dockerfile.lambda.{light,htl,combustion,fermentation}`):

| Function | Endpoints | Dependencies |
|---|---|---|
| `light` | `/health`, `/ready`, `/metrics`, `/performance`, `/htl/county`, `/combustion/county`, `/fermentation/county` | `fastapi`, `pandas`, `psutil` only |
| `htl` | `/htl/calc` | + `exposan`, `chaospy` |
| `combustion` | `/combustion/calc` | + `biosteam`, `thermosteam` only (no `exposan`/`biorefineries`) |
| `fermentation` | `/fermentation/calc` | + `biosteam`, `biorefineries.cellulosic`, `biorefineries.cornstover` |

CloudFront routes by path pattern to each function's own Function URL. Each
`*-calc` function gets its own memory/timeout profile, tuned independently
of `light`'s.

## API Structure

All endpoints under `/api/v1/`. Each processing type has two endpoint patterns:
- `GET /<type>/county?county_name=<name>` — Looks up NJ county data from CSV, then runs calculation
- `GET /<type>/calc?<params>` — Direct calculation from provided mass/input values

FastAPI docs available at `/docs` (Swagger) and `/redoc` when the app is running.

## Key Scientific Dependencies

Split across the base install and an optional `heavy` group (see
`pyproject.toml`) so the `light` Lambda function never pulls these in:

- `exposan==1.4.1`, `biosteam==2.46.1`, `biorefineries==2.31.0`,
  `thermosteam==0.45.0`, `chaospy==4.3.17` — all pinned to exact PyPI
  releases (no git-commit pins).
- `qsdsan` and the rest of the scientific stack (`numba`, `scipy`,
  `chemicals`, etc.) are transitive dependencies resolved and locked
  automatically by `uv lock` — not listed directly in `pyproject.toml`.
