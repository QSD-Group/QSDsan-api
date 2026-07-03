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
    """
    Lipids/Proteins/Carbohydrates/Ash are built with the same three-line
    assignment order as the old exposan-based construction: HHV is set to
    22.0e6*MW/1000, then LHV=0, then Hf=0. Setting Hf triggers thermosteam's
    Hf setter, which recomputes HHV/LHV from formula stoichiometry as a side
    effect -- so the literal 22.0e6*MW/1000 value does not survive; only
    Hf itself ends up as 0 (see _chemicals.py's _create_sludge_chemicals
    docstring). This smoke test checks the actual (clobbered-but-consistent)
    outcome: all four chemicals share the same formula, so they end up with
    identical, non-zero HHV/LHV, and Hf == 0.
    """
    from app.services.combustion._chemicals import create_chemicals
    chems = create_chemicals()
    hhvs = set()
    lhvs = set()
    for chem_id in ("Lipids", "Proteins", "Carbohydrates", "Ash"):
        chem = getattr(chems, chem_id)
        assert chem.Hf == 0
        assert chem.HHV > 0
        assert chem.LHV > 0
        hhvs.add(chem.HHV)
        lhvs.add(chem.LHV)
    assert len(hhvs) == 1  # identical formula -> identical HHV
    assert len(lhvs) == 1  # identical formula -> identical LHV
