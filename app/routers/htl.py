"""
HTL (Hydrothermal Liquefaction) FastAPI Router

This router replaces the Flask HTL blueprint with FastAPI endpoints.
It provides the same functionality with improved validation, documentation,
and error handling.

Endpoints:
- GET /htl/calc - Calculate HTL diesel production from sludge mass
- GET /htl/county - Get HTL potential for specific NJ county

Migration Status: Converted from app/blueprints/htl.py
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Union

# Import service functions (unchanged from Flask version)
from app.services.htl_service import (
    htl_calc, 
    htl_county, 
    htl_convert_sludge_mass_kg_hr as htl_convert_kg
)

# Import Pydantic models
from app.models.htl import (
    HTLCalcResponse,
    HTLCountyResponse, 
    HTLUnit,
    ErrorResponse,
    ErrorResponseWithMessage
)

# Create router (replaces Flask Blueprint)
router = APIRouter()


@router.get(
    "/htl/calc",
    response_model=HTLCalcResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Bad request"},
        422: {"model": ErrorResponse, "description": "Invalid unit"},
        500: {"model": ErrorResponse, "description": "Unexpected error"}
    },
    summary="Calculate HTL diesel production",
    description="""
    Takes in a sludge mass in a specified unit and returns:
    1. Mass of the sludge in kg/hr
    2. Price of the HTL product in $/gallon  
    3. Greenhouse gas emissions in lb CO2e/gallon
    """
)
async def htl_calc_data(
    sludge: float = Query(
        ...,
        gt=0,
        description="The mass of the sludge",
        openapi_examples={"default": {"value": 100.0}}
    ),
    unit: HTLUnit = Query(
        HTLUnit.KGHR,
        description="The unit of the sludge mass",
        openapi_examples={"default": {"value": "kghr"}}
    )
) -> HTLCalcResponse:
    """
    Calculate HTL diesel production from sludge mass.
    
    This endpoint converts sludge mass to diesel production metrics
    using hydrothermal liquefaction process calculations.
    """
    
    # Convert sludge to kg/hr using existing service function
    sludge_kg_hr = htl_convert_kg(sludge, unit.value)
    
    try:
        # Call existing HTL calculation service
        result = htl_calc(sludge_kg_hr)
        
        if result:
            price, gwp = result
            return HTLCalcResponse(
                sludge=sludge_kg_hr,
                price=price,
                gwp=gwp
            )
        else:
            raise HTTPException(
                status_code=500,
                detail="Unexpected error in HTL calculation"
            )
            
    except TypeError as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.get(
    "/htl/county", 
    response_model=HTLCountyResponse,
    responses={
        400: {"model": ErrorResponseWithMessage, "description": "Bad request"},
        404: {"model": ErrorResponseWithMessage, "description": "County not found"},
        500: {"model": ErrorResponseWithMessage, "description": "Unexpected error"}
    },
    summary="Get HTL potential for NJ county",
    description="""
    Takes in a county name and returns:
    1. The name of the county
    2. The mass of the sludge in kg/hr
    3. The price of the HTL product in $/gallon
    4. The greenhouse gas emissions in lb CO2e/gallon
    """
)
async def htl_county_data(
    county_name: str = Query(
        ...,
        description="The name of the New Jersey county",
        openapi_examples={"default": {"value": "Atlantic"}}
    )
) -> HTLCountyResponse:
    """
    Get HTL conversion potential for a specific New Jersey county.
    
    This endpoint looks up county-specific sludge data and calculates
    the HTL diesel production potential for that county.
    """
    
    try:
        # Call existing HTL county service
        result = htl_county(county_name)
        
        if result:
            name, sludge, price, gwp = result
            return HTLCountyResponse(
                county_name=name,
                sludge=sludge,
                price=price,
                gwp=gwp
            )
        else:
            raise HTTPException(
                status_code=500,
                detail="Unexpected error in HTL county calculation"
            )
            
    except ValueError:
        raise HTTPException(
            status_code=404,
            detail="County not found"
        )
    except TypeError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )