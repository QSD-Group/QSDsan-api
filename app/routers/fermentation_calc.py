"""
Fermentation ethanol-production FastAPI router (heavy — imports biosteam
and the cellulosic biorefinery).

Endpoints:
- GET /fermentation/calc - Calculate ethanol production from biomass
"""

from fastapi import APIRouter, Query, HTTPException

from app.services.fermentation.calc import fermentation_calc
from app.services.fermentation.lookup import fermentation_convert_feedstock_kg_hr as fermentation_kg

from app.models.fermentation import (
    FermentationCalcResponse,
    FermentationUnit,
    FermentationErrorResponse
)

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
    try:
        kg_hr = fermentation_kg(mass, unit.value)
        ethanol, price, gwp = fermentation_calc(kg_hr)

        return FermentationCalcResponse(
            mass=kg_hr,
            ethanol=ethanol,
            price=price,
            gwp=gwp
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
