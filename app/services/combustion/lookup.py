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
