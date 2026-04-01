"""
Combustion FastAPI Router

This router replaces the Flask combustion blueprint with FastAPI endpoints.
It provides the same functionality with improved validation, documentation,
and error handling.

Endpoints:
- GET /combustion/calc - Calculate electricity generation from waste
- GET /combustion/county - Get combustion potential for specific NJ county

Migration Status: Converted from app/blueprints/combustion.py
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Union

# Import service functions (unchanged from Flask version)
from app.services.combustion_service import (
    combustion_calc,
    combustion_county
)

# Import Pydantic models
from app.models.combustion import (
    CombustionCalcResponse,
    CombustionCountyResponse,
    CombustionUnit,
    WasteType,
    CombustionErrorResponse
)

# Create router (replaces Flask Blueprint)
router = APIRouter()


def convert_mass_to_kg_hr(mass: float, unit: str) -> float:
    """
    Convert mass from various units to kg/hr.
    Replaces the inline conversion logic from Flask blueprint.
    """
    if unit == 'kghr':
        return mass
    elif unit == 'tons':      # short tons/year -> kg/hr
        return mass * 907.185 / (365 * 24)
    elif unit == 'tonnes':    # metric tonnes/year -> kg/hr
        return mass * 1000 / (365 * 24)
    elif unit == 'mgd':       # MGD -> kg/hr
        # 1 million gallons/day = 1e6 gallons/day
        # 1 gallon ~ 3.78541 kg water
        return mass * 1e6 * 3.78541 / 24
    elif unit == 'm3d':       # m^3/day -> kg/hr
        # 1 m^3 of water ~ 1000 kg
        return mass * 1000 / 24
    else:
        raise ValueError(f"Invalid unit: {unit}")


@router.get(
    "/combustion/calc",
    response_model=CombustionCalcResponse,
    responses={
        400: {"model": CombustionErrorResponse, "description": "Bad request"},
        422: {"model": CombustionErrorResponse, "description": "Invalid unit or waste type"},
        500: {"model": CombustionErrorResponse, "description": "Unexpected error"}
    },
    summary="Calculate combustion electricity generation",
    description="""
    Takes in a mass, a unit of that mass, and a waste type, then returns:
    1. The mass converted to kg/hr
    2. The annual electricity production in MWh  
    3. The avoided emissions in million metric tonnes
    4. The fraction of total NJ emissions avoided
    """
)
async def combustion_calc_data(
    mass: float = Query(
        ...,
        gt=0,
        description="The mass of the feedstock",
        openapi_examples={"default": {"value": 100.0}}
    ),
    unit: CombustionUnit = Query(
        CombustionUnit.KGHR,
        description="The unit of the feedstock mass",
        openapi_examples={"default": {"value": "kghr"}}
    ),
    waste_type: WasteType = Query(
        WasteType.SLUDGE,
        description="The type of waste",
        openapi_examples={"default": {"value": "sludge"}}
    )
) -> CombustionCalcResponse:
    """
    Calculate combustion electricity generation from waste mass.
    
    This endpoint converts waste mass to electricity production metrics
    using combustion process calculations.
    """
    
    try:
        # Convert mass to kg/hr using the conversion function
        mass_kg_hr = convert_mass_to_kg_hr(mass, unit.value)
        
        # Call existing combustion calculation service
        result = combustion_calc(mass_kg_hr, waste_type.value)
        
        if not result:
            raise HTTPException(
                status_code=500,
                detail="Unexpected error in combustion_calc"
            )
        
        # Unpack the results - matches Flask blueprint return format
        wt, mass_kg_hr2, electricity, emissions, percent = result
        
        return CombustionCalcResponse(
            mass=mass_kg_hr2,
            waste_type=wt,
            electricity=electricity,
            emissions=emissions,
            percent=percent
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail=str(e)
        )
    except TypeError as e:
        raise HTTPException(
            status_code=422,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )


@router.get(
    "/combustion/county",
    response_model=CombustionCountyResponse,
    responses={
        400: {"model": CombustionErrorResponse, "description": "Bad request"},
        404: {"model": CombustionErrorResponse, "description": "County not found"},
        422: {"model": CombustionErrorResponse, "description": "Invalid waste type"},
        500: {"model": CombustionErrorResponse, "description": "Unexpected error"}
    },
    summary="Get combustion potential for NJ county",
    description="""
    Takes in a county name and a waste type, then returns:
    1. The county name (as found in the data set)
    2. The mass (kg/hr) associated with that county for the specified waste
    3. The annual electricity production in MWh
    4. The avoided emissions in million metric tonnes
    5. The fraction of total NJ emissions avoided
    """
)
async def combustion_county_data(
    county_name: str = Query(
        ...,
        description="The name of the New Jersey county",
        openapi_examples={"default": {"value": "Essex"}}
    ),
    waste_type: WasteType = Query(
        WasteType.SLUDGE,
        description="The type of waste",
        openapi_examples={"default": {"value": "sludge"}}
    )
) -> CombustionCountyResponse:
    """
    Get combustion potential for a specific New Jersey county.
    
    This endpoint looks up county-specific waste data and calculates
    the combustion electricity generation potential for that county.
    """
    
    try:
        # Call existing combustion county service
        result = combustion_county(county_name, waste_type.value)
        
        if result is None:
            raise HTTPException(
                status_code=404,
                detail=f"County '{county_name}' not found. Valid counties are the 21 NJ counties (e.g. Essex, Atlantic, Bergen)."
            )
        
        # Unpack the results - matches Flask blueprint return format
        name_final, wt, mass, electricity, emissions, percent = result
        
        return CombustionCountyResponse(
            county_name=name_final,
            waste_type=wt,
            mass=mass,
            electricity=electricity,
            emissions=emissions,
            percent=percent
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail=str(e)
        )
    except TypeError as e:
        raise HTTPException(
            status_code=422,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )