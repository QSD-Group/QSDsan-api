"""
Combustion electricity-generation FastAPI router (heavy — imports biosteam).

Endpoints:
- GET /combustion/calc - Calculate electricity generation from waste
"""

from fastapi import APIRouter, Query, HTTPException

from app.services.combustion.calc import combustion_calc

from app.models.combustion import (
    CombustionCalcResponse,
    CombustionUnit,
    WasteType,
    CombustionErrorResponse
)

router = APIRouter()


def convert_mass_to_kg_hr(mass: float, unit: str) -> float:
    """Convert mass from various units to kg/hr."""
    if unit == 'kghr':
        return mass
    elif unit == 'tons':
        return mass * 907.185 / (365 * 24)
    elif unit == 'tonnes':
        return mass * 1000 / (365 * 24)
    elif unit == 'mgd':
        return mass * 1e6 * 3.78541 / 24
    elif unit == 'm3d':
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
    try:
        mass_kg_hr = convert_mass_to_kg_hr(mass, unit.value)
        result = combustion_calc(mass_kg_hr, waste_type.value)

        if not result:
            raise HTTPException(status_code=500, detail="Unexpected error in combustion_calc")

        wt, mass_kg_hr2, electricity, emissions, percent = result

        return CombustionCalcResponse(
            mass=mass_kg_hr2,
            waste_type=wt,
            electricity=electricity,
            emissions=emissions,
            percent=percent
        )

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except TypeError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
