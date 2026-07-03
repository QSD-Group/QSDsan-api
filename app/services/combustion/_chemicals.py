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

    HHV/LHV/Hf are assigned in this exact order (HHV explicit value, then
    LHV=0, then Hf=0) to match exposan's own assignment order. Note: setting
    Hf triggers thermosteam's Chemical.Hf setter, which recomputes HHV/LHV
    from formula stoichiometry as a side effect—so the actual HHV/LHV end up
    as thermosteam's recomputed values, not the literal numbers assigned
    above, and only Hf itself ends up as 0. This is intentional-by-inheritance:
    the old exposan code has the exact same three-line order and the exact
    same clobbering behavior (confirmed via the parity test in
    tests/test_combustion_chemicals.py), so this module reproduces it
    faithfully rather than "fixing" it—changing the assignment order here
    would be a behavior change relative to the old code, which this module
    must not introduce.
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
