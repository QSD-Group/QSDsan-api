"""
HTL (Hydrothermal Liquefaction) Pydantic Models

These models define the request/response schemas for HTL endpoints.
They provide automatic validation, documentation, and type safety.

Based on the existing Flask HTL blueprint structure.
"""

from enum import Enum
from pydantic import BaseModel, ConfigDict, Field


class HTLUnit(str, Enum):
    """Valid units for HTL mass input"""
    KGHR = "kghr"
    TONS = "tons"
    TONNES = "tonnes"
    MGD = "mgd"
    M3D = "m3d"


class HTLCalcResponse(BaseModel):
    """Response model for HTL calculation endpoint (/htl/calc)"""
    model_config = ConfigDict(json_schema_extra={
        "example": {"sludge": 100.0, "price": 2.45, "gwp": 8.21}
    })

    sludge: float = Field(description="Mass of the sludge in kg/hr")
    price: float = Field(description="Price of the HTL product in $/gallon")
    gwp: float = Field(description="Global warming potential in lb CO2e/gallon")


class HTLCountyResponse(BaseModel):
    """Response model for HTL county endpoint (/htl/county)"""
    model_config = ConfigDict(json_schema_extra={
        "example": {"county_name": "Atlantic", "sludge": 1234.56, "price": 2.45, "gwp": 8.21}
    })

    county_name: str = Field(description="Name of the county")
    sludge: float = Field(description="Mass of the sludge in kg/hr")
    price: float = Field(description="Price of the HTL product in $/gallon")
    gwp: float = Field(description="Global warming potential in lb CO2e/gallon")


class ErrorResponse(BaseModel):
    """Standard error response model"""
    model_config = ConfigDict(json_schema_extra={
        "example": {"error": "Invalid input parameter"}
    })

    error: str = Field(description="Error message")


class ErrorResponseWithMessage(BaseModel):
    """Alternative error response model (used by county endpoint)"""
    model_config = ConfigDict(json_schema_extra={
        "example": {"message": "County not found"}
    })

    message: str = Field(description="Error message")
