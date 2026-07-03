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


def _eval_handle(handle, chemical, *args):
    """
    Evaluate a thermosteam property handle (Cn/mu/V), returning None if no
    model is set.

    Most of the chemicals here are locked to a single phase at construction
    (e.g. Lipids/Proteins/Carbohydrates/Ash at 's', O2/N2/CH4/CO2 at 'g'),
    giving handles that are callable directly as handle(*args) and expose
    `.method`. Water is the one exception in CHEMICAL_IDS: both the old
    (qsdsan Component('H2O')) and new (tmo.Chemical('Water')) constructions
    build it as a full multi-phase chemical, so its Cn/mu/V handles are
    PhaseTHandle/PhaseTPHandle objects with no top-level `.method` --
    dispatch to the phase-specific sub-handle at the chemical's reference
    phase instead (thermosteam.base.PhaseTHandle.__call__ does the same
    dispatch internally: getattr(self, phase)(*args)).
    """
    if hasattr(handle, "method"):
        target = handle
    else:
        phase = chemical.locked_state or chemical.phase_ref
        target = getattr(handle, phase)
    return target(*args) if target.method else None


def _snapshot(chemical):
    return {
        "formula": chemical.formula,
        "MW": chemical.MW,
        "HHV": chemical.HHV,
        "LHV": chemical.LHV,
        "Hf": chemical.Hf,
        "Cn": _eval_handle(chemical.Cn, chemical, REFERENCE_T),
        "mu": _eval_handle(chemical.mu, chemical, REFERENCE_T, REFERENCE_P),
        "V": _eval_handle(chemical.V, chemical, REFERENCE_T, REFERENCE_P),
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
