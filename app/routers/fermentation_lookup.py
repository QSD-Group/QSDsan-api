"""
Fermentation county-lookup FastAPI router (light — no biosteam/biorefineries).

Endpoints:
- GET /fermentation/county - Get fermentation potential for a specific NJ county
"""

from fastapi import APIRouter, Query, HTTPException

from app.services.fermentation.lookup import fermentation_county

from app.models.fermentation import (
    FermentationCountyResponse,
    FermentationErrorResponse
)

router = APIRouter()


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
    try:
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
        raise HTTPException(status_code=500, detail=str(e))
