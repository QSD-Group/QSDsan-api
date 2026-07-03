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
