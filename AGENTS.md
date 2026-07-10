# Agent Context

This file mirrors `CLAUDE.md` (kept in sync — apply any edit to both) plus records durable project state that doesn't belong in the architecture docstring.

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

## Git workflow

Never run `git commit` or `git push` without the user's explicit approval. Present a diff/file-list summary and stop; the user commits themselves. "Do it"/"go ahead" approves edits, not commits — commit approval requires the literal word "commit". Don't ask "how do you want the commits structured" at a finish line either — that question presumes you'll be the one running `git commit`; just describe what's ready and let the user invoke it.

## Current state (Lambda migration — done, live in production)

Completed 2026-07-05. This repo runs as 4 separate Lambda functions (`nj-bioenergy-light`, `-htl`, `-combustion`, `-fermentation`) behind CloudFront with path-pattern routing, replacing an earlier ECS Express Mode backend entirely. Full deployment inventory is in the `deployments` repo at `Coding/deployments/qsdsan.md` (account/config facts only — no bug narratives there; see the QSDsan-platform root `AGENTS.md`).

**Real bugs found only via live AWS testing (not caught by code review beforehand) — watch for regressions of these:**
- `app/routers/__init__.py` must NOT eagerly import all routers — `from app.routers import X` always runs the package `__init__.py` first, so an eager `from . import htl_calc, htl_lookup, ...` silently pulls every heavy service module into every entrypoint, crashing `light` (no exposan there) and defeating per-function dependency isolation.
- Each Lambda function needs its own real readiness endpoint for smoke tests — `light` is the only one that registers `/health`; the others correctly 404 on it by design.
- CloudFront's default 30s origin response timeout is shorter than htl/fermentation's real cold-start (~37-55s); it's raised to 120s on all four origins. Don't let this regress if origins are ever recreated.
- Do not enable CORS at both the Lambda Function URL layer and the app's own `CORSMiddleware` for the same origin — both add an `Access-Control-Allow-Origin` header, which get folded into one invalid comma-joined value that all browsers reject. CORS is disabled at the Function URL level; `CORSMiddleware` is the sole source.
- Any `getInfo`/`getManualInfo`-style fetch helper (frontend side, `nj-bioenergy-app`) must re-throw on failure, not swallow and return `null` — a swallowed failure surfaces as a confusing "data is null" crash far from the real error.

**Per-warm-container caching bug (root-caused and fixed 2026-07-04, distinct mechanisms per service):**
- **Fermentation** (`app/services/fermentation/calc.py`): biosteam's default recycle tolerance is a per-iteration relative-delta check, not true convergence, so a warm-started resimulation "converges" after 1 iteration while a cold build takes 15-30 — producing monotonic drift across repeated calls on the same warm container. Fixed via `_br.sys.set_tolerance(mol=1e-6, rmol=1e-9, subsystems=True)` once at cache-build time, forcing every call (warm or cold) to the same tight fixed point.
- **HTL** (`app/services/htl/calc.py`): exposan's HTL system has `ReversedSplitter` units that read stale demand from the *previous* simulate() call (one pass behind) — this is a genuine upstream `exposan/htl/systems.py` bug, not something this app introduced. App-level stopgap: call `model.metrics_at_baseline()` twice per request (priming pass + real pass). The real fix (declare the splitters' outs as `sys.recycle` + tight tolerance) was made upstream on EXPOsan branch `fix-htl-recycle` — check whether that PR has merged and a release pinned here before assuming the double-call stopgap is still needed; once it lands, `htl_calc`'s double `metrics_at_baseline()` call becomes redundant overhead (perf cleanup only, not a correctness fix).
- If the exposan/biosteam pin here is ever bumped, re-verify both fixes still reproduce the same tolerance/ordering numbers — don't assume upstream silently fixed either.

**Process note:** Lambda memory is pinned at 3008 MB (not lowered to 1024 MB) — lower memory is cheaper in raw GB-seconds but ~2x's cold-start latency, and at this app's real (low) traffic level the free tier absorbs the cost difference, so latency was the only thing that mattered. Don't assume lower memory = cheaper without measuring.
