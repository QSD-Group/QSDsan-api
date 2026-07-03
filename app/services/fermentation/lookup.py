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
