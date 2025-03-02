"""
What dpes this file do?

It creates three important functions that will be called throughout the project:
1. fermentation_convert_feedstock_kg_hr: This function converts the feedstock to kg/hr
2. fermentation_calc: This function calculates the (i) annual ethanol in MM gal/year, (ii) price in $/gal and (iii) GWP in lbCO2/yr based on the given mass of ethanol produced
3. fermentation_county: This function takes a county name from the user and returns the (i) annual ethanol, (ii) price and (iii) GWP

Where are these functions used in the project?
1. fermentation.py - Blueprint for Flask

What does the file rely on?
1. biosteam, biorefineries, pandas, warnings
2. biomass_data.csv in app/data/fermentation
"""
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import warnings
warnings.filterwarnings('ignore')

'''
QSDsan-webapp: Web application for QSDsan

This module is developed by:
    
    Yalin Li <mailto.yalin.li@gmail.com>

This module is under the University of Illinois/NCSA Open Source License.
Please refer to https://github.com/QSD-Group/QSDsan/blob/main/LICENSE.txt
for license details.
'''

import biosteam as bst
from biorefineries.cellulosic import Biorefinery as CellulosicEthanol
from biorefineries.cellulosic.streams import cornstover as cornstover_kwargs
from biorefineries.cornstover import ethanol_density_kggal
import pandas as pd

GWP_CFs = {
    'cornstover': 0.2,
    'sulfuric_acid': 1,
    'ammonia': 1,
    'cellulase': 1, #!!! note water content
    'CSL': 1,
    'caustic': 1, #!!! note water content    
    'FGD_lime': 1, #!!! need to be clear if this is CaO or Ca(OH)2
    }

STATE_DATA = pd.read_csv(r"app\data\fermentation\fermentation_data.csv")

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
    
    # Type checks
    if not isinstance(feedstock, (int, float)):
        raise TypeError('Feedstock should be a number')
    if not isinstance(unit, str):
        raise TypeError('Unit should be a string')
    
    if unit.lower() == 'kghr':
        return feedstock # No conversion needed
    elif unit.lower() == 'tons':
        return feedstock * 907.185 / 8760 # Convert tons/yr to kg/hr
    elif unit.lower() == 'tonnes':
        return feedstock * 1000 / 8760 # Convert tonnes/yr to kg/hr
    else:
        raise ValueError('Invalid unit')


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
        Contains the following:
        - 'cornstover': price of cornstover (USD/kg) [0.2]
        - 'sulfuric_acid': price of sulfuric acid (USD/kg) [1]
        - 'ammonia': price of ammonia (USD/kg) [1]
        - 'cellulase': price of cellulase (USD/kg) [1]
        - 'CSL': price of CSL (USD/kg) [1]
        - 'caustic': price of caustic (USD/kg) [1]
        - 'FGD_lime': price of FGD lime (USD/kg) [1]
    characterization_factors : tuple
        Global warming potential characterization factors (kg CO2-eq/kg).
        Contains the following:
        - consumption
        - production
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
    TypeError
        If the power utility price is not a number.
    Note: Add more checks for the other parameters.
    """
    
    # Type checks
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
    
    br = CellulosicEthanol(
        name='ethanol',
        )
    sys = br.sys
    tea = sys.TEA
    f = sys.flowsheet
    stream = f.stream
    feedstock = stream.cornstover
    ethanol = stream.ethanol
    
    feedstock.F_mass = mass 
    
    prices = {
        'cornstover': cornstover_price,
        }
    for ID, price in prices.items(): stream.search(ID).price = price
    bst.PowerUtility.price = power_utility_price
    
    for ID, CF in GWP_CFs.items(): stream.search(ID).characterization_factors['GWP'] = CF
    bst.PowerUtility.characterization_factors['GWP'] = characterization_factors
    
    sys.simulate()
    
    kg_to_lb_conversion_factor = 2.20462
    
    get_ethanol = lambda: ethanol.F_mass*ethanol_density_kggal*tea.operating_hours/1e6 # MM gal/year
    get_MESP = lambda: tea.solve_price(ethanol)*ethanol_density_kggal # from $/kg to $/gallon
    get_GWP = lambda: (sys.get_net_impact('GWP')/sys.operating_hours/ethanol.F_mass*ethanol_density_kggal)*kg_to_lb_conversion_factor # lb CO2e/gal

    # Comment these print statements for now
    # print(f'annual ethanol: ${get_ethanol():.3f} MM gal/yr')
    # print(f'price: ${get_MESP():.2f}/gal')
    # print(f'GWP: {get_GWP():.2f} lb CO2e/gal')
    
    return get_ethanol(), get_MESP(), get_GWP()
    

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
    # check if the name inputted in county exists in the first column of state_data
    
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
    
    try:
        kg_per_hr = state_data.loc[state_data['County'] == name_final, 'Kilogram/hr'].values[0]
    except KeyError:
        raise KeyError("Column 'Kilogram/hr' not found in the dataset.")
    except IndexError:
        raise ValueError(f"Value for 'Kilogram/hr' not found for county '{name_final}'.")

    ethanol, price, gwp = fermentation_calc(kg_per_hr)
    
    return name_final, dry_tonnes, ethanol, price, gwp
    
if __name__ == '__main__':
    
    # Let's write some unit tests
    
    # Test 1 - Fermentation Convert Feedstock kg/hr
    # Test 1 A - Test for valid inputs
    print(fermentation_convert_feedstock_kg_hr(100, 'tons')) # 10.356
    print(fermentation_convert_feedstock_kg_hr(100, 'tonnes')) # 11.416
    print(fermentation_convert_feedstock_kg_hr(100, 'kghr')) # 100
    
    # Test 1 B - Test for invalid inputs
    try:
        print(fermentation_convert_feedstock_kg_hr('100', 'tons')) # TypeError
    except TypeError as e:
        print(e)
    try:
        print(fermentation_convert_feedstock_kg_hr(100, 100)) # TypeError
    except TypeError as e:
        print(e)
    try:
        print(fermentation_convert_feedstock_kg_hr(100, 'ton')) # ValueError
    except ValueError as e:
        print(e)
        
    # Test 1 C - Test for edge cases
        
    # Test 2 - Lignocellulose Calc
    # Test 2 A - Test for valid inputs
    print(fermentation_calc(100)) # (0.0, 0.0, 0.0)

    # Test 2 B - Test for invalid inputs
    try:
        print(fermentation_calc('100')) # TypeError
    except TypeError as e:
        print(e)
    try:
        print(fermentation_calc(100, '100')) # TypeError
    except TypeError as e:
        print(e)
    try:
        print(fermentation_calc(100, 0.2, 'GWP_CFs')) # TypeError
    except TypeError as e:
        print(e)
        
    # Test 3 - Fermentation County
    # Test 3 A - Test for valid inputs        
    print(fermentation_county('cape may')) # ('Cape May', 0, 0.0, 0.0, 0.0)
    
    # Test 3 B - Test for invalid inputs
    try:
        print(fermentation_county(100)) # TypeError
    except TypeError as e:
        print(e)