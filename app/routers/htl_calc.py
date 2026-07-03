"""
HTL diesel-production FastAPI router (heavy — imports exposan.htl).

Endpoints:
- GET /htl/calc - Calculate HTL diesel production from sludge mass
"""

from fastapi import APIRouter, Query, HTTPException

from app.services.htl.calc import htl_calc
from app.services.htl.lookup import htl_convert_sludge_mass_kg_hr as htl_convert_kg

from app.models.htl import (
    HTLCalcResponse,
    HTLUnit,
    ErrorResponse
)

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
    sludge_kg_hr = htl_convert_kg(sludge, unit.value)

    try:
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
