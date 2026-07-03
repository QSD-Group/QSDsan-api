"""
HTL county-lookup FastAPI router (light — no exposan/biosteam).

Endpoints:
- GET /htl/county - Get HTL potential for a specific NJ county
"""

from fastapi import APIRouter, Query, HTTPException

from app.services.htl.lookup import htl_county

from app.models.htl import (
    HTLCountyResponse,
    ErrorResponseWithMessage
)

router = APIRouter()


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
    try:
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
            detail=f"County '{county_name}' not found. Valid counties are the 21 NJ counties (e.g. Essex, Atlantic, Bergen)."
        )
    except TypeError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
