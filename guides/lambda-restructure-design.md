# Lambda Restructure Design

**Status:** approved, ready for implementation planning.
**Supersedes:** `guides/lambda-migration-plan.md` (kept for historical reference — Tasks 1-3 of that
plan already landed on `main`; this doc replaces its remaining tasks with a different architecture).

## Context

The first Lambda migration attempt (see `[[project_lambda_migration]]` memory) got a single monolithic
Lambda function built and smoke-tested, but stalled before the CloudFront cutover and was abandoned —
the ECS/ALB backend was fully decommissioned instead. This doc restarts the migration with a different,
more deliberate architecture, informed by two findings made during design:

1. **The exposan version comment is stale.** `htl_service.py`/`combustion_service.py` still say
   `# exposan version @ git+...93d4173...` in a comment, but `pyproject.toml`/`uv.lock` actually pin
   `exposan==1.4.1` from PyPI (confirmed installed in `.venv`). The `simulate=False` fix
   (EXPOsan commit `5087fe7`, 2026-07-02) is not in any tagged EXPOsan release — it only exists on
   `main`. **Decision: defer all dependency version changes and the `simulate=False` adoption to a
   separate follow-up.** This restructuring pass touches only import structure, module boundaries, and
   Lambda packaging — not dependency versions.

2. **`app/main.py` imports every router (and therefore every service's heavy deps) unconditionally at
   startup**, and each router imports its service module eagerly too. This is the real driver of
   cold-start cost, not just the service files' own top-level imports.

## Scope

**In scope:** import/module restructuring, a 4-Lambda-function architecture, per-container model
caching, the code-level Docker/CI changes, and the full AWS cutover (Lambda functions, Function URLs,
CloudFront path routing) through to decommissioning what remains of the old attempt.

**Out of scope (deferred to a later pass):** bumping thermosteam/biosteam/qsdsan/exposan to newer
releases; adopting the `simulate=False` fix; the small upstream EXPOsan PR wrapping
`exposan.utils._init_modules`'s bare `os.mkdir()` in a try/except (independent, low-risk, proposed
separately against EXPOsan whenever convenient — not gating anything here, since `Dockerfile.lambda`
already works around the crash by pre-creating the directory).

## Architecture: 4 Lambda functions

| Function | Endpoints | Dependencies |
|---|---|---|
| `light-api` | `/health`, `/ready`, `/metrics`, `/performance`, `/htl/county`, `/combustion/county`, `/fermentation/county` | `fastapi`, `pandas`, `psutil` — no `biosteam`/`exposan`/`biorefineries` |
| `htl-calc` | `/htl/calc` | `exposan.htl.create_model`, `chaospy` |
| `combustion-calc` | `/combustion/calc` | `biosteam`, `thermosteam` only (see below — no `exposan`, no `biorefineries`) |
| `fermentation-calc` | `/fermentation/calc` | `biosteam`, `biorefineries.cellulosic`, `biorefineries.cornstover` |

`light-api` gets a small image and a low memory/timeout profile; each `*-calc` function gets its own
memory/timeout tuned independently. CloudFront routes by path pattern to 4 origins (4 Function URLs),
replacing the single-origin swap the old plan's Task 7 described.

Combustion and fermentation do **not** actually have non-overlapping dependency slices today —
`biorefineries.cane` (which `combustion_service.py` currently imports for
`create_sugarcane_chemicals`) transitively imports `biorefineries.cellulosic` via
`biorefineries/cane/chemicals.py`'s module-level `from biorefineries import cellulosic`, which is the
same heavy biorefinery-building package `fermentation_service.py` needs directly. Removing
`biorefineries.cane` from combustion (below) restores the non-overlapping-slices premise the 4-function
split depends on.

## Module layout

Each service becomes a package split into a light lookup module and a heavy calc module:

```
app/services/htl/{lookup.py, calc.py}
app/services/combustion/{lookup.py, calc.py, _chemicals.py}
app/services/fermentation/{lookup.py, calc.py}
```

Routers get the same split (`app/routers/htl_calc.py` + `app/routers/htl_lookup.py`, etc.), composed by
four slim entrypoint modules:

```
app/entrypoints/light_app.py         -> health router + 3 lookup routers
app/entrypoints/htl_app.py           -> htl_calc router only
app/entrypoints/combustion_app.py    -> combustion_calc router only
app/entrypoints/fermentation_app.py  -> fermentation_calc router only
```

`app/main.py` is left importing everything, as today — it's the local-dev convenience entrypoint
(`uv run uvicorn app.main:app`) and is never what Lambda runs, so there's no reason to make it lazy.
The Flask legacy app (`wsgi.py`, `app/blueprints/`) referenced in `CLAUDE.md` no longer exists in this
repo (confirmed) — `CLAUDE.md`'s "dual-app migration" section is stale and should be updated as part of
this work.

**No lazy-imports-inside-handlers needed.** With four separately-deployed apps, each entrypoint's
module-import closure naturally scopes to only what that function needs — the original goal of
deferring imports into handler bodies is achieved more simply by the module/entrypoint boundaries
themselves.

`app/routers/health.py`'s `/ready` endpoint currently imports `biosteam` and all three service modules
unconditionally to health-check them — this needs rewriting for `light-api`, since those heavy modules
won't exist in that function's image at all.

## Combustion's dependency reduction

`combustion_service.py` currently imports:
```python
from exposan.htl import create_components          # -> qsdsan.Component machinery
from biorefineries.cane import create_sugarcane_chemicals   # -> transitively imports biorefineries.cellulosic
from biorefineries.tea import create_cellulosic_ethanol_tea # -> cheap import, but unused output
```

Investigation found all three can be removed:

- **`create_components()`** builds an 85-species `qsdsan.Components` set; `combustion_service.py` only
  ever pulls out 4 of them (`Sludge_lipid`, `Sludge_protein`, `Sludge_carbo`, `Sludge_ash`) and copies
  them into a plain `bst.Chemicals` collection. None of the qsdsan-specific fields (`particle_size`,
  `degradability`, `organic`) are read again — only the physical properties (formula, density → `V`,
  `HHV`, `Cn`, `mu`) matter. These get rebuilt directly as plain `thermosteam.Chemical` objects in
  `app/services/combustion/_chemicals.py`.
- **`create_sugarcane_chemicals()`** itself only uses `thermosteam`/`thermosteam.functional` in its body
  (~50 lines of pure `Chemical` construction) — the heavy transitive import is a module-level side
  effect of the file it lives in, unrelated to this specific function. Also rebuilt directly in
  `_chemicals.py`.
- **`create_cellulosic_ethanol_tea()`** builds a `CellulosicEthanolTEA(bst.TEA)` object that
  `combustion_calc_raw` assigns to `tea` and never reads again. Confirmed via direct inspection of
  `biosteam.facilities.BoilerTurbogenerator` and `System.simulate()` that neither touches
  `system.TEA` — it's only ever consulted (optionally) inside `save_report()`, which this code never
  calls. **This line is simply deleted**, not reimplemented — it's dead code, not a dependency to
  replace.

Net result: `combustion_service.py`'s heavy module depends on `biosteam`/`thermosteam` only.

**HHV/LHV/Hf handling in `_chemicals.py`:** `exposan.htl._components.py` (confirmed unchanged in
current EXPOsan `main`) explicitly zeroes any `HHV`/`LHV`/`Hf` left `None` after construction. For
`Sludge_lipid/protein/carbo/ash`, only `HHV` is set explicitly (from the `22.0e6 * MW / 1000` formula);
`LHV` and `Hf` are deliberately left at `0`. This ties directly into `[[project_thermosteam_hf_regression]]`
— the QSDsan-side guard added during that work specifically suppresses thermosteam's Dulong/Boie
auto-estimation for `organic=False` chemicals with no measured heat of formation and no explicit user
value, exactly to prevent a fabricated energetics value for pseudo-species like these. `_chemicals.py`
should hardcode `LHV=0`/`Hf=0` explicitly, matching real behavior at every thermosteam version in play —
not delegate to auto-estimation.

**Verification requirement:** because chemicals move from `qsdsan.Component` to plain
`thermosteam.Chemical`, the implementation must include a direct attribute-level comparison (formula,
`MW`, `HHV`, `LHV`, `Hf`, `Cn` model output, `mu` model output, `V` model output at a reference
temperature) between the old and new chemical objects — not just a before/after comparison of
`combustion_calc`'s final 3 returned metrics — before trusting the output is unchanged.

## Model caching per warm container

Each `*-calc` module (`htl/calc.py`, `combustion/calc.py`, `fermentation/calc.py`) gets a module-level
`_model = None` (or equivalent cached-state holder) guarded by a `threading.Lock()`. The first request
in a warm container builds the model (paying the full build/simulate cost once); subsequent requests in
the same container reuse it — override the relevant baseline parameter and re-call
`metrics_at_baseline()` (or the equivalent re-simulate step) rather than rebuilding from scratch. The
lock is required because FastAPI's thread pool can run handlers concurrently, and biosteam's global
`bst.settings`/flowsheet state is not concurrency-safe. This is a real win independent of the deferred
`simulate=False` fix — it eliminates the wasted first `create_model()` simulation for every request
after a container's first.

## Verification approach

No dependency versions are changing, so this is a behavioral-parity check, not a numeric-drift
analysis:
- Run the existing test suite (`tests/test_htl.py`, `tests/test_combustion.py`,
  `tests/test_fermentation.py`, `tests/test_cors.py`) after the restructuring.
- Direct before/after comparison of `htl_calc(150)`, `combustion_calc(1000, "sludge")`,
  `fermentation_calc(100)` against the values already recorded in each service module's `__main__`
  block.
- The `_chemicals.py` attribute-level diff described above, specific to combustion.

## CI/Docker strategy

One `Dockerfile.lambda` parameterized by a build ARG selecting which entrypoint module to `CMD` into
(or four thin Dockerfiles sharing the same builder stage) — four images in the existing
`nj-bioenergy-api` ECR repo under distinct tag prefixes (`light-*`, `htl-*`, `combustion-*`,
`fermentation-*`). The existing `.github/workflows/build-and-push-lambda.yml` extends to build,
smoke-test, and push all four; the deploy step (once each function exists) updates all four.

## Operational constraints (carried forward from the prior plan)

- Every commit is proposed as a diff and requires explicit user approval before it's made — no
  autonomous commits, no `--no-verify`.
- No AWS credentials are available in this environment. Code/CI tasks (module restructuring,
  Dockerfile/workflow changes) are executed directly; anything touching the live `qsdsan-app` AWS
  account (creating/updating Lambda functions, Function URLs, CloudFront) is written as an exact
  runbook for whoever has the `yalin-admin` → `qsdsan-app` switch-role access documented in
  `deployments/qsdsan.md`.
- No local Docker install is available (neither this environment nor the user's machine) — image
  builds/smoke tests run inside GitHub Actions, as the existing `build-and-push-lambda.yml` already
  does.
- The public custom domain and its CloudFront distribution/ACM cert do not change — only origins
  and path-pattern behaviors are added/modified.

## Small fixes bundled in while touching these files

- Correct the stale `# exposan version @ git+...93d4173...` comments in `htl_service.py`/
  `combustion_service.py` to reflect the real PyPI pin (`exposan==1.4.1`) — obviously-correct, no
  behavior change.
- Update `CLAUDE.md`'s "Architecture: Dual-App Migration State" section, which still describes a Flask
  legacy app (`wsgi.py`, `app/blueprints/`) that no longer exists in this repo.
