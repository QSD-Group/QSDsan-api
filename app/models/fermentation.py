"""
Fermentation Pydantic Models

These models define the request/response schemas for fermentation endpoints.
They provide automatic validation, documentation, and type safety.

Based on the existing Flask fermentation blueprint structure.
"""

from enum import Enum
from pydantic import BaseModel, ConfigDict, Field


class FermentationUnit(str, Enum):
    """Valid units for fermentation mass input"""
    KGHR = "kghr"
    TONS = "tons"
    TONNES = "tonnes"


class FermentationCalcResponse(BaseModel):
    """Response model for fermentation calculation endpoint (/fermentation/calc)"""
    model_config = ConfigDict(json_schema_extra={
        "example": {"mass": 100.0, "ethanol": 0.65, "price": 84.66, "gwp": 13.63}
    })

    mass: float = Field(description="Mass of the feedstock in kg/hr")
    ethanol: float = Field(description="Ethanol produced in MM gallons/year")
    price: float = Field(description="Ethanol price in $/gallon")
    gwp: float = Field(description="Greenhouse gas emissions in lb CO2e/gallon")


class FermentationCountyResponse(BaseModel):
    """Response model for fermentation county endpoint (/fermentation/county)"""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "county_name": "Atlantic",
            "mass": 200.0,
            "ethanol": 1.2,
            "price": 84.66,
            "gwp": 13.63,
        }
    })

    county_name: str = Field(description="Name of the county")
    mass: float = Field(description="Mass of the feedstock in kg/hr")
    ethanol: float = Field(description="Ethanol produced in MM gallons/year")
    price: float = Field(description="Ethanol price in $/gallon")
    gwp: float = Field(description="Greenhouse gas emissions in lb CO2e/gallon")


class FermentationErrorResponse(BaseModel):
    """Standard error response model for fermentation endpoints"""
    model_config = ConfigDict(json_schema_extra={
        "example": {"message": "Unit must be one of ['kghr', 'tons', 'tonnes']"}
    })

    message: str = Field(description="Error message")
