# Lambda Restructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure `nj-bioenergy-api` into four independently-deployable FastAPI apps (one shared light lookup/health app + one heavy per-service calc app each for HTL/combustion/fermentation), each with a minimal, non-overlapping dependency footprint, and carry that through to a live AWS Lambda deployment behind CloudFront.

**Architecture:** Split each service module into a `lookup.py` (pandas/CSV only) and `calc.py` (heavy compute, cached model per warm container). Combustion's `calc.py` drops `exposan`/`biorefineries` entirely by rebuilding the handful of chemical values it actually reads as plain `thermosteam.Chemical` objects, and by deleting a dead TEA object it never reads. Four slim FastAPI entrypoint modules compose the split routers into four deployables; `app/main.py` stays as the "everything" local-dev entrypoint. Four Lambda functions, four Dockerfiles, one CI workflow, CloudFront routes by path pattern to four origins.

**Tech Stack:** FastAPI, uvicorn, biosteam/thermosteam/exposan (pinned versions unchanged — see Global Constraints), pytest, Docker, AWS Lambda (container image) + Function URLs, CloudFront, GitHub Actions.

**Full design rationale:** see `guides/lambda-restructure-design.md` (approved, committed as `35bbf81`). This plan implements that design; it does not re-derive it.

## Global Constraints

- No dependency version changes. `thermosteam==0.45.0`, `biosteam==2.46.1`, `qsdsan==1.4.1`, `exposan==1.4.1`, and every other pin in `pyproject.toml`/`uv.lock` stay exactly as they are. Nothing in this plan bumps a version.
- No behavior change to any endpoint's computed output. This is a structural refactor (where imports happen, which files things live in) — every task that touches a `calc.py` module must include a numeric-parity check against the pre-refactor output.
- Every commit is proposed as a diff and requires explicit user approval before it's made.
- No AWS credentials are available in this environment. Tasks 1-10 (below) are code/CI changes executed directly. Tasks 11-14 are AWS console/CLI steps written as an exact runbook for whoever has the `yalin-admin` → `qsdsan-app` switch-role access documented in `deployments/qsdsan.md` — the assistant does not execute them.
- No local Docker install is available (neither this environment nor the user's machine) — image builds/smoke tests run inside GitHub Actions, per the existing `.github/workflows/build-and-push-lambda.yml` pattern.
- Run `uv run pytest -v` (or `./.venv/Scripts/python.exe -m pytest -v` if `uv run` fails to resolve the venv) after every task that touches `app/` or `tests/`.

---

## File Structure

**Create:**
- `app/services/htl/__init__.py`, `app/services/htl/lookup.py`, `app/services/htl/calc.py`
- `app/services/combustion/__init__.py`, `app/services/combustion/_chemicals.py`, `app/services/combustion/lookup.py`, `app/services/combustion/calc.py`
- `app/services/fermentation/__init__.py`, `app/services/fermentation/lookup.py`, `app/services/fermentation/calc.py`
- `app/routers/htl_lookup.py`, `app/routers/htl_calc.py`
- `app/routers/combustion_lookup.py`, `app/routers/combustion_calc.py`
- `app/routers/fermentation_lookup.py`, `app/routers/fermentation_calc.py`
- `app/app_factory.py`
- `app/entrypoints/__init__.py`, `app/entrypoints/light_app.py`, `app/entrypoints/htl_app.py`, `app/entrypoints/combustion_app.py`, `app/entrypoints/fermentation_app.py`
- `Dockerfile.lambda.light`, `Dockerfile.lambda.htl`, `Dockerfile.lambda.combustion`, `Dockerfile.lambda.fermentation`
- `tests/test_combustion_chemicals.py`

**Modify:**
- `app/routers/health.py` (light-safe `/ready`)
- `app/main.py` (use `app_factory`, import the new split routers)
- `.github/workflows/build-and-push-lambda.yml` (build/smoke-test/push/deploy all four images)
- `CLAUDE.md` (drop the stale Flask section, describe the new structure)
- `tests/test_htl.py`, `tests/test_combustion.py`, `tests/test_fermentation.py` (patch targets move to the new router modules)

**Delete:**
- `app/services/htl_service.py`, `app/services/combustion_service.py`, `app/services/fermentation_service.py`
- `app/routers/htl.py`, `app/routers/combustion.py`, `app/routers/fermentation.py`
- `Dockerfile.lambda`

---

### Task 1: HTL service/router split

**Files:**
- Create: `app/services/htl/__init__.py`, `app/services/htl/lookup.py`, `app/services/htl/calc.py`
- Create: `app/routers/htl_lookup.py`, `app/routers/htl_calc.py`
- Delete: `app/services/htl_service.py`, `app/routers/htl.py`
- Modify: `tests/test_htl.py`

**Interfaces:**
- Produces: `app.services.htl.lookup.htl_convert_sludge_mass_kg_hr(sludge, unit) -> float`, `app.services.htl.lookup.htl_county(county, state_data=STATE_DATA) -> tuple`, `app.services.htl.calc.htl_calc(kg_hr, mmbtu_to_gal=0.12845, kg_to_lb=2.20462) -> tuple`.

- [ ] **Step 1: Create `app/services/htl/__init__.py`**

```python
```
(empty — makes `app/services/htl` a package)

- [ ] **Step 2: Create `app/services/htl/lookup.py`**

```python
"""
HTL lookup functions: unit conversion and NJ county data lookup.

Pandas/CSV only — no exposan/biosteam. Kept separate from calc.py so the
light Lambda function (health + county lookups) never needs to import the
heavy scientific stack.
"""

import os
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "..", "..", "data", "htl", "htl_data.csv")

STATE_DATA = pd.read_csv(CSV_PATH)


def htl_convert_sludge_mass_kg_hr(sludge, unit):
    """
    Take the sludge in the unit specified and convert it to kg/hr.

    Parameters
    ----------
    sludge : float
        The sludge in the unit specified.
    unit : str
        The unit of the sludge.
        Available units - 'kghr', 'tons', 'tonnes', 'mgd', 'm3d' [kg/hr, short tons/yr, metric tonnes/yr, million gallons/day, cubic meters/day].

    Returns
    -------
    sludge_kg_hr : float
        The sludge in kg/hr.

    Raises
    ------
    ValueError
        If the unit is not found.
    TypeError
        If the sludge is not a float.
    TypeError
        If the unit is not a string.

    Example
    -------
    htl_convert_sludge_mass_kg_hr(150, 'tons')
    >>> 15.56  # Example of converting 150 tons/year to kg/hr
    """

    if not isinstance(sludge, (int, float)):
        raise TypeError("Sludge should be a float or an int.")

    if not isinstance(unit, str):
        raise TypeError("Unit should be a string.")

    if unit.lower() == 'kghr':
        return sludge
    elif unit.lower() == 'tons':
        return sludge * 907.185 / 8760
    elif unit.lower() == 'tonnes':
        return sludge * 1000 / 8760
    elif unit.lower() == 'mgd':
        return sludge * 3.78541 * 1e6 / 24
    elif unit.lower() == 'm3d':
        return sludge * 1000 / 24
    else:
        raise ValueError(f"Unit '{unit}' not found.")


def htl_county(county, state_data=STATE_DATA):
    """
    Take a county name in New Jersey from the user and return the price and GWP.

    Parameters
    ----------
    county : str
        The name of the county.
        Available name - Atlantic, Bergen, Burlington, Camden, Cape May, Cumberland, Essex, Gloucester, Hudson, Hunterdon, Mercer, Middlesex, Monmouth, Morris, Ocean, Passaic, Salem, Somerset, Sussex, Union, Warren.
    state_data : pd.DataFrame, optional
        The data of the counties. Default is STATE_DATA.

    Returns
    -------
    tuple
        name_final : str
            The name of the county.
        sludge : float
            The dry metric tonnes of sludge in that county.
        price : float
            The minimum diesel selling price in $/gal diesel.
        gwp : float
            The global warming potential of diesel in lb CO2/gal diesel.

    Raises
    ------
    ValueError
        If the county is not found.
    TypeError
        If the county is not a string.
    TypeError
        If the state_data is not a DataFrame.
    """

    if not isinstance(county, str):
        raise TypeError("County should be a string.")
    if not isinstance(state_data, pd.DataFrame):
        raise TypeError("State data should be a DataFrame.")

    name_final = None
    for item in state_data["County"]:
        if county.lower() in item.lower():
            name_final = item
            break

    if name_final is None:
        raise ValueError(f"County {county} not found.")

    mass_dmt = float(state_data.loc[state_data["County"] == name_final, "County Total (Dry Metric Tonnes/Year)"].values[0])
    price = float(state_data.loc[state_data["County"] == name_final, "MDSP ($/gal)"].values[0])
    gwp = float(state_data.loc[state_data["County"] == name_final, "GWP (lb CO2/gal)"].values[0])

    return name_final, mass_dmt, price, gwp
```

- [ ] **Step 3: Create `app/services/htl/calc.py`**

```python
"""
HTL diesel-production calculation (MDSP, GWP) from sludge mass.

Heavy: imports exposan.htl.create_model and chaospy. The built model is
cached per warm Lambda container behind a lock, since biosteam's global
flowsheet/settings state isn't concurrency-safe and FastAPI's thread pool
can run handlers concurrently.
"""

import threading

from chaospy import distributions as shape  # chaospy version 4.3.17

from exposan.htl import create_model  # exposan version: PyPI exposan==1.4.1 (see pyproject.toml/uv.lock)

_model = None
_model_lock = threading.Lock()


def _get_model():
    """Build (once per warm container) or return the cached HTL model."""
    global _model
    if _model is not None:
        return _model
    with _model_lock:
        if _model is None:
            model = create_model(
                plant_size=True,
                feedstock='sludge',
                include_CFs_as_metrics=False,
                include_other_metrics=False,
                include_other_CFs_as_metrics=False,
            )
            param = model.parameter
            sys = model.system
            stream = sys.flowsheet.stream
            raw_wastewater = stream.feedstock_assumed_in_wastewater
            dist = shape.Uniform(12618039, 18927059)

            @param(name='plant_size',
                   element=raw_wastewater,
                   kind='coupled',
                   units='kg/hr',
                   baseline=15772549,
                   distribution=dist)
            def set_plant_size(i):
                raw_wastewater.F_mass = i

            _model = model
        return _model


def htl_calc(kg_hr, mmbtu_to_gal=0.12845, kg_to_lb=2.20462):
    """
    Take the existing dry metric tonnes of sludge and return the minimum diesel selling price and global warming potential of diesel.

    Parameters
    ----------
    kg_hr : float
        Sludge in kg/hr.
    mmbtu_to_gal : float, optional
        Conversion factor for MMBTU to gal diesel. Default is 0.12845.
        1 MMBTU = 0.12845 gal diesel.
    kg_to_lb : float, optional
        Conversion factor for kg to lb. Default is 2.20462.
        1 kg CO2 = 2.20462 lb CO2.

    Returns
    -------
    MDSP : float
        Minimum diesel selling price in $/gal diesel.
    GWP : float
        Global warming potential of diesel in lb CO2/gal diesel.

    Raises
    ------
    TypeError
        If kg_hr is not a float.
    TypeError
        If mmbtu_to_gal is not a float.
    TypeError
        If kg_to_lb is not a float.

    Example
    -------
    htl_calc(15772549)
    >>> (2.5, 10)

    Notes
    -----
    1. If used in other parts, make sure to convert the sludge to kg/hr.
    2. The MSDP is in $/gal diesel, which can be converted to various other units.
    3. The GWP is in lb CO2/gal diesel, which can be converted to various other units.
    """

    if not isinstance(kg_hr, (int, float)):
        raise TypeError("Sludge should be a float.")
    if not isinstance(mmbtu_to_gal, (int, float)):
        raise TypeError("MMBTU to gal should be a float.")
    if not isinstance(kg_to_lb, (int, float)):
        raise TypeError("KG to lb should be a float.")

    model = _get_model()
    plant_size = model.parameters[-1]
    plant_size.baseline = kg_hr

    df = model.metrics_at_baseline()

    MSDP, GWP = [m for m in model.metrics if m.name in ('MDSP', 'GWP diesel')]

    return MSDP.get(), GWP.get() * mmbtu_to_gal * kg_to_lb
```

Note: the model-caching change means `htl_calc` no longer rebuilds the model from scratch on every call within the same warm container — the first call in a container pays the full `create_model()` cost (which includes one `sys.simulate()` internally), subsequent calls in that container reuse the cached model and just re-run `metrics_at_baseline()`. This does not change any endpoint's *output* for a given `kg_hr` — it only changes how much repeated work happens across multiple calls to the same process. The `ww_2_dry_sludge`/`print` debug lines from the original are dropped (they printed to stdout and were not used in the return value).

- [ ] **Step 4: Create `app/routers/htl_lookup.py`**

```python
"""
HTL county-lookup FastAPI router (light — no exposan/biosteam).

Endpoints:
- GET /htl/county - Get HTL potential for a specific NJ county
"""

from fastapi import APIRouter, Query, HTTPException

from app.services.htl.lookup import htl_county

from app.models.htl import (
    HTLCountyResponse,
    ErrorResponseWithMessage
)

router = APIRouter()


@router.get(
    "/htl/county",
    response_model=HTLCountyResponse,
    responses={
        400: {"model": ErrorResponseWithMessage, "description": "Bad request"},
        404: {"model": ErrorResponseWithMessage, "description": "County not found"},
        500: {"model": ErrorResponseWithMessage, "description": "Unexpected error"}
    },
    summary="Get HTL potential for NJ county",
    description="""
    Takes in a county name and returns:
    1. The name of the county
    2. The mass of the sludge in kg/hr
    3. The price of the HTL product in $/gallon
    4. The greenhouse gas emissions in lb CO2e/gallon
    """
)
async def htl_county_data(
    county_name: str = Query(
        ...,
        description="The name of the New Jersey county",
        openapi_examples={"default": {"value": "Atlantic"}}
    )
) -> HTLCountyResponse:
    try:
        result = htl_county(county_name)

        if result:
            name, sludge, price, gwp = result
            return HTLCountyResponse(
                county_name=name,
                sludge=sludge,
                price=price,
                gwp=gwp
            )
        else:
            raise HTTPException(
                status_code=500,
                detail="Unexpected error in HTL county calculation"
            )

    except ValueError:
        raise HTTPException(
            status_code=404,
            detail=f"County '{county_name}' not found. Valid counties are the 21 NJ counties (e.g. Essex, Atlantic, Bergen)."
        )
    except TypeError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
```

- [ ] **Step 5: Create `app/routers/htl_calc.py`**

```python
"""
HTL diesel-production FastAPI router (heavy — imports exposan.htl).

Endpoints:
- GET /htl/calc - Calculate HTL diesel production from sludge mass
"""

from fastapi import APIRouter, Query, HTTPException

from app.services.htl.calc import htl_calc
from app.services.htl.lookup import htl_convert_sludge_mass_kg_hr as htl_convert_kg

from app.models.htl import (
    HTLCalcResponse,
    HTLUnit,
    ErrorResponse
)

router = APIRouter()


@router.get(
    "/htl/calc",
    response_model=HTLCalcResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Bad request"},
        422: {"model": ErrorResponse, "description": "Invalid unit"},
        500: {"model": ErrorResponse, "description": "Unexpected error"}
    },
    summary="Calculate HTL diesel production",
    description="""
    Takes in a sludge mass in a specified unit and returns:
    1. Mass of the sludge in kg/hr
    2. Price of the HTL product in $/gallon
    3. Greenhouse gas emissions in lb CO2e/gallon
    """
)
async def htl_calc_data(
    sludge: float = Query(
        ...,
        gt=0,
        description="The mass of the sludge",
        openapi_examples={"default": {"value": 100.0}}
    ),
    unit: HTLUnit = Query(
        HTLUnit.KGHR,
        description="The unit of the sludge mass",
        openapi_examples={"default": {"value": "kghr"}}
    )
) -> HTLCalcResponse:
    sludge_kg_hr = htl_convert_kg(sludge, unit.value)

    try:
        result = htl_calc(sludge_kg_hr)

        if result:
            price, gwp = result
            return HTLCalcResponse(
                sludge=sludge_kg_hr,
                price=price,
                gwp=gwp
            )
        else:
            raise HTTPException(
                status_code=500,
                detail="Unexpected error in HTL calculation"
            )

    except TypeError as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
```

- [ ] **Step 6: Update `tests/test_htl.py`'s import and patch targets**

Replace the fixture in `TestHTLConversion.setup`:

```python
    @pytest.fixture(autouse=True)
    def setup(self):
        from app.services.htl.lookup import htl_convert_sludge_mass_kg_hr
        self.convert = htl_convert_sludge_mass_kg_hr
```

Replace every `patch("app.routers.htl.htl_convert_kg", ...)` and `patch("app.routers.htl.htl_calc", ...)` with `patch("app.routers.htl_calc.htl_convert_kg", ...)` / `patch("app.routers.htl_calc.htl_calc", ...)` (9 occurrences across `TestHTLCalcEndpoint`).

Replace every `patch("app.routers.htl.htl_county", ...)` with `patch("app.routers.htl_lookup.htl_county", ...)` (5 occurrences across `TestHTLCountyEndpoint`).

- [ ] **Step 7: Delete the old files**

```bash
git rm app/services/htl_service.py app/routers/htl.py
```

- [ ] **Step 8: Run the HTL tests**

Run: `uv run pytest tests/test_htl.py -v`
Expected: all tests pass (router registration happens in Task 6 — until then, `app/main.py` still imports the deleted `app.routers.htl`, so this step will fail until Task 6 lands. If executing tasks strictly in order, skip running the full test file here and instead just run:)

Run: `uv run python -c "from app.services.htl.lookup import htl_convert_sludge_mass_kg_hr, htl_county; from app.services.htl.calc import htl_calc; print(htl_calc(150))"`
Expected: prints a `(price, gwp)` tuple close to the original recorded value `(397878.8243590509, 408526.3837657836)` for `htl_calc(150)` (the model-caching change does not alter this — it's the same computation, same inputs).

- [ ] **Step 9: Commit**

```bash
git add app/services/htl app/routers/htl_lookup.py app/routers/htl_calc.py tests/test_htl.py
git commit -m "Split HTL service/router into lookup (light) and calc (heavy, cached model)"
```

---

### Task 2: Combustion chemical definitions (`_chemicals.py`)

**Files:**
- Create: `app/services/combustion/__init__.py`, `app/services/combustion/_chemicals.py`
- Create: `tests/test_combustion_chemicals.py`

**Interfaces:**
- Produces: `app.services.combustion._chemicals.create_chemicals() -> biosteam.Chemicals` — a drop-in replacement for the `create_chemicals()` currently defined inside `app/services/combustion_service.py`, built without `exposan`/`biorefineries`.

This task runs **before** Task 3 deletes `app/services/combustion_service.py`, specifically so the test below can compare the old and new chemical objects side by side.

- [ ] **Step 1: Write the failing parity test**

```python
# tests/test_combustion_chemicals.py
"""
Parity test: the new dependency-free chemical construction in
app/services/combustion/_chemicals.py must produce chemicals with the same
physical properties as the old exposan/biorefineries-based construction in
app/services/combustion_service.py, for every property combustion_calc_raw
actually reads (formula, MW, HHV, LHV, Hf, Cn model output, mu model
output, V model output).
"""
import pytest

REFERENCE_T = 298.15  # K
REFERENCE_P = 101325  # Pa

CHEMICAL_IDS = ["Water", "Lipids", "Proteins", "Carbohydrates", "Ash",
                "Cellulose", "Hemicellulose", "Lignin", "CaO",
                "P4O10", "O2", "N2", "CH4", "CO2"]


def _snapshot(chemical):
    return {
        "formula": chemical.formula,
        "MW": chemical.MW,
        "HHV": chemical.HHV,
        "LHV": chemical.LHV,
        "Hf": chemical.Hf,
        "Cn": chemical.Cn(REFERENCE_T),
        "mu": chemical.mu(REFERENCE_T, REFERENCE_P) if chemical.mu.method else None,
        "V": chemical.V(REFERENCE_T, REFERENCE_P) if chemical.V.method else None,
    }


def test_new_chemicals_match_old_chemicals():
    from app.services.combustion_service import create_chemicals as old_create_chemicals
    old_chems = old_create_chemicals()

    from app.services.combustion._chemicals import create_chemicals as new_create_chemicals
    new_chems = new_create_chemicals()

    for chem_id in CHEMICAL_IDS:
        old_snap = _snapshot(getattr(old_chems, chem_id))
        new_snap = _snapshot(getattr(new_chems, chem_id))
        for key in old_snap:
            old_val, new_val = old_snap[key], new_snap[key]
            if isinstance(old_val, float) and isinstance(new_val, float):
                assert old_val == pytest.approx(new_val, rel=1e-9), (
                    f"{chem_id}.{key} mismatch: old={old_val!r} new={new_val!r}"
                )
            else:
                assert old_val == new_val, (
                    f"{chem_id}.{key} mismatch: old={old_val!r} new={new_val!r}"
                )
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/test_combustion_chemicals.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.combustion._chemicals'`

- [ ] **Step 3: Create `app/services/combustion/__init__.py`**

```python
```
(empty — makes `app/services/combustion` a package)

- [ ] **Step 4: Create `app/services/combustion/_chemicals.py`**

```python
"""
Chemical definitions combustion_calc needs, built directly with thermosteam
instead of importing exposan/biorefineries.

Why: combustion_service.py previously pulled 4 chemicals out of
exposan.htl.create_components() (an 85-species qsdsan.Components set) and
9 out of biorefineries.cane.chemicals.create_sugarcane_chemicals(). Neither
qsdsan's sanitation-specific fields (particle_size, degradability, organic)
nor biorefineries.cane's other functions are ever read by combustion — only
the physical properties (formula, density -> V, HHV, Cn, mu) matter, all of
which are plain thermosteam.Chemical fields. Rebuilding them directly here
also removes a large transitive cost: biorefineries/cane/chemicals.py's
module-level `from biorefineries import cellulosic` pulls in the entire
cellulosic-biorefinery-building package for functions this app never calls.

The functions below are near-verbatim copies of the originals (attribution
below), executed locally so combustion-calc's only dependencies are
biosteam/thermosteam.
"""

import thermosteam as tmo
from thermosteam import functional as fn
import biosteam as bst


def _create_sludge_chemicals():
    """
    Sludge_lipid/protein/carbo/ash, renamed Lipids/Proteins/Carbohydrates/Ash.

    Values copied from exposan.htl._components.create_components()
    (EXPOsan, University of Illinois/NCSA Open Source License,
    https://github.com/QSD-Group/EXPOsan/blob/main/LICENSE.txt). The
    original builds these as qsdsan.Component (adds particle_size/
    degradability/organic fields); combustion never reads those fields, so
    they're rebuilt as plain thermosteam.Chemical here.

    LHV and Hf are explicitly 0, matching exposan's own behavior: only HHV
    is set explicitly there, and exposan.htl._components.create_components()
    zeroes any of HHV/LHV/Hf left None after construction (confirmed
    unchanged in EXPOsan's current main branch as of 2026-07-03).
    """
    chemicals = []
    for name in ("Lipids", "Proteins", "Carbohydrates", "Ash"):
        chem = tmo.Chemical(name, phase='s', formula='C56H95O24N9P', search_db=False)
        chem.HHV = 22.0e6 * chem.MW / 1000  # Li et al., 2018
        chem.LHV = 0
        chem.Hf = 0
        chem.Cn.add_model(1.25e3 * chem.MW / 1000)  # Leow et al., 2015
        chem.mu.add_model(6000)  # made up value, so HTL.ins[0].nu ~ 0.03 m2/s (NREL 2013 appendix B)
        V_model = fn.rho_to_V(1400, chem.MW)
        chem.V.add_model(V_model)
        chemicals.append(chem)
    return chemicals


def _create_sugarcane_chemicals(yeast_includes_nitrogen=None):
    """
    Copied near-verbatim from biorefineries.cane.chemicals.create_sugarcane_chemicals()
    (BioSTEAM, UIUC open-source license,
    https://github.com/BioSTEAMDevelopmentGroup/biosteam/blob/master/LICENSE.txt).
    Only thermosteam/thermosteam.functional are used in this function's own
    body — the extra chemicals it builds (Water, Ethanol, Glucose, Sucrose,
    H3PO4, Octane, Flocculant, Solids, Yeast) are not used by combustion, but
    are kept here (not trimmed) so every chemical combustion *does* use
    (Cellulose, Hemicellulose, Lignin, CaO, P4O10, O2, N2, CH4, CO2) goes
    through the exact same construction sequence as upstream, including the
    density-override loops and the final .default() pass — trimming the
    unused ones risked silently changing a shared code path (e.g. P4O10's V
    model is overridden by the "insoluble_solids" loop below, not its raw
    database value).
    """
    if yeast_includes_nitrogen is None:
        yeast_includes_nitrogen = False
    (Water, Ethanol, Glucose, Sucrose, H3PO4, P4O10, CO2, Octane, O2, N2, CH4) = chemicals = tmo.Chemicals(
        ['Water', 'Ethanol',
         tmo.Chemical('Glucose', phase='l'),
         tmo.Chemical('Sucrose', phase='l'),
         tmo.Chemical('H3PO4', phase='l'),
         tmo.Chemical('P4O10', phase='l'),
         tmo.Chemical('CO2', phase='g'),
         'Octane',
         tmo.Chemical('O2', phase='g'),
         tmo.Chemical('N2', phase='g'),
         tmo.Chemical('CH4', phase='g')]
    )
    Glucose.N_solutes = 1
    Sucrose.N_solutes = 2

    def create_new_chemical(ID, phase='s', **constants):
        chemical = tmo.Chemical(ID, phase=phase, phase_ref=phase, search_db=False, **constants)
        chemicals.append(chemical)
        return chemical

    Ash = create_new_chemical('Ash', MW=1.)
    Cellulose = create_new_chemical('Cellulose', formula="C6H10O5", Hf=-975708.8)
    Hemicellulose = create_new_chemical('Hemicellulose', formula="C5H8O4", Hf=-761906.4)
    Flocculant = create_new_chemical('Flocculant', MW=1.)
    Lignin = create_new_chemical('Lignin', formula='C8H8O3', Hf=-452909.632)
    Solids = create_new_chemical('Solids', MW=1.)
    Yeast = create_new_chemical(
        'Yeast',
        formula='CH1.61O0.56N0.16' if yeast_includes_nitrogen else 'CH1.61O0.56',
        rho=1540,
        Cp=Glucose.Cp(298.15),
        default=True,
    )
    Yeast.Hf = Glucose.Hf / Glucose.MW * Yeast.MW
    CaO = create_new_chemical('CaO', formula='CaO')

    insoluble_solids = (Ash, Cellulose, Hemicellulose, Flocculant, Lignin, Solids, Yeast, P4O10)
    soluble_solids = (CaO, H3PO4, Glucose, Sucrose)

    for chemical in insoluble_solids:
        V = fn.rho_to_V(rho=1540, MW=chemical.MW)
        chemical.V.add_model(V, top_priority=True)

    for chemical in soluble_solids:
        V = fn.rho_to_V(rho=1e5, MW=chemical.MW)
        chemical.V.add_model(V, top_priority=True)

    Ash.Cn.add_model(0.09 * 4.184 * Ash.MW)
    CaO.Cn.add_model(1.02388 * CaO.MW)
    Cellulose.Cn.add_model(1.364 * Cellulose.MW)
    Hemicellulose.Cn.add_model(1.364 * Hemicellulose.MW)
    Flocculant.Cn.add_model(4.184 * Flocculant.MW)
    Lignin.Cn.add_model(1.364 * Lignin.MW)
    Solids.Cn.add_model(1.100 * Solids.MW)

    for chemical in chemicals:
        chemical.default()

    chemicals.compile()
    chemicals.set_synonym('Water', 'H2O')
    chemicals.set_synonym('Yeast', 'DryYeast')

    return chemicals


def create_chemicals():
    """Drop-in replacement for combustion_service.create_chemicals()."""
    Lipids, Proteins, Carbohydrates, Ash = _create_sludge_chemicals()
    cane_chems = _create_sugarcane_chemicals()

    Water = tmo.Chemical('Water')
    Cellulose = cane_chems.Cellulose
    Hemicellulose = cane_chems.Hemicellulose
    Lignin = cane_chems.Lignin
    CaO = cane_chems.CaO
    P4O10 = cane_chems.P4O10
    O2 = cane_chems.O2
    N2 = cane_chems.N2
    CH4 = cane_chems.CH4
    CO2 = cane_chems.CO2

    chems = bst.Chemicals((
        Water, Lipids, Proteins, Carbohydrates, Ash,
        Cellulose, Hemicellulose, Lignin, CaO,
        P4O10, O2, N2, CH4, CO2))
    bst.settings.set_thermo(chems)

    return chems
```

- [ ] **Step 5: Run the parity test**

Run: `uv run pytest tests/test_combustion_chemicals.py -v`
Expected: PASS. If any property mismatches, the assertion message names the exact chemical and property — fix `_chemicals.py` to match before proceeding (do not adjust the test's expectations to match a mismatch).

- [ ] **Step 6: Commit**

```bash
git add app/services/combustion/__init__.py app/services/combustion/_chemicals.py tests/test_combustion_chemicals.py
git commit -m "Add dependency-free combustion chemical definitions, verified against the old exposan/biorefineries-based construction"
```

---

### Task 3: Combustion service/router split

**Files:**
- Create: `app/services/combustion/lookup.py`, `app/services/combustion/calc.py`
- Create: `app/routers/combustion_lookup.py`, `app/routers/combustion_calc.py`
- Delete: `app/services/combustion_service.py`, `app/routers/combustion.py`
- Modify: `tests/test_combustion.py`, `tests/test_combustion_chemicals.py`

**Interfaces:**
- Consumes: `app.services.combustion._chemicals.create_chemicals()` (Task 2).
- Produces: `app.services.combustion.lookup.combustion_county(county, waste_type, state_data=STATE_DATA, compositions=COMPOSITIONS) -> tuple | None`, `app.services.combustion.calc.combustion_calc(mass, waste_type, compositions=COMPOSITIONS, dry_mass=None) -> tuple`.

- [ ] **Step 1: Create `app/services/combustion/lookup.py`**

```python
"""
Combustion county-lookup and unit data. Pandas/CSV only — no biosteam.
"""

import os
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "..", "..", "data", "combustion", "combustion_data.csv")

STATE_DATA = pd.read_csv(CSV_PATH)

COMPOSITIONS = {
    'sludge': [0.7, 0.257, 0.204, 0.463],
    'food': [0.74, 0.0679, 0.22, 0.2],
    'fog': [0.35, 0.01865, 0.987, 0.002],
    'green': [0.342, 0.134, 0.018, 0.049],
    'manure': [0.6634, 0.3056, 0.092325, 0.216375],
}


def combustion_county(county, waste_type, state_data=STATE_DATA, compositions=COMPOSITIONS):
    """
    Calculates the annual electricity production and avoided emissions from combustion of sludge, food waste, FOG, or green manure in a county.

    Parameters
    ----------
    county : str
        County name
    waste_type : str
        Type of waste, must be one of 'sludge', 'food', 'fog', 'green', or 'manure'
    state_data : pd.DataFrame
        DataFrame containing the waste data for each county
    compositions : dict
        Dictionary containing the compositions of water, ash, lipids, and proteins for each waste type

    Returns
    -------
    county : str
        County name
    waste_type : str
        Type of waste - sludge, food, fog, green, manure
    annual_electricity : float
        Annual electricity production in MWh
    avoided_emissions : float
        Avoided emissions in million metric tonnes
    avoided_emissions_percent : float
        Avoided emissions as a percentage of total emissions

    Raises
    ------
    ValueError
        If waste_type is not one of 'sludge', 'food', 'fog', 'green', or 'manure'
    TypeError
        If waste_type is not a string
    TypeError
        If county is not a string
    TypeError
        If state_data is not a pd.DataFrame
    """

    if not isinstance(waste_type, str):
        raise TypeError("waste_type must be a string")
    if not isinstance(county, str):
        raise TypeError("county must be a string")
    if not isinstance(state_data, pd.DataFrame):
        raise TypeError("state_data must be a pd.DataFrame")

    name_final = None

    for item in state_data['County']:
        if item.lower() == county.lower():
            name_final = item
            break

    if name_final is None:
        return None

    if waste_type not in ("sludge", "food", "fog", "green", "manure"):
        raise ValueError("waste_type must be one of 'sludge', 'food', 'fog', 'green', or 'manure'")

    col = waste_type.capitalize()
    mass = float(state_data.loc[state_data['County'] == name_final, f'{col} Mass kg/hr'].values[0])
    annual_electricity = float(state_data.loc[state_data['County'] == name_final, f'{col} Electricity (MWH)'].values[0])
    avoided_emissions = float(state_data.loc[state_data['County'] == name_final, f'{col} Avoided Emissions (million metric tonnes)'].values[0])
    avoided_emissions_percent = float(state_data.loc[state_data['County'] == name_final, f'{col} Avoided Emissions Percentage'].values[0])

    return (
        name_final,
        waste_type,
        mass,
        annual_electricity,
        avoided_emissions,
        avoided_emissions_percent
    )
```

- [ ] **Step 2: Create `app/services/combustion/calc.py`**

```python
"""
Combustion electricity-generation calculation.

Heavy: imports biosteam/thermosteam only (no exposan, no biorefineries —
see _chemicals.py). The chemicals + thermo settings are built once per
warm container behind a lock, since biosteam's global bst.settings/
flowsheet state isn't concurrency-safe and FastAPI's thread pool can run
handlers concurrently.
"""

import threading
import warnings

import biosteam as bst

from app.services.combustion._chemicals import create_chemicals
from app.services.combustion.lookup import COMPOSITIONS

warnings.filterwarnings("ignore")

_chemicals_ready = False
_chemicals_lock = threading.Lock()


class BoilerTurbogenerator(bst.facilities.BoilerTurbogenerator):

    def _load_utility_agents(self):
        steam_utilities = self.steam_utilities
        steam_utilities.clear()
        agent = self.agent
        units = self.other_units
        if units is not None:
            for agent in (*self.other_agents, agent):
                ID = agent.ID
                for u in units:
                    for hu in u.heat_utilities:
                        agent = hu.agent
                        if agent and agent.ID == ID:
                            steam_utilities.add(hu)
            self.electricity_demand = sum([u.power_utility.consumption for u in units])
        else:
            self.electricity_demand = 0


def _ensure_chemicals():
    """Set the process-wide thermo basis once per warm container."""
    global _chemicals_ready
    if _chemicals_ready:
        return
    with _chemicals_lock:
        if not _chemicals_ready:
            create_chemicals()
            _chemicals_ready = True


def combustion_calc_raw(mass_in_kg_hr, composition=[0.7, 0.257, 0.204, 0.463], nj_avg_power_co2=486.63, dry_mass_in_kg_hr=None):
    """
    Calculates the annual electricity production and avoided emissions based on the composition of water, ash, lipids, and proteins in the feedstock.

    Parameters
    ----------
    mass_in_kg_hr: float
        Mass flow rate in kg/hr
    composition : list
        [moisture, ash, lipids, proteins] in kg/hr
    nj_avg_power_co2 : float
        Average power plant emissions in lb CO2/MWh
        Default value from: https://www.epa.gov/egrid/data-explorer
    dry_mass_in_kg_hr : float
        Dry mass flow rate in kg/hr

    Returns
    -------
    annual_electricity : float
        Annual electricity production in MWh
    avoided_emissions : float
        Avoided emissions in million metric tonnes
    avoided_emissions_percent : float
        Avoided emissions as a percentage of total emissions

    Raises
    ------
    TypeError
        If composition is not a list
    TypeError
        If nj_avg_power_co2 is not a float or an int
    ValueError
        If composition does not have 4 elements
    """

    if not isinstance(composition, list):
        raise TypeError("composition must be a list")
    if not isinstance(nj_avg_power_co2, (float, int)):
        raise TypeError("nj_avg_power_co2 must be a float or an int")
    if len(composition) != 4:
        raise ValueError("composition must have 4 elements")

    a, b, c, d = composition
    _ensure_chemicals()

    moisture = a * mass_in_kg_hr

    if dry_mass_in_kg_hr is not None:
        moisture = mass_in_kg_hr - dry_mass_in_kg_hr

    ash = b * mass_in_kg_hr
    lipids = c * (mass_in_kg_hr - (moisture + ash))
    proteins = d * (mass_in_kg_hr - (moisture + ash))
    carbohydrates = mass_in_kg_hr - (moisture + ash + lipids + proteins)

    feedstock = bst.Stream('feedstock',
                            Water=moisture,
                            Ash=ash,
                            Lipids=lipids,
                            Proteins=proteins,
                            Carbohydrates=carbohydrates)
    BT = BoilerTurbogenerator('BT', ins=feedstock)
    sys = bst.System('sys', path=(BT,))
    BT = sys.flowsheet.unit.BT
    sys.simulate()

    total_electricity = -BT.net_power
    annual_electricity = total_electricity * 365 * 24 / 1e3

    NJ_avg_power_CO2 = nj_avg_power_co2 * 0.453592
    avoided_emissions = NJ_avg_power_CO2 * annual_electricity / 1e3 / 1e6

    avoided_emissions_percent = avoided_emissions / 97.6

    return (
        annual_electricity,
        avoided_emissions,
        avoided_emissions_percent
    )


def combustion_calc(mass, waste_type, compositions=COMPOSITIONS, dry_mass=None):
    """
    Calculates the annual electricity production and avoided emissions from combustion of sludge, food waste, FOG, or green manure.

    Parameters
    ----------
    mass : float
        Mass flow rate in kg/hr
    waste_type : str
        Type of waste, must be one of 'sludge', 'food', 'fog', 'green', or 'manure'
    compositions : dict
        Dictionary containing the compositions of water, ash, lipids, and proteins for each waste type
    dry_mass : float
        Dry mass flow rate in kg/hr

    Returns
    -------
    waste_type : str
        Type of waste - sludge, food, fog, green, manure
    mass : float
        Mass flow rate in kg/hr
    annual_electricity : float
        Annual electricity production in MWh
    avoided_emissions : float
        Avoided emissions in million metric tonnes
    avoided_emissions_percent : float
        Avoided emissions as a percentage of total emissions

    Raises
    ------
    ValueError
        If waste_type is not one of 'sludge', 'food', 'fog', 'green', or 'manure'
    TypeError
        If waste_type is not a string
    TypeError
        If mass is not a float or an int
    ValueError
        If compositions is not a dict
    ValueError
        If mass is less than or equal to 0
    """

    if not isinstance(waste_type, str):
        raise TypeError("waste_type must be a string")
    if not isinstance(mass, (float, int)):
        raise TypeError("mass must be a float or an int")
    if not isinstance(compositions, dict):
        raise ValueError("compositions must be a dict")
    if mass <= 0:
        raise ValueError("mass must be greater than 0")

    waste_type = waste_type.lower()

    match waste_type:
        case "sludge":
            list_to_use = compositions['sludge']
        case "food":
            list_to_use = compositions['food']
        case "fog":
            list_to_use = compositions['fog']
        case "green":
            list_to_use = compositions['green']
        case "manure":
            list_to_use = compositions['manure']
        case _:
            raise ValueError("waste_type must be one of 'sludge', 'food', 'fog', 'green', or 'manure'")

    annual_electricity, avoided_emissions, avoided_emissions_percent = combustion_calc_raw(mass, list_to_use, dry_mass_in_kg_hr=dry_mass)
    return (
        waste_type,
        mass,
        annual_electricity,
        avoided_emissions,
        avoided_emissions_percent
    )
```

- [ ] **Step 3: Create `app/routers/combustion_lookup.py`**

```python
"""
Combustion county-lookup FastAPI router (light — no biosteam).

Endpoints:
- GET /combustion/county - Get combustion potential for a specific NJ county
"""

from fastapi import APIRouter, Query, HTTPException

from app.services.combustion.lookup import combustion_county

from app.models.combustion import (
    CombustionCountyResponse,
    WasteType,
    CombustionErrorResponse
)

router = APIRouter()


@router.get(
    "/combustion/county",
    response_model=CombustionCountyResponse,
    responses={
        400: {"model": CombustionErrorResponse, "description": "Bad request"},
        404: {"model": CombustionErrorResponse, "description": "County not found"},
        422: {"model": CombustionErrorResponse, "description": "Invalid waste type"},
        500: {"model": CombustionErrorResponse, "description": "Unexpected error"}
    },
    summary="Get combustion potential for NJ county",
    description="""
    Takes in a county name and a waste type, then returns:
    1. The county name (as found in the data set)
    2. The mass (kg/hr) associated with that county for the specified waste
    3. The annual electricity production in MWh
    4. The avoided emissions in million metric tonnes
    5. The fraction of total NJ emissions avoided
    """
)
async def combustion_county_data(
    county_name: str = Query(
        ...,
        description="The name of the New Jersey county",
        openapi_examples={"default": {"value": "Essex"}}
    ),
    waste_type: WasteType = Query(
        WasteType.SLUDGE,
        description="The type of waste",
        openapi_examples={"default": {"value": "sludge"}}
    )
) -> CombustionCountyResponse:
    try:
        result = combustion_county(county_name, waste_type.value)

        if result is None:
            raise HTTPException(
                status_code=404,
                detail=f"County '{county_name}' not found. Valid counties are the 21 NJ counties (e.g. Essex, Atlantic, Bergen)."
            )

        name_final, wt, mass, electricity, emissions, percent = result

        return CombustionCountyResponse(
            county_name=name_final,
            waste_type=wt,
            mass=mass,
            electricity=electricity,
            emissions=emissions,
            percent=percent
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except TypeError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
```

- [ ] **Step 4: Create `app/routers/combustion_calc.py`**

```python
"""
Combustion electricity-generation FastAPI router (heavy — imports biosteam).

Endpoints:
- GET /combustion/calc - Calculate electricity generation from waste
"""

from fastapi import APIRouter, Query, HTTPException

from app.services.combustion.calc import combustion_calc

from app.models.combustion import (
    CombustionCalcResponse,
    CombustionUnit,
    WasteType,
    CombustionErrorResponse
)

router = APIRouter()


def convert_mass_to_kg_hr(mass: float, unit: str) -> float:
    """Convert mass from various units to kg/hr."""
    if unit == 'kghr':
        return mass
    elif unit == 'tons':
        return mass * 907.185 / (365 * 24)
    elif unit == 'tonnes':
        return mass * 1000 / (365 * 24)
    elif unit == 'mgd':
        return mass * 1e6 * 3.78541 / 24
    elif unit == 'm3d':
        return mass * 1000 / 24
    else:
        raise ValueError(f"Invalid unit: {unit}")


@router.get(
    "/combustion/calc",
    response_model=CombustionCalcResponse,
    responses={
        400: {"model": CombustionErrorResponse, "description": "Bad request"},
        422: {"model": CombustionErrorResponse, "description": "Invalid unit or waste type"},
        500: {"model": CombustionErrorResponse, "description": "Unexpected error"}
    },
    summary="Calculate combustion electricity generation",
    description="""
    Takes in a mass, a unit of that mass, and a waste type, then returns:
    1. The mass converted to kg/hr
    2. The annual electricity production in MWh
    3. The avoided emissions in million metric tonnes
    4. The fraction of total NJ emissions avoided
    """
)
async def combustion_calc_data(
    mass: float = Query(
        ...,
        gt=0,
        description="The mass of the feedstock",
        openapi_examples={"default": {"value": 100.0}}
    ),
    unit: CombustionUnit = Query(
        CombustionUnit.KGHR,
        description="The unit of the feedstock mass",
        openapi_examples={"default": {"value": "kghr"}}
    ),
    waste_type: WasteType = Query(
        WasteType.SLUDGE,
        description="The type of waste",
        openapi_examples={"default": {"value": "sludge"}}
    )
) -> CombustionCalcResponse:
    try:
        mass_kg_hr = convert_mass_to_kg_hr(mass, unit.value)
        result = combustion_calc(mass_kg_hr, waste_type.value)

        if not result:
            raise HTTPException(status_code=500, detail="Unexpected error in combustion_calc")

        wt, mass_kg_hr2, electricity, emissions, percent = result

        return CombustionCalcResponse(
            mass=mass_kg_hr2,
            waste_type=wt,
            electricity=electricity,
            emissions=emissions,
            percent=percent
        )

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except TypeError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
```

- [ ] **Step 5: Update `tests/test_combustion.py`'s patch targets**

Replace every `from app.services.combustion_service import combustion_calc` with `from app.services.combustion.calc import combustion_calc`, and every `patch("app.services.combustion_service.combustion_calc_raw", ...)` with `patch("app.services.combustion.calc.combustion_calc_raw", ...)` (2 occurrences, in `TestCombustionCalcService`).

Replace every `patch("app.routers.combustion.combustion_calc", ...)` with `patch("app.routers.combustion_calc.combustion_calc", ...)` (in `TestCombustionCalcEndpoint`).

Replace every `patch("app.routers.combustion.combustion_county", ...)` with `patch("app.routers.combustion_lookup.combustion_county", ...)` (in `TestCombustionCountyEndpoint`).

- [ ] **Step 6: Update `tests/test_combustion_chemicals.py`'s old-path import**

`app.services.combustion_service` is deleted in this task, so the parity test from Task 2 can no longer import it. Change:

```python
    from app.services.combustion_service import create_chemicals as old_create_chemicals
```

Delete this test file's `test_new_chemicals_match_old_chemicals` function entirely — its job (verify the new construction matches the old one) is done once and shouldn't run against code that no longer exists. Replace the file's contents with a smaller smoke test that just confirms the new module's chemicals are self-consistent (importable, non-empty properties):

```python
# tests/test_combustion_chemicals.py
"""
Smoke test for app/services/combustion/_chemicals.py — the one-time parity
check against the old exposan/biorefineries-based construction ran in the
commit that introduced this module (see git history) and is not re-run
here since the old construction path no longer exists.
"""


def test_create_chemicals_returns_expected_ids():
    from app.services.combustion._chemicals import create_chemicals
    chems = create_chemicals()
    expected_ids = {"Water", "Lipids", "Proteins", "Carbohydrates", "Ash",
                     "Cellulose", "Hemicellulose", "Lignin", "CaO",
                     "P4O10", "O2", "N2", "CH4", "CO2"}
    actual_ids = {chem.ID for chem in chems}
    assert expected_ids == actual_ids


def test_sludge_derived_chemicals_have_expected_energetics():
    from app.services.combustion._chemicals import create_chemicals
    chems = create_chemicals()
    for chem_id in ("Lipids", "Proteins", "Carbohydrates", "Ash"):
        chem = getattr(chems, chem_id)
        assert chem.HHV == 22.0e6 * chem.MW / 1000
        assert chem.LHV == 0
        assert chem.Hf == 0
```

- [ ] **Step 7: Delete the old files**

```bash
git rm app/services/combustion_service.py app/routers/combustion.py
```

- [ ] **Step 8: Run the combustion tests**

Run: `uv run python -c "from app.services.combustion.calc import combustion_calc; print(combustion_calc(1000.0, 'sludge'))"`
Expected: prints a tuple close to the original recorded value for `combustion_calc(1000, "sludge")`: `('sludge', 1000.0, 16771611.411033249, 3.7020225242133353, 0.037930558649726796)` (allow floating-point tolerance).

Run: `uv run pytest tests/test_combustion_chemicals.py -v`
Expected: both tests pass.

(Full `tests/test_combustion.py` suite runs after Task 6 rewires `app/main.py` — same ordering note as Task 1 Step 8.)

- [ ] **Step 9: Commit**

```bash
git add app/services/combustion tests/test_combustion.py tests/test_combustion_chemicals.py
git commit -m "Split combustion service/router into lookup (light) and calc (heavy, no exposan/biorefineries)"
```

---

### Task 4: Fermentation service/router split

**Files:**
- Create: `app/services/fermentation/__init__.py`, `app/services/fermentation/lookup.py`, `app/services/fermentation/calc.py`
- Create: `app/routers/fermentation_lookup.py`, `app/routers/fermentation_calc.py`
- Delete: `app/services/fermentation_service.py`, `app/routers/fermentation.py`
- Modify: `tests/test_fermentation.py`

**Interfaces:**
- Produces: `app.services.fermentation.lookup.fermentation_convert_feedstock_kg_hr(feedstock, unit='kghr') -> float`, `app.services.fermentation.lookup.fermentation_county(name, state_data=STATE_DATA) -> tuple`, `app.services.fermentation.calc.fermentation_calc(mass, cornstover_price=0.2, GWP_CFs=GWP_CFs, characterization_factors=(1., 1.,), power_utility_price=0.07) -> tuple`.

Fermentation legitimately needs `biorefineries.cellulosic`/`biorefineries.cornstover` (it instantiates the actual modeled biorefinery process) — no chemical-vendoring opportunity here, unlike combustion.

- [ ] **Step 1: Create `app/services/fermentation/__init__.py`**

```python
```
(empty — makes `app/services/fermentation` a package)

- [ ] **Step 2: Create `app/services/fermentation/lookup.py`**

```python
"""
Fermentation unit conversion and NJ county lookup. Pandas/CSV only — no
biosteam/biorefineries.
"""

import os
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "..", "..", "data", "fermentation", "fermentation_data.csv")

STATE_DATA = pd.read_csv(CSV_PATH)


def fermentation_convert_feedstock_kg_hr(feedstock, unit='kghr'):
    """
    Convert the feedstock to kg/hr.

    Parameters
    ----------
    feedstock : float
        The mass of the feed
    unit : str
        The unit of the feedstock mass.
        They can choose from the following:
        - 'kghr' kg/hr
        - 'tons' tons/yr
        - 'tonnes' tonnes/yr
        Default is 'kghr'.

    Returns
    -------
    feedstock : float
        The mass of the feedstock in kg/hr.

    Raises
    ------
    ValueError
        If the unit is not in the list of valid units.
    TypeError
        If the feedstock is not a number.
    TypeError
        If the unit is not a string.

    Example
    -------
    >>> fermentation_convert_feedstock_kg_hr(100, 'tons')
    0.011363636363636364
    """

    if not isinstance(feedstock, (int, float)):
        raise TypeError('Feedstock should be a number')
    if not isinstance(unit, str):
        raise TypeError('Unit should be a string')

    if unit.lower() == 'kghr':
        return feedstock
    elif unit.lower() == 'tons':
        return feedstock * 907.185 / 8760
    elif unit.lower() == 'tonnes':
        return feedstock * 1000 / 8760
    else:
        raise ValueError('Invalid unit')


def fermentation_county(name, state_data=STATE_DATA):
    """
    Take a county name from the user and return the annual ethanol price and GWP.

    Parameters
    ----------
    name : str
        The name of the county.
    state_data : pandas.DataFrame
        The data for the state.
        Set to default value of STATE_DATA.
        https://ecocomplex.rutgers.edu/biomass-energy-potential.html

    Returns
    -------
    tuple
        Contains the following:
        name_final : str
            The name of the county.
        feedstock_kg_hr : int
            Dry feedstock of lignocellulose in dry kg/hr.
        ethanol : float
            Annual ethanol in MM gal/year.
        price : float
            Price in $/gal.
        gwp : float
            GWP in lb CO2e/gal.

    Raises
    ------
    TypeError
        If name is not a string.
    TypeError
        If state_data is not a pandas DataFrame.
    ValueError
        If the county name is not in the state data.
    """

    if not isinstance(name, str):
        raise TypeError('County should be a string')
    if not isinstance(state_data, pd.DataFrame):
        raise TypeError('State data should be a pandas DataFrame')

    if name.lower() not in state_data['County'].str.lower().values:
        raise ValueError(f"County '{name}' not found in the state data")

    try:
        name_final = state_data.loc[state_data['County'].str.lower() == name.lower(), 'County'].values[0]
    except IndexError:
        raise ValueError(f"County name '{name}' not found in the dataset.")

    try:
        dry_tonnes = int(state_data.loc[state_data['County'] == name_final, 'Lignocellulose (dry tons)'].values[0])
    except KeyError:
        raise KeyError("Column 'Lignocellulose (dry tons)' not found in the dataset.")
    except ValueError:
        raise ValueError(f"Value in 'Lignocellulose (dry tons)' for county '{name_final}' cannot be converted to an integer.")

    ethanol = float(state_data.loc[state_data['County'] == name_final, 'Annual Ethanol (gal/yr)'].values[0])
    price = float(state_data.loc[state_data['County'] == name_final, 'Price ($/gal)'].values[0])
    gwp = float(state_data.loc[state_data['County'] == name_final, 'GWP (kg CO2e/gal)'].values[0])

    return name_final, dry_tonnes, ethanol, price, gwp
```

- [ ] **Step 3: Create `app/services/fermentation/calc.py`**

```python
"""
Fermentation ethanol-production calculation from biomass feedstock.

Heavy: imports biosteam and the cellulosic-ethanol biorefinery. The
biorefinery is built once per warm container behind a lock, since
biosteam's global bst.settings/flowsheet state isn't concurrency-safe and
FastAPI's thread pool can run handlers concurrently.
"""

import threading
import warnings

warnings.filterwarnings('ignore')

import biosteam as bst
from biorefineries.cellulosic import Biorefinery as CellulosicEthanol
from biorefineries.cornstover import ethanol_density_kggal

GWP_CFs = {
    'cornstover': 0.2,
    'sulfuric_acid': 1,
    'ammonia': 1,
    'cellulase': 1,
    'CSL': 1,
    'caustic': 1,
    'FGD_lime': 1,
}

_br = None
_br_lock = threading.Lock()


def _get_biorefinery():
    """Build (once per warm container) or return the cached CellulosicEthanol biorefinery."""
    global _br
    if _br is not None:
        return _br
    with _br_lock:
        if _br is None:
            _br = CellulosicEthanol(name='ethanol')
        return _br


def fermentation_calc(mass, cornstover_price=0.2, GWP_CFs=GWP_CFs, characterization_factors=(1., 1.,), power_utility_price=0.07):
    """
    Calculate the annual ethanol price and GWP based on the given mass of ethanol produced.

    Parameters
    ----------
    mass : float
        The annual mass of ethanol produced (kg/yr).
    cornstover_price : float
        The price of cornstover (USD/kg).
        Set to default of 0.2
    GWP_CFs : dict
        Global warming potential characterization factors (kg CO2-eq/kg).
    characterization_factors : tuple
        Global warming potential characterization factors for power (consumption, production).
        Set to default value of (1., 1.).
    power_utility_price : float
        Price of power utility (USD/kWh).
        Set to default value of 0.07.

    Returns
    -------
    tuple
        Contains the following:
        - annual ethanol (MM gal/yr)
        - price ($/gal)
        - GWP (lb CO2e/gal)

    Raises
    ------
    TypeError
        If mass is not a number.
    TypeError
        If cornstover_price is not a number.
    TypeError
        If power_utility_price is not a number.
    TypeError
        If GWP_CFs is not a dictionary.
    TypeError
        If characterization_factors is not a tuple.
    """

    if not isinstance(mass, (int, float)):
        raise TypeError('Mass should be a number')
    if not isinstance(cornstover_price, (int, float)):
        raise TypeError('Cornstover price should be a number')
    if not isinstance(power_utility_price, (int, float)):
        raise TypeError('Power utility price should be a number')
    if not isinstance(GWP_CFs, dict):
        raise TypeError('GWP_CFs should be a dictionary')
    if not isinstance(characterization_factors, tuple):
        raise TypeError('Characterization factors should be a tuple')

    br = _get_biorefinery()
    sys = br.sys
    tea = sys.TEA
    f = sys.flowsheet
    stream = f.stream
    feedstock = stream.cornstover
    ethanol = stream.ethanol

    feedstock.F_mass = mass

    prices = {'cornstover': cornstover_price}
    for ID, price in prices.items():
        stream.search(ID).price = price
    bst.PowerUtility.price = power_utility_price

    for ID, CF in GWP_CFs.items():
        stream.search(ID).characterization_factors['GWP'] = CF
    bst.PowerUtility.characterization_factors['GWP'] = characterization_factors

    sys.simulate()

    kg_to_lb_conversion_factor = 2.20462

    get_ethanol = lambda: ethanol.F_mass * ethanol_density_kggal * tea.operating_hours / 1e6
    get_MESP = lambda: tea.solve_price(ethanol) * ethanol_density_kggal
    get_GWP = lambda: (sys.get_net_impact('GWP') / sys.operating_hours / ethanol.F_mass * ethanol_density_kggal) * kg_to_lb_conversion_factor

    return get_ethanol(), get_MESP(), get_GWP()
```

Note: as with `htl.calc`, caching the biorefinery object across calls in the same warm container means the *first* request in a container pays for building `CellulosicEthanol(...)`; subsequent requests reuse it and just re-simulate with new feedstock/price/CF values. This changes nothing about a given request's computed output.

- [ ] **Step 4: Create `app/routers/fermentation_lookup.py`**

```python
"""
Fermentation county-lookup FastAPI router (light — no biosteam/biorefineries).

Endpoints:
- GET /fermentation/county - Get fermentation potential for a specific NJ county
"""

from fastapi import APIRouter, Query, HTTPException

from app.services.fermentation.lookup import fermentation_county

from app.models.fermentation import (
    FermentationCountyResponse,
    FermentationErrorResponse
)

router = APIRouter()


@router.get(
    "/fermentation/county",
    response_model=FermentationCountyResponse,
    responses={
        400: {"model": FermentationErrorResponse, "description": "Bad request"},
        404: {"model": FermentationErrorResponse, "description": "County not found"},
        500: {"model": FermentationErrorResponse, "description": "Internal server error"}
    },
    summary="Get fermentation potential for NJ county",
    description="""
    Calculate ethanol production and related metrics for a given county.
    Takes in a county name and returns:
    1. Mass of the feedstock in kg/hr
    2. Ethanol produced in MM gallons/year
    3. Price of ethanol in $/gallon
    4. Greenhouse gas emissions in lb CO2e/gallon
    """
)
async def fermentation_county_data(
    county_name: str = Query(
        ...,
        description="Name of the New Jersey county",
        openapi_examples={"default": {"value": "Atlantic"}}
    )
) -> FermentationCountyResponse:
    try:
        name, mass, ethanol, price, gwp = fermentation_county(county_name)

        return FermentationCountyResponse(
            county_name=name,
            mass=mass,
            ethanol=ethanol,
            price=price,
            gwp=gwp
        )

    except ValueError:
        raise HTTPException(
            status_code=404,
            detail=f"County '{county_name}' not found. Valid counties are the 21 NJ counties (e.g. Essex, Atlantic, Bergen)."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

- [ ] **Step 5: Create `app/routers/fermentation_calc.py`**

```python
"""
Fermentation ethanol-production FastAPI router (heavy — imports biosteam
and the cellulosic biorefinery).

Endpoints:
- GET /fermentation/calc - Calculate ethanol production from biomass
"""

from fastapi import APIRouter, Query, HTTPException

from app.services.fermentation.calc import fermentation_calc
from app.services.fermentation.lookup import fermentation_convert_feedstock_kg_hr as fermentation_kg

from app.models.fermentation import (
    FermentationCalcResponse,
    FermentationUnit,
    FermentationErrorResponse
)

router = APIRouter()


@router.get(
    "/fermentation/calc",
    response_model=FermentationCalcResponse,
    responses={
        400: {"model": FermentationErrorResponse, "description": "Bad request"},
        422: {"model": FermentationErrorResponse, "description": "Invalid unit"},
        500: {"model": FermentationErrorResponse, "description": "Internal server error"}
    },
    summary="Calculate ethanol production from biomass",
    description="""
    Convert mass input to ethanol production and related metrics.
    Takes in a mass of feed stock, a unit of that mass and returns:
    1. Mass of the feedstock in kg/hr
    2. Ethanol produced in MM gallons/year
    3. Price of ethanol in $/gallon
    4. Greenhouse gas emissions in lb CO2e/gallon
    """
)
async def fermentation_calc_data(
    mass: float = Query(
        ...,
        gt=0,
        description="Mass of the feedstock",
        openapi_examples={"default": {"value": 100.0}}
    ),
    unit: FermentationUnit = Query(
        FermentationUnit.KGHR,
        description="Unit of the mass",
        openapi_examples={"default": {"value": "kghr"}}
    )
) -> FermentationCalcResponse:
    try:
        kg_hr = fermentation_kg(mass, unit.value)
        ethanol, price, gwp = fermentation_calc(kg_hr)

        return FermentationCalcResponse(
            mass=kg_hr,
            ethanol=ethanol,
            price=price,
            gwp=gwp
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

- [ ] **Step 6: Update `tests/test_fermentation.py`'s import and patch targets**

Replace the fixture in `TestFermentationConversion.setup`:

```python
    @pytest.fixture(autouse=True)
    def setup(self):
        from app.services.fermentation.lookup import fermentation_convert_feedstock_kg_hr
        self.convert = fermentation_convert_feedstock_kg_hr
```

Replace every `patch("app.routers.fermentation.fermentation_kg", ...)` and `patch("app.routers.fermentation.fermentation_calc", ...)` with `patch("app.routers.fermentation_calc.fermentation_kg", ...)` / `patch("app.routers.fermentation_calc.fermentation_calc", ...)` (in `TestFermentationCalcEndpoint`).

Replace every `patch("app.routers.fermentation.fermentation_county", ...)` with `patch("app.routers.fermentation_lookup.fermentation_county", ...)` (in `TestFermentationCountyEndpoint`).

- [ ] **Step 7: Delete the old files**

```bash
git rm app/services/fermentation_service.py app/routers/fermentation.py
```

- [ ] **Step 8: Sanity-check the calc function directly**

Run: `uv run python -c "from app.services.fermentation.calc import fermentation_calc; print(fermentation_calc(100))"`
Expected: prints a `(ethanol, price, gwp)` tuple close to the original recorded value `(0.0, 0.0, 0.0)` for `fermentation_calc(100)`.

(Full `tests/test_fermentation.py` suite runs after Task 6 — same ordering note as Tasks 1/3.)

- [ ] **Step 9: Commit**

```bash
git add app/services/fermentation app/routers/fermentation_lookup.py app/routers/fermentation_calc.py tests/test_fermentation.py
git commit -m "Split fermentation service/router into lookup (light) and calc (heavy, cached biorefinery)"
```

---

### Task 5: Light-safe `/ready` health check

**Files:**
- Modify: `app/routers/health.py`

**Interfaces:**
- No change to `HealthResponse`/`ReadinessResponse`/`MetricsResponse` shapes — only `check_dependencies()`'s internals change.

`check_dependencies()` currently does `import biosteam` and `from app.services import htl_service` / `combustion_service` / `fermentation_service` unconditionally — those modules and that heavy dependency won't exist in the `light-api` Lambda image at all, so this needs to check what's actually relevant to whichever function is running.

- [ ] **Step 1: Replace `check_dependencies()` in `app/routers/health.py`**

```python
def check_dependencies() -> Dict[str, str]:
    """Check if critical dependencies are available.

    Only checks what every deployment (light or heavy) actually has:
    fastapi/pandas (always present) and the data CSVs. Does not probe for
    biosteam/exposan/biorefineries — those are only installed in the heavy
    *-calc Lambda functions, not in light-api, so an unconditional import
    here would make light-api's own /ready endpoint report a false failure.
    """
    dependencies = {}

    try:
        import pandas
        dependencies["pandas"] = "OK"
    except ImportError:
        dependencies["pandas"] = "FAILED"

    try:
        import numpy
        dependencies["numpy"] = "OK"
    except ImportError:
        dependencies["numpy"] = "FAILED"

    for name, rel_path in (
        ("htl_data", os.path.join("htl", "htl_data.csv")),
        ("combustion_data", os.path.join("combustion", "combustion_data.csv")),
        ("fermentation_data", os.path.join("fermentation", "fermentation_data.csv")),
    ):
        try:
            data_path = os.path.join(os.path.dirname(__file__), "..", "data", rel_path)
            dependencies[name] = "OK" if os.path.exists(data_path) else "MISSING"
        except Exception:
            dependencies[name] = "ERROR"

    return dependencies
```

Delete the old function body's `biosteam`/`htl_service`/`combustion_service`/`fermentation_service` import-check blocks — they're replaced by the pandas/numpy checks and the three CSV-existence checks above (the CSV paths were previously nested one level shallower per-service; the new checks above use the same three-file set but don't require importing any service module to find them).

- [ ] **Step 2: Run the health tests**

Run: `uv run python -c "
from fastapi.testclient import TestClient
from app.main import app
c = TestClient(app)
r = c.get('/ready')
print(r.status_code, r.json())
"`
Expected: `200` with `dependencies` showing `pandas: OK`, `numpy: OK`, and all three `*_data: OK`.

- [ ] **Step 3: Commit**

```bash
git add app/routers/health.py
git commit -m "Make /ready health check light-safe (no biosteam/service imports)"
```

---

### Task 6: Shared app factory + rewire `app/main.py`

**Files:**
- Create: `app/app_factory.py`
- Modify: `app/main.py`

**Interfaces:**
- Produces: `app.app_factory.create_app() -> fastapi.FastAPI` (middleware + CORS + exception handlers pre-registered, no routers). `app.app_factory.ALLOWED_ORIGINS` (moved from `app/main.py`, re-exported there for `tests/test_cors.py`'s `from app.main import ALLOWED_ORIGINS`).

- [ ] **Step 1: Create `app/app_factory.py`**

```python
"""
Shared FastAPI app construction: middleware, CORS, and error handlers.

Used by app/main.py (the "everything" local-dev entrypoint) and by each of
the four app/entrypoints/*.py Lambda entrypoints, so all four deployables
get identical error-handling/CORS/security behavior without duplicating it
four times. Callers register their own routers after calling create_app().
"""

import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.middleware import (
    ErrorHandlerMiddleware,
    PerformanceMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware
)

# env-driven allowlist, default-closed to the known frontends.
# Set ALLOWED_ORIGINS (comma-separated) in production to override the default.
# NOTE: "*" + allow_credentials=True is rejected by browsers, so origins are explicit.
_DEFAULT_ALLOWED_ORIGINS = (
    "https://nj-bioenergy.apps.qsdsan.com,"  # group-owned frontend
    "http://localhost:8000,http://localhost:3000"  # local dev
)
ALLOWED_ORIGINS = [
    o.strip()
    for o in os.getenv("ALLOWED_ORIGINS", _DEFAULT_ALLOWED_ORIGINS).split(",")
    if o.strip()
]


def create_app(title: str = "Waste-to-Energy Processing API") -> FastAPI:
    app = FastAPI(
        title=title,
        description="High-performance API for waste-to-energy calculations",
        version="2.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json"
    )

    # Order matters - last added runs first.
    app.add_middleware(ErrorHandlerMiddleware)
    app.add_middleware(PerformanceMiddleware, slow_request_threshold=0.5)
    app.add_middleware(RateLimitMiddleware, requests_per_minute=30, requests_per_hour=500)
    app.add_middleware(SecurityHeadersMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request, exc: RequestValidationError):
        messages = []
        for error in exc.errors():
            field = error["loc"][-1] if error["loc"] else "field"
            input_val = error.get("input", "")
            error_type = error.get("type", "")

            if error_type == "missing":
                messages.append(f"Missing required parameter: '{field}'")
            elif error_type == "enum":
                expected = error.get("ctx", {}).get("expected", "")
                messages.append(f"Invalid {field} '{input_val}'. Valid options: {expected}")
            elif error_type in ("greater_than", "greater_than_equal"):
                messages.append(f"'{field}' must be a positive number (got {input_val})")
            elif error_type in ("float_parsing", "int_parsing"):
                messages.append(f"'{field}' must be a number (got '{input_val}')")
            else:
                messages.append(f"Invalid '{field}': {error.get('msg', error_type)}")

        return JSONResponse(
            status_code=422,
            content={"error": messages[0] if len(messages) == 1 else messages}
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request, exc: HTTPException):
        return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})

    @app.exception_handler(500)
    async def internal_error_handler(request, exc):
        return JSONResponse(status_code=500, content={"error": "Internal server error"})

    return app
```

- [ ] **Step 2: Rewrite `app/main.py`**

```python
"""
FastAPI Application Entry Point (local-dev / "everything" entrypoint).

Registers all six routers (three light lookup + three heavy calc + health)
in a single app, for local development (`uv run uvicorn app.main:app`) and
for the test suite's TestClient. Lambda deployments use the four separate
entrypoints in app/entrypoints/ instead — see guides/lambda-restructure-design.md.
"""

import uvicorn

from app.app_factory import create_app, ALLOWED_ORIGINS  # noqa: F401 (ALLOWED_ORIGINS re-exported for tests/test_cors.py)
from app.routers import (
    health,
    htl_lookup, htl_calc,
    combustion_lookup, combustion_calc,
    fermentation_lookup, fermentation_calc,
)

app = create_app()

app.include_router(htl_calc.router, prefix="/api/v1", tags=["HTL"])
app.include_router(htl_lookup.router, prefix="/api/v1", tags=["HTL"])
app.include_router(combustion_calc.router, prefix="/api/v1", tags=["Combustion"])
app.include_router(combustion_lookup.router, prefix="/api/v1", tags=["Combustion"])
app.include_router(fermentation_calc.router, prefix="/api/v1", tags=["Fermentation"])
app.include_router(fermentation_lookup.router, prefix="/api/v1", tags=["Fermentation"])
app.include_router(health.router, tags=["Health"])


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Waste-to-Energy Processing API",
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/health",
        "api_version": "v1",
        "base_url": "/api/v1",
        "endpoints": {
            "htl": "/api/v1/htl/",
            "combustion": "/api/v1/combustion/",
            "fermentation": "/api/v1/fermentation/"
        },
        "monitoring": {
            "health": "/health",
            "readiness": "/ready",
            "metrics": "/metrics",
            "performance": "/performance"
        }
    }


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=5000,
        reload=True,
        log_level="info"
    )
```

- [ ] **Step 3: Run the full test suite**

Run: `uv run pytest -v`
Expected: all tests pass — this is the first point since Task 1 where the full suite can run end-to-end, since `app/main.py` now imports the new split routers instead of the deleted monolithic ones.

- [ ] **Step 4: Commit**

```bash
git add app/app_factory.py app/main.py
git commit -m "Add shared app_factory, rewire app/main.py to the split routers"
```

---

### Task 7: Four Lambda entrypoint modules

**Files:**
- Create: `app/entrypoints/__init__.py`, `app/entrypoints/light_app.py`, `app/entrypoints/htl_app.py`, `app/entrypoints/combustion_app.py`, `app/entrypoints/fermentation_app.py`

**Interfaces:**
- Consumes: `app.app_factory.create_app()` (Task 6).
- Produces: `app.entrypoints.light_app.app`, `app.entrypoints.htl_app.app`, `app.entrypoints.combustion_app.app`, `app.entrypoints.fermentation_app.app` — each a `fastapi.FastAPI` instance, the ASGI target each Dockerfile's `CMD` points uvicorn at.

- [ ] **Step 1: Create `app/entrypoints/__init__.py`**

```python
```
(empty — makes `app/entrypoints` a package)

- [ ] **Step 2: Create `app/entrypoints/light_app.py`**

```python
"""
Lambda entrypoint: health + all three county-lookup endpoints.

No biosteam/exposan/biorefineries in this deployable's dependency set at
all — see Dockerfile.lambda.light.
"""

from app.app_factory import create_app
from app.routers import health, htl_lookup, combustion_lookup, fermentation_lookup

app = create_app()

app.include_router(htl_lookup.router, prefix="/api/v1", tags=["HTL"])
app.include_router(combustion_lookup.router, prefix="/api/v1", tags=["Combustion"])
app.include_router(fermentation_lookup.router, prefix="/api/v1", tags=["Fermentation"])
app.include_router(health.router, tags=["Health"])
```

- [ ] **Step 3: Create `app/entrypoints/htl_app.py`**

```python
"""
Lambda entrypoint: HTL calc only. Imports exposan.htl/chaospy.
"""

from app.app_factory import create_app
from app.routers import htl_calc

app = create_app()

app.include_router(htl_calc.router, prefix="/api/v1", tags=["HTL"])
```

- [ ] **Step 4: Create `app/entrypoints/combustion_app.py`**

```python
"""
Lambda entrypoint: combustion calc only. Imports biosteam/thermosteam only
(no exposan, no biorefineries — see app/services/combustion/_chemicals.py).
"""

from app.app_factory import create_app
from app.routers import combustion_calc

app = create_app()

app.include_router(combustion_calc.router, prefix="/api/v1", tags=["Combustion"])
```

- [ ] **Step 5: Create `app/entrypoints/fermentation_app.py`**

```python
"""
Lambda entrypoint: fermentation calc only. Imports biosteam and the
cellulosic-ethanol biorefinery.
"""

from app.app_factory import create_app
from app.routers import fermentation_calc

app = create_app()

app.include_router(fermentation_calc.router, prefix="/api/v1", tags=["Fermentation"])
```

- [ ] **Step 6: Smoke-test each entrypoint imports and serves its own routes only**

Run: `uv run python -c "
from fastapi.testclient import TestClient
from app.entrypoints.light_app import app as light_app
c = TestClient(light_app)
print('light /health:', c.get('/health').status_code)
print('light /htl/county:', c.get('/api/v1/htl/county?county_name=Atlantic').status_code)
print('light /htl/calc (should 404, not registered here):', c.get('/api/v1/htl/calc?sludge=100').status_code)
"`
Expected: `200`, `200`, `404` — confirming `light_app` genuinely doesn't serve `/htl/calc`.

- [ ] **Step 7: Commit**

```bash
git add app/entrypoints
git commit -m "Add four Lambda entrypoint modules (light + htl/combustion/fermentation calc)"
```

---

### Task 8: Four Lambda Dockerfiles

**Files:**
- Create: `Dockerfile.lambda.light`, `Dockerfile.lambda.htl`, `Dockerfile.lambda.combustion`, `Dockerfile.lambda.fermentation`
- Delete: `Dockerfile.lambda`

Each Dockerfile is self-contained (the ~15-line builder stage is duplicated across the four rather than shared via a build ARG, since Lambda's `CMD` must be a fixed exec-form array — parameterizing it would need an extra shell wrapper for no real benefit at only 4 files).

- [ ] **Step 1: Create `Dockerfile.lambda.light`**

```dockerfile
# Lambda container image for the light function: health + all three
# *_county lookup endpoints. No biosteam/exposan/biorefineries installed —
# see app/entrypoints/light_app.py.

FROM python:3.10-slim AS builder

RUN apt-get update && apt-get install -y gcc g++ gfortran git

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-cache

FROM python:3.10-slim AS runtime

RUN apt-get update && apt-get install -y libopenblas0 liblapack3 && rm -rf /var/lib/apt/lists/*

COPY --from=public.ecr.aws/awsguru/aws-lambda-adapter:0.9.1 /lambda-adapter /opt/extensions/lambda-adapter
ENV AWS_LWA_PORT=5000
ENV AWS_LWA_READINESS_CHECK_PATH=/health

ENV HOME=/tmp
ENV XDG_CACHE_HOME=/tmp/.cache

COPY --from=builder /app/.venv /app/.venv

WORKDIR /app

COPY . .

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app"

CMD ["uvicorn", "app.entrypoints.light_app:app", "--host", "0.0.0.0", "--port", "5000"]
```

- [ ] **Step 2: Create `Dockerfile.lambda.htl`**

```dockerfile
# Lambda container image for the htl-calc function: /htl/calc only.
# Imports exposan.htl + chaospy.

FROM python:3.10-slim AS builder

RUN apt-get update && apt-get install -y gcc g++ gfortran git

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-cache

FROM python:3.10-slim AS runtime

RUN apt-get update && apt-get install -y libopenblas0 liblapack3 && rm -rf /var/lib/apt/lists/*

COPY --from=public.ecr.aws/awsguru/aws-lambda-adapter:0.9.1 /lambda-adapter /opt/extensions/lambda-adapter
ENV AWS_LWA_PORT=5000
ENV AWS_LWA_READINESS_CHECK_PATH=/health

ENV HOME=/tmp
ENV XDG_CACHE_HOME=/tmp/.cache
ENV MPLCONFIGDIR=/tmp/matplotlib
ENV NUMBA_CACHE_DIR=/tmp/numba_cache

COPY --from=builder /app/.venv /app/.venv

# exposan.htl creates its own "results" output directory at import time
# (exposan/utils.py:_init_modules, called from exposan/htl/__init__.py),
# unconditionally. "data" ships with the package so that half of the check
# passes; "results" does not, so the bare os.mkdir() call crashes Lambda's
# read-only filesystem before the app can even start. Pre-create it here,
# in the writable build stage, so the runtime's os.path.isdir() check finds
# it already there and skips the mkdir. (A small upstream EXPOsan PR to
# wrap that os.mkdir() in a try/except is tracked separately — see
# guides/lambda-restructure-design.md — but isn't required for this to work.)
RUN mkdir -p /app/.venv/lib/python3.10/site-packages/exposan/htl/results

WORKDIR /app

COPY . .

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app"

CMD ["uvicorn", "app.entrypoints.htl_app:app", "--host", "0.0.0.0", "--port", "5000"]
```

- [ ] **Step 3: Create `Dockerfile.lambda.combustion`**

```dockerfile
# Lambda container image for the combustion-calc function:
# /combustion/calc only. Imports biosteam/thermosteam only.

FROM python:3.10-slim AS builder

RUN apt-get update && apt-get install -y gcc g++ gfortran git

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-cache

FROM python:3.10-slim AS runtime

RUN apt-get update && apt-get install -y libopenblas0 liblapack3 && rm -rf /var/lib/apt/lists/*

COPY --from=public.ecr.aws/awsguru/aws-lambda-adapter:0.9.1 /lambda-adapter /opt/extensions/lambda-adapter
ENV AWS_LWA_PORT=5000
ENV AWS_LWA_READINESS_CHECK_PATH=/health

ENV HOME=/tmp
ENV XDG_CACHE_HOME=/tmp/.cache
ENV MPLCONFIGDIR=/tmp/matplotlib
ENV NUMBA_CACHE_DIR=/tmp/numba_cache

COPY --from=builder /app/.venv /app/.venv

WORKDIR /app

COPY . .

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app"

CMD ["uvicorn", "app.entrypoints.combustion_app:app", "--host", "0.0.0.0", "--port", "5000"]
```

- [ ] **Step 4: Create `Dockerfile.lambda.fermentation`**

```dockerfile
# Lambda container image for the fermentation-calc function:
# /fermentation/calc only. Imports biosteam + biorefineries.cellulosic/cornstover.

FROM python:3.10-slim AS builder

RUN apt-get update && apt-get install -y gcc g++ gfortran git

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-cache

FROM python:3.10-slim AS runtime

RUN apt-get update && apt-get install -y libopenblas0 liblapack3 && rm -rf /var/lib/apt/lists/*

COPY --from=public.ecr.aws/awsguru/aws-lambda-adapter:0.9.1 /lambda-adapter /opt/extensions/lambda-adapter
ENV AWS_LWA_PORT=5000
ENV AWS_LWA_READINESS_CHECK_PATH=/health

ENV HOME=/tmp
ENV XDG_CACHE_HOME=/tmp/.cache
ENV MPLCONFIGDIR=/tmp/matplotlib
ENV NUMBA_CACHE_DIR=/tmp/numba_cache

COPY --from=builder /app/.venv /app/.venv

WORKDIR /app

COPY . .

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app"

CMD ["uvicorn", "app.entrypoints.fermentation_app:app", "--host", "0.0.0.0", "--port", "5000"]
```

- [ ] **Step 5: Delete the old single Dockerfile**

```bash
git rm Dockerfile.lambda
```

- [ ] **Step 6: Commit**

```bash
git add Dockerfile.lambda.light Dockerfile.lambda.htl Dockerfile.lambda.combustion Dockerfile.lambda.fermentation
git commit -m "Replace single Dockerfile.lambda with four per-function Dockerfiles"
```

(Actual `docker build` smoke tests of these four happen in Task 9's CI workflow — no local Docker is available to test them directly here.)

---

### Task 9: CI workflow for four images

**Files:**
- Modify: `.github/workflows/build-and-push-lambda.yml`

**Interfaces:**
- Produces: four ECR images in the existing `nj-bioenergy-api` repo, tagged `light-latest`/`light-<sha>`, `htl-latest`/`htl-<sha>`, `combustion-latest`/`combustion-<sha>`, `fermentation-latest`/`fermentation-<sha>`.

- [ ] **Step 1: Rewrite the workflow to build/smoke-test/push a matrix of four images**

```yaml
name: Build, smoke-test, and push Lambda images to ECR

# Manual-dispatch only, on purpose: the four Lambda functions don't exist
# yet (created by hand per guides/lambda-restructure-plan.md's AWS
# runbook tasks), and this shouldn't run automatically on every push to
# main until the Lambda path has been cut over to in production. Once
# that's done, this can be folded into the normal push-triggered pipeline
# like build-and-push-ecr.yml.
#
# Runs on GitHub's hosted runner (which already has Docker) instead of
# requiring a local Docker install, and smoke-tests each image (health
# check + one real request against that function's own heavy endpoint,
# where it has one) before ever pushing to ECR.
#
# This does NOT validate the AWS Lambda Web Adapter's extension-proxy
# behavior: the standalone Lambda Runtime Interface Emulator does not
# support Lambda Extensions, so that path can only be exercised on real
# Lambda (see the AWS runbook's function-creation test-event steps).

on:
  workflow_dispatch: {}

permissions:
  id-token: write
  contents: read

env:
  AWS_REGION: us-east-2
  ECR_REPOSITORY: nj-bioenergy-api

jobs:
  build-smoketest-and-push:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        include:
          - name: light
            dockerfile: Dockerfile.lambda.light
            smoke_path: /api/v1/htl/county?county_name=Atlantic
          - name: htl
            dockerfile: Dockerfile.lambda.htl
            smoke_path: /api/v1/htl/calc?sludge=150
          - name: combustion
            dockerfile: Dockerfile.lambda.combustion
            smoke_path: /api/v1/combustion/calc?mass=1000&waste_type=sludge
          - name: fermentation
            dockerfile: Dockerfile.lambda.fermentation
            smoke_path: /api/v1/fermentation/calc?mass=100
    steps:
      - name: Check out the repo
        uses: actions/checkout@v7

      - name: Build ${{ matrix.name }} image
        run: docker build -f "${{ matrix.dockerfile }}" -t "nj-bioenergy-api:${{ matrix.name }}-smoketest" .

      - name: Smoke test ${{ matrix.name }} - health + one real request
        run: |
          docker run -d --rm -p 5000:5000 --name "${{ matrix.name }}-smoketest-app" "nj-bioenergy-api:${{ matrix.name }}-smoketest"

          echo "Waiting for /health to respond..."
          healthy=""
          for i in $(seq 1 60); do
            if curl -sf http://localhost:5000/health > /dev/null; then
              healthy="1"
              echo "Healthy after $((i * 10))s"
              break
            fi
            sleep 10
          done
          if [ -z "$healthy" ]; then
            echo "App never became healthy within 600s"
            docker logs "${{ matrix.name }}-smoketest-app"
            exit 1
          fi

          echo "Checking ${{ matrix.smoke_path }}..."
          http_code=$(curl -s -o /tmp/response.json -w "%{http_code}" "http://localhost:5000${{ matrix.smoke_path }}")
          cat /tmp/response.json
          if [ "$http_code" != "200" ]; then
            echo "${{ matrix.smoke_path }} returned $http_code"
            docker logs "${{ matrix.name }}-smoketest-app"
            exit 1
          fi

          docker stop "${{ matrix.name }}-smoketest-app"

      - name: Configure AWS credentials (OIDC, no stored keys)
        uses: aws-actions/configure-aws-credentials@v6
        with:
          role-to-assume: ${{ secrets.AWS_GHA_ROLE_ARN }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Log in to Amazon ECR
        id: ecr
        uses: aws-actions/amazon-ecr-login@v2

      - name: Tag and push ${{ matrix.name }} image
        env:
          REGISTRY: ${{ steps.ecr.outputs.registry }}
        run: |
          IMAGE="$REGISTRY/$ECR_REPOSITORY"
          docker tag "nj-bioenergy-api:${{ matrix.name }}-smoketest" "$IMAGE:${{ matrix.name }}-${{ github.sha }}"
          docker tag "nj-bioenergy-api:${{ matrix.name }}-smoketest" "$IMAGE:${{ matrix.name }}-latest"
          docker push "$IMAGE:${{ matrix.name }}-${{ github.sha }}"
          docker push "$IMAGE:${{ matrix.name }}-latest"
          echo "Pushed $IMAGE:${{ matrix.name }}-latest and :${{ matrix.name }}-${{ github.sha }}"
```

Note: the deploy step (`aws lambda update-function-code`) is deliberately not added yet — it needs each function's exact name, which only exists after Task 11 (AWS runbook) creates them. Add it then, one `aws lambda update-function-code --function-name <name> --image-uri ...` line per matrix entry, matching the pattern from the original single-function plan's Task 6.

- [ ] **Step 2: Commit and push**

```bash
git add .github/workflows/build-and-push-lambda.yml
git commit -m "Extend Lambda CI workflow to build/smoke-test/push all four function images"
git push
```

- [ ] **Step 3: Run it once by hand and confirm all four images land in ECR**

GitHub Actions tab → "Build, smoke-test, and push Lambda images to ECR" → Run workflow → `main`.

Expected: 4 green matrix jobs (check each job's smoke-test log line for its cold-start duration — note all four, since they inform each function's memory/timeout starting values in Task 11). Then:

```bash
aws ecr describe-images --repository-name nj-bioenergy-api --region us-east-2 \
  --query "imageDetails[?contains(imageTags, 'light-latest') || contains(imageTags, 'htl-latest') || contains(imageTags, 'combustion-latest') || contains(imageTags, 'fermentation-latest')]"
```

Expected: four image entries, one per tag family.

---

### Task 10: Documentation cleanup

**Files:**
- Modify: `CLAUDE.md`

**Interfaces:** none.

- [ ] **Step 1: Replace the stale "Architecture: Dual-App Migration State" section**

`CLAUDE.md` currently describes a Flask legacy app (`wsgi.py`, `app/blueprints/`) that no longer exists in this repo. Replace that section with:

```markdown
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
```

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "Update CLAUDE.md to describe the split light/heavy, four-entrypoint architecture"
```

---

### Task 11 (AWS runbook — human-executed): Create four Lambda functions

**Files:** none (AWS console/CLI)

> Sign in as `yalin-admin` (management account) → Switch Role → `qsdsan-app` (476663692697) → role `OrganizationAccountAccessRole`, region **us-east-2** (per `deployments/qsdsan.md`). The Lambda function, ECR images, and IAM execution role from the prior single-function attempt are still sitting idle in this account (see `[[project_lambda_migration]]` memory) — they can be deleted once the four new functions are confirmed working, or left alone in the meantime since idle Lambda functions cost nothing.

- [ ] **Step 1: Reuse or recreate the IAM execution role**

Console: IAM → Roles → confirm `nj-bioenergy-api-lambda-execution` still exists (from the prior attempt) with `AWSLambdaBasicExecutionRole` attached. If not, recreate it: Create role → AWS service → Lambda → attach `AWSLambdaBasicExecutionRole` → name `nj-bioenergy-api-lambda-execution`. All four functions share this one role — none of them talk to a VPC or any other AWS service beyond CloudWatch Logs.

- [ ] **Step 2: Create the four functions from their ECR images**

Console: Lambda → Create function → "Container image", once per function:

| Function name | ECR image tag |
|---|---|
| `nj-bioenergy-light` | `nj-bioenergy-api:light-latest` |
| `nj-bioenergy-htl` | `nj-bioenergy-api:htl-latest` |
| `nj-bioenergy-combustion` | `nj-bioenergy-api:combustion-latest` |
| `nj-bioenergy-fermentation` | `nj-bioenergy-api:fermentation-latest` |

Architecture `x86_64`, execution role `nj-bioenergy-api-lambda-execution` for all four.

- [ ] **Step 3: Set memory/timeout/ephemeral storage per function**

`nj-bioenergy-light`: Memory **512 MB**, Timeout **30 seconds**, ephemeral storage default (512 MB). This function never imports biosteam/exposan — pandas/CSV lookups and a health check should be fast even cold.

`nj-bioenergy-htl`, `nj-bioenergy-combustion`, `nj-bioenergy-fermentation`: start at the same values the prior single-function attempt landed on — Memory **3008 MB** (the us-east-2 account/region Service Quota ceiling at the time; check whether a quota increase has since been requested/approved and raise if so), Timeout **120 seconds**, ephemeral storage **1024 MB**. Adjust each independently after Step 4's real cold-start numbers come in — they no longer have to share one setting.

- [ ] **Step 4: Smoke-test each function directly (bypassing everything else)**

For `nj-bioenergy-light`, Test tab, HTTP-proxy-shaped test event:

```json
{
  "version": "2.0",
  "routeKey": "$default",
  "rawPath": "/health",
  "requestContext": { "http": { "method": "GET", "path": "/health" } },
  "headers": {}
}
```

Expected: `"statusCode": 200`.

For each of `nj-bioenergy-htl`/`nj-bioenergy-combustion`/`nj-bioenergy-fermentation`, a test event hitting that function's own heavy endpoint — e.g. for `nj-bioenergy-htl`:

```json
{
  "version": "2.0",
  "routeKey": "$default",
  "rawPath": "/api/v1/htl/calc",
  "rawQueryString": "sludge=150",
  "queryStringParameters": { "sludge": "150" },
  "requestContext": { "http": { "method": "GET", "path": "/api/v1/htl/calc" } },
  "headers": {}
}
```

(swap the path/query for `/api/v1/combustion/calc?mass=1000&waste_type=sludge` and `/api/v1/fermentation/calc?mass=100` for the other two). Expected: `"statusCode": 200` with the calculated fields in the body. Note each function's `Duration`/`Max Memory Used` — that's what should actually inform further memory/timeout tuning per function, not the health-only reading.

- [ ] **Step 5: Invoke each function a second time and confirm the warm-container caching works**

Immediately re-run the same heavy test event from Step 4 against each `*-calc` function. Expected: a visibly shorter `Duration` than the first (cold) invocation — this is the model/biorefinery caching from Tasks 1/3/4 paying off (the container reused the already-built model instead of rebuilding it).

---

### Task 12 (AWS runbook — human-executed): Function URLs

**Files:** none (AWS console/CLI)

- [ ] **Step 1: Create a Function URL for each of the four functions**

Console: each function → Configuration → Function URL → Create function URL.
- Auth type: **NONE** (matches the current public-API behavior; the app's own CORS allowlist and rate-limiting middleware are the actual access controls).
- CORS: mirror `_DEFAULT_ALLOWED_ORIGINS` in `app/app_factory.py` — allow origin `https://nj-bioenergy.apps.qsdsan.com`, methods `*`, headers `*`. Defense-in-depth alongside the app's own `CORSMiddleware`.

- [ ] **Step 2: Test each Function URL directly, before touching CloudFront**

```bash
curl -s "https://<light-function-url-id>.lambda-url.us-east-2.on.aws/health"
curl -s "https://<light-function-url-id>.lambda-url.us-east-2.on.aws/api/v1/htl/county?county_name=Atlantic"
curl -s "https://<htl-function-url-id>.lambda-url.us-east-2.on.aws/api/v1/htl/calc?sludge=150"
curl -s "https://<combustion-function-url-id>.lambda-url.us-east-2.on.aws/api/v1/combustion/calc?mass=1000&waste_type=sludge"
curl -s "https://<fermentation-function-url-id>.lambda-url.us-east-2.on.aws/api/v1/fermentation/calc?mass=100"
```

Expected: same responses as Task 11 Step 4/5's console tests. Time each call under real HTTP — this is the clearest signal yet for whether Task 11 Step 3's memory/timeout values need further adjustment before going anywhere near the custom domain.

---

### Task 13 (AWS runbook — human-executed): CloudFront path-pattern cutover

**Files:** none (AWS console/CLI)

- [ ] **Step 1: Record current state for rollback**

Console: CloudFront → distribution `d3t3sqyyjalry1.cloudfront.net` → Origins tab → note the current origin (from the prior ECS attempt, if still configured, or whatever origin is currently live) and its cache/origin-request policy names (`CachingDisabled` / `AllViewerExceptHostHeader` per `deployments/qsdsan.md`).

- [ ] **Step 2: Add four origins**

Origins tab → Create origin, once per Function URL, using each Function URL's hostname (no `https://` prefix, no path) as "Origin domain", protocol HTTPS-only.

- [ ] **Step 3: Add four path-pattern behaviors, most-specific first**

CloudFront evaluates behaviors in order and uses the first match, so the two `*_calc`-shaped patterns must come before the catch-all:

| Path pattern | Origin |
|---|---|
| `/api/v1/htl/calc*` | htl Function URL origin |
| `/api/v1/combustion/calc*` | combustion Function URL origin |
| `/api/v1/fermentation/calc*` | fermentation Function URL origin |
| `Default (*)` | light Function URL origin |

Keep the same cache/origin-request policies (`CachingDisabled` / `AllViewerExceptHostHeader`) on all four behaviors — these are dynamic API responses, not cacheable static content. Save.

- [ ] **Step 4: Verify end-to-end via the real custom domain**

```bash
curl -s https://nj-bioenergy-api.apps.qsdsan.com/health
curl -s "https://nj-bioenergy-api.apps.qsdsan.com/api/v1/htl/county?county_name=Atlantic"
curl -s "https://nj-bioenergy-api.apps.qsdsan.com/api/v1/htl/calc?sludge=150"
curl -s "https://nj-bioenergy-api.apps.qsdsan.com/api/v1/combustion/calc?mass=1000&waste_type=sludge"
curl -s "https://nj-bioenergy-api.apps.qsdsan.com/api/v1/fermentation/calc?mass=100"
```

Run each 5-10 times in a row, not just once, to see both cold and warm responses. Confirm the frontend (`nj-bioenergy.apps.qsdsan.com`) still works end-to-end in a browser, including a real calculation of each type through the UI.

---

### Task 14 (AWS runbook — human-executed): Burn-in and cleanup

**Files:**
- Modify: `deployments/qsdsan.md` (separate repo)
- Modify: `QSDsan/docs/source/app/index.rst` (restore the "Launch the app" button, removing the "temporarily unavailable" note added when the ECS backend was decommissioned — see `[[project_lambda_migration]]`)

- [ ] **Step 1: Watch CloudWatch Logs/metrics for all four functions for a few days**

Console: CloudWatch → Log groups → `/aws/lambda/nj-bioenergy-light`, `/aws/lambda/nj-bioenergy-htl`, `/aws/lambda/nj-bioenergy-combustion`, `/aws/lambda/nj-bioenergy-fermentation`. Watch for errors; check each function's own Duration/Errors/Throttles metrics.

- [ ] **Step 2: Clean up the prior single-function attempt**

Once the four new functions are confirmed stable: delete the old single Lambda function, its Function URL (if one was ever created), and the now-unused `lambda-*`-tagged ECR images from the prior attempt (`nj-bioenergy-api:lambda-latest` etc.) — keep the new `light-*`/`htl-*`/`combustion-*`/`fermentation-*` tags.

- [ ] **Step 3: Restore the frontend's "Launch the app" link**

In the `QSDsan` repo, `docs/source/app/index.rst`: remove the `alert alert-info` "temporarily unavailable" note and restore the original "Launch the app" button, now that the backend is live again.

- [ ] **Step 4: Update the deployment inventory**

Edit `deployments/qsdsan.md`'s "Backend (API)" section to describe the four-Lambda-function + CloudFront-path-routing setup, replacing whatever it currently says (ECS Express Mode, or "offline" if it was updated when the backend was decommissioned). Add a line to its rotation/change log noting the cutover date.

---

## Self-Review Notes

- **Spec coverage:** every section of `guides/lambda-restructure-design.md` maps to a task — 4-function architecture (Tasks 7-9, 11-13), module layout (Tasks 1, 3, 4), combustion dependency reduction (Task 2/3), model caching (Tasks 1, 3, 4), verification approach (parity test in Task 2, direct output checks in Tasks 1/3/4, full suite in Task 6), CI/Docker strategy (Tasks 8-9), operational constraints (respected throughout — no AWS/Docker steps executed by the assistant, every commit is its own step for approval), small bundled fixes (Task 10; the stale exposan-pin comment is naturally dropped since Tasks 1/3/4 rewrite those files from scratch with a corrected comment).
- **Placeholder scan:** no TBD/TODO; every code step has complete, real code (not "similar to Task N").
- **Type consistency:** checked that patch targets in test-update steps (Tasks 1/3/4 Step 6) match the exact router module names created in that same task's earlier steps, and that `app/main.py`/`app/entrypoints/*.py` (Tasks 6-7) import router modules by the exact names Tasks 1/3/4 create them under.
