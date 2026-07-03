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
