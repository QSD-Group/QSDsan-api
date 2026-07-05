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
    """Build (once per warm container) or return the cached CellulosicEthanol biorefinery.

    biosteam's default recycle tolerance (rmol=0.01) is a per-iteration
    relative-delta check, not a true-convergence check: a cold build takes
    many iterations to first satisfy it (landing close to converged), but
    resimulating an already-converged cached System satisfies it after just
    one iteration, so each warm call only advances one contraction step
    toward the true fixed point. This under-convergence is most visible in
    sys.get_net_impact('GWP') and tea.solve_price, which depend on a
    slow-converging subsystem (fermentation stillage/solids handling feeding
    the boiler) that the product mass balance itself isn't sensitive to.
    Tightening tolerance once here forces every simulate() call, warm or
    cold, to reach the same tight fixed point regardless of starting point.
    """
    global _br
    if _br is not None:
        return _br
    with _br_lock:
        if _br is None:
            _br = CellulosicEthanol(name='ethanol')
            _br.sys.set_tolerance(mol=1e-6, rmol=1e-9, subsystems=True)
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
