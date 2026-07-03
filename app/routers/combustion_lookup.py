"""
Combustion county-lookup FastAPI router (light — no biosteam).

Endpoints:
- GET /combustion/county - Get combustion potential for a specific NJ county
"""

from fastapi import APIRouter, Query, HTTPException

from app.services.combustion.lookup import combustion_county

from app.models.combustion import (
    CombustionCountyResponse,
    WasteType,
    CombustionErrorResponse
)

router = APIRouter()


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
    try:
        result = combustion_county(county_name, waste_type.value)

        if result is None:
            raise HTTPException(
                status_code=404,
                detail=f"County '{county_name}' not found. Valid counties are the 21 NJ counties (e.g. Essex, Atlantic, Bergen)."
            )

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
        raise
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except TypeError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
