"""
Fermentation FastAPI Router

This router replaces the Flask fermentation blueprint with FastAPI endpoints.
It provides the same functionality with improved validation, documentation,
and error handling.

Endpoints:
- GET /fermentation/calc - Calculate ethanol production from biomass
- GET /fermentation/county - Get fermentation potential for specific NJ county

Migration Status: Converted from app/blueprints/fermentation.py
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Union

# Import service functions (unchanged from Flask version)
from app.services.fermentation_service import (
    fermentation_calc,
    fermentation_county,
    fermentation_convert_feedstock_kg_hr as fermentation_kg
)

# Import Pydantic models
from app.models.fermentation import (
    FermentationCalcResponse,
    FermentationCountyResponse,
    FermentationUnit,
    FermentationErrorResponse
)

# Create router (replaces Flask Blueprint)
router = APIRouter()


@router.get(
    "/fermentation/calc",
    response_model=FermentationCalcResponse,
    responses={
        400: {"model": FermentationErrorResponse, "description": "Bad request"},
        422: {"model": FermentationErrorResponse, "description": "Invalid unit"},
        500: {"model": FermentationErrorResponse, "description": "Internal server error"}
    },
    summary="Calculate ethanol production from biomass",
    description="""
    Convert mass input to ethanol production and related metrics.
    Takes in a mass of feed stock, a unit of that mass and returns:
    1. Mass of the feedstock in kg/hr
    2. Ethanol produced in MM gallons/year
    3. Price of ethanol in $/gallon
    4. Greenhouse gas emissions in lb CO2e/gallon
    """
)
async def fermentation_calc_data(
    mass: float = Query(
        ...,
        gt=0,
        description="Mass of the feedstock",
        openapi_examples={"default": {"value": 100.0}}
    ),
    unit: FermentationUnit = Query(
        FermentationUnit.KGHR,
        description="Unit of the mass",
        openapi_examples={"default": {"value": "kghr"}}
    )
) -> FermentationCalcResponse:
    """
    Calculate ethanol production from biomass feedstock.
    
    This endpoint converts biomass mass to ethanol production metrics
    using fermentation process calculations.
    """
    
    try:
        # Convert mass to kg/hr using existing service function
        kg_hr = fermentation_kg(mass, unit.value)
        
        # Call existing fermentation calculation service
        ethanol, price, gwp = fermentation_calc(kg_hr)
        
        return FermentationCalcResponse(
            mass=kg_hr,
            ethanol=ethanol,
            price=price,
            gwp=gwp
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.get(
    "/fermentation/county",
    response_model=FermentationCountyResponse,
    responses={
        400: {"model": FermentationErrorResponse, "description": "Bad request"},
        404: {"model": FermentationErrorResponse, "description": "County not found"},
        500: {"model": FermentationErrorResponse, "description": "Internal server error"}
    },
    summary="Get fermentation potential for NJ county",
    description="""
    Calculate ethanol production and related metrics for a given county.
    Takes in a county name and returns:
    1. Mass of the feedstock in kg/hr
    2. Ethanol produced in MM gallons/year
    3. Price of ethanol in $/gallon
    4. Greenhouse gas emissions in lb CO2e/gallon
    """
)
async def fermentation_county_data(
    county_name: str = Query(
        ...,
        description="Name of the New Jersey county",
        openapi_examples={"default": {"value": "Atlantic"}}
    )
) -> FermentationCountyResponse:
    """
    Get fermentation potential for a specific New Jersey county.
    
    This endpoint looks up county-specific biomass data and calculates
    the ethanol production potential for that county.
    """
    
    try:
        # Call existing fermentation county service
        name, mass, ethanol, price, gwp = fermentation_county(county_name)
        
        return FermentationCountyResponse(
            county_name=name,
            mass=mass,
            ethanol=ethanol,
            price=price,
            gwp=gwp
        )
        
    except ValueError:
        raise HTTPException(
            status_code=404,
            detail=f"County '{county_name}' not found. Valid counties are the 21 NJ counties (e.g. Essex, Atlantic, Bergen)."
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )