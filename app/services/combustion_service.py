"""
What does this file do?

It creates four important functions that willbe called throughout the project:
1. combustion_convert_feedstock_kg_hr: 
2. combustion_calc_raw:
3. combustion_calc:
4. combustion_county:

Where are these functions used in the project?
1. combustion.py - Blueprint for Flask

What does this file rely on?
1. biosteam, exposan, biorefineries, and pandas
2. combustion_data.csv
"""
import biosteam as bst

# for file paths
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Define a relative path inside the project
EXPOSAN_RESULTS_PATH = os.path.join(BASE_DIR, "..", "exposan_results")

if not os.path.exists(EXPOSAN_RESULTS_PATH):
    os.makedirs(EXPOSAN_RESULTS_PATH, exist_ok=True)

from exposan import htl
from biorefineries.cane import create_sugarcane_chemicals
from biorefineries.tea import create_cellulosic_ethanol_tea

import warnings
warnings.filterwarnings("ignore")

import pandas as pd



BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "..", "data", "combustion", "combustion_data.csv")

STATE_DATA = pd.read_csv(CSV_PATH)
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
        else: self.electricity_demand = 0

def create_chemicals():
    htl_cmps = htl.create_components()
    cane_chems = create_sugarcane_chemicals()
    
    Water = htl_cmps.Water
    Lipids = htl_cmps.Sludge_lipid.copy('Lipids')
    Proteins = htl_cmps.Sludge_protein.copy('Proteins')
    Carbohydrates = htl_cmps.Sludge_carbo.copy('Carbohydrates')
    Ash = htl_cmps.Sludge_ash.copy('Ash')
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
    dry_mass : float
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
    
    Examples
    --------
    >>> combustion_calc(1000, [0.7, 0.257, 0.204, 0.463], 486.63)
    (16771611.411033249, 3.7020225242133353, 0.037930558649726796)
    
    >>> combustion_calc(1000)
    (16771611.411033249, 3.7020225242133353, 0.037930558649726796)

    """
    
    
    # Error handling
    if not isinstance(composition, list):
        raise TypeError("composition must be a list")
    if not isinstance(nj_avg_power_co2, (float, int)):
        raise TypeError("nj_avg_power_co2 must be a float or an int")
    if len(composition) != 4:
        raise ValueError("composition must have 4 elements")
    
    # Assign values
    a, b, c, d = composition
    chems = create_chemicals() # Create chemicals, this code is important
    
    moisture = a*mass_in_kg_hr # Moisture is a% of mass flow rate, kg/hr
    
    if (dry_mass_in_kg_hr is not None):
        moisture = mass_in_kg_hr - dry_mass_in_kg_hr 
        # If provided the dry mass, then moisture is the difference between the total mass and the dry mass
    
    ash = b*mass_in_kg_hr # Ash is b% of mass flow rate, kg/hr
    lipids = c*(mass_in_kg_hr - (moisture + ash)) # Of the remaining non-moisture, non-ash, c% is lipids, kg/hr
    proteins = d*(mass_in_kg_hr - (moisture + ash)) # Of the remaining non-moisture, non-ash, d% is proteins, kg/hr
    carbohydrates = mass_in_kg_hr - (moisture + ash + lipids + proteins) # Of the remaining non-moisture, non-ash, the rest is carbohydrates, kg/hr
    
    
    feedstock = bst.Stream('feedstock',
                           Water=moisture, 
                            Ash=ash,
                            Lipids=lipids, 
                            Proteins=proteins,
                            Carbohydrates=carbohydrates)
    BT = BoilerTurbogenerator('BT', ins=feedstock)
    sys = bst.System('sys', path=(BT,))
    BT = sys.flowsheet.unit.BT
    tea = create_cellulosic_ethanol_tea(sys, OSBL_units=[BT])
    sys.simulate()
    
    total_electricity = -BT.net_power # kW (kWh/hr), net production so the original value is negative
    annual_electricity = total_electricity * 365 * 24 / 1e3 # MWh // million watters we can generate per year
    
    NJ_avg_power_CO2 = nj_avg_power_co2 * 0.453592 # lb CO2/MWh to kg CO2/MWh
    avoided_emissions = NJ_avg_power_CO2 * annual_electricity / 1e3 / 1e6 # million metric tonne
    
    avoided_emissions_percent = avoided_emissions / 97.6
                           
    return (
        annual_electricity,
        avoided_emissions,
        avoided_emissions_percent
    )
    
COMPOSITIONS = {
    'sludge': [0.7, 0.257, 0.204, 0.463], 
    'food': [0.74, 0.0679, 0.22, 0.2],
    'fog': [0.35, 0.01865, 0.987, 0.002], 
    'green': [0.342, 0.134, 0.018, 0.049],
    'manure': [0.6634, 0.3056, 0.092325, 0.216375],
    }

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
        
    Examples
    --------
    >>> combustion_calc(1000, "sludge")
    (16771611.411033249, 3.7020225242133353, 0.037930558649726796)
        
    """
    
    # raising the TypeErrors
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
        
    annual_electricity, avoided_emissions, avoided_emissions_percent = combustion_calc_raw(mass, list_to_use)
    return (
        waste_type, # type of waste - sludge, food, fog, green, manure
        mass, # in kg/hr
        annual_electricity, # in MWh
        avoided_emissions, # in million metric tonnes
        avoided_emissions_percent # as a percentage of total emissions
    )
        
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
        
    Examples
    --------
    >>> combustion_county("Warren", "sludge")
    (Warren, 16771611.411033249, 3.7020225242133353, 0.037930558649726796)
        
    """
    
    # raising the TypeErrors
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
    
    dry_mass_kg_hr = None
    
    match waste_type:
        case "sludge":
            mass = state_data.loc[state_data['County'] == name_final, 'Sludge (MGD)'].values[0] # this is in MGD | Convert from million gallons/day to kg/hr
            mass_kg_hr = mass * 1e6*3.78541/24 # number from report, MGD to kg/hr
            
        case "food":
            mass = state_data.loc[state_data['County'] == name_final, 'Food (tons)'].values[0] # this is tons | Convert from dry tons/year to kg/hr
            mass_kg_hr = mass * 907.185 / (24*365) # complete mass is kg/hr
            
            dry_mass = state_data.loc[state_data['County'] == name_final, 'Food (dry tons)'].values[0] # this is tons | Convert from dry tons/year to kg/hr
            dry_mass_kg_hr = dry_mass * 907.185 / (24*365) # this is dry, which is some percentage of the data
            
        case "fog":
            mass = state_data.loc[state_data['County'] == name_final, 'Fog (tons)'].values[0] # this is tons | Convert from dry tons/year to kg/hr
            mass_kg_hr = mass * 907.185 / (24*365) # this is dry, which is some percentage of the data
            
            dry_mass = state_data.loc[state_data['County'] == name_final, 'Fog (dry tons)'].values[0] # this is tons | Convert from dry tons/year to kg/hr
            dry_mass_kg_hr = dry_mass * 907.185 / (24*365) # this is dry, which is some percentage of the data

        case "green":
            mass = state_data.loc[state_data['County'] == name_final, 'Green (dry tons)'].values[0] # this is tons | Convert from dry tons/year to kg/hr
            mass_kg_hr = mass * 907.185 / (24*365) # this is dry, which is some percentage of the data
            mass_kg_hr = mass_kg_hr / compositions["green"][0] # this is complete green in kg/hr

        case "manure":
            mass = state_data.loc[state_data['County'] == name_final, 'Manure (lbs)'].values[0] # this is lbs | Convert from lbs/year to kg/hr
            mass_kg_hr = mass * 0.453592 / (24*365) # this is dry, which is some percentage of the data
            mass_kg_hr = mass_kg_hr / compositions["manure"][0] # this is complete manure in kg/hr

        case _:
            raise ValueError("waste_type must be one of 'sludge', 'food', 'fog', 'green', or 'manure'")
        
    waste_type, mass, annual_electricity, avoided_emissions, avoided_emissions_percent = combustion_calc(mass_kg_hr, waste_type, dry_mass=dry_mass_kg_hr) 

    return (
        name_final, # County name
        waste_type, # type of waste - sludge, food, fog, green, manure
        mass, # in kg/hr
        annual_electricity, # in MWh
        avoided_emissions, # in million metric tonnes
        avoided_emissions_percent # as a percentage of total emissions
    )
    
if __name__ == '__main__':
    print(combustion_calc_raw(1000))
    print(combustion_calc(1000, "sludge"))
    
    dmt_yr = 29286.4
    dmt_hr = dmt_yr / (24*365)
    kg_hr = dmt_hr * 1000
    print(combustion_calc(kg_hr, "sludge"))
    
    print("\nEverything Essex")
    print(combustion_county("essex", "sludge"))
    print(combustion_county("essex", "food"))
    print(combustion_county("essex", "fog"))
    print(combustion_county("essex", "green"))
    print(combustion_county("essex", "manure"))
    
    print("\n Everything Warren")
    print(combustion_county("warren", "sludge"))
    print(combustion_county("warren", "food"))
    print(combustion_county("warren", "fog"))
    print(combustion_county("warren", "green"))
    print(combustion_county("warren", "manure"))
    
    print("\n Everything Cape May")
    print(combustion_county("cape may", "sludge"))
    print(combustion_county("cape may", "food"))
    print(combustion_county("cape may", "fog"))
    print(combustion_county("cape may", "green"))
    print(combustion_county("cape may", "manure"))    
    
    print("\n Everything Bergen")
    print(combustion_county("bergen", "sludge"))
    print(combustion_county("bergen", "food"))
    print(combustion_county("bergen", "fog"))
    print(combustion_county("bergen", "green"))
    print(combustion_county("bergen", "manure"))
    
    print("\n Everything Middlesex")
    print(combustion_county("middlesex", "sludge"))
    print(combustion_county("middlesex", "food"))
    print(combustion_county("middlesex", "fog"))
    print(combustion_county("middlesex", "green"))
    print(combustion_county("middlesex", "manure"))
       
    
    print("\n Everything Hudson")
    print(combustion_county("hudson", "sludge"))
    print(combustion_county("hudson", "food"))
    print(combustion_county("hudson", "fog"))
    print(combustion_county("hudson", "green"))
    try:
        print(combustion_county("hudson", "manure"))
    except ValueError as e:
        print(e)
    
    print("\n Everything Mercer")
    print(combustion_county("mercer", "sludge"))
    print(combustion_county("mercer", "food"))
    print(combustion_county("mercer", "fog"))
    print(combustion_county("mercer", "green"))
    print(combustion_county("mercer", "manure"))
    
