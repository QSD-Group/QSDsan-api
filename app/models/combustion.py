"""
Combustion Pydantic Models

These models define the request/response schemas for combustion endpoints.
They provide automatic validation, documentation, and type safety.

Based on the existing Flask combustion blueprint structure.
"""

from enum import Enum
from pydantic import BaseModel, ConfigDict, Field


class CombustionUnit(str, Enum):
    """Valid units for combustion mass input"""
    KGHR = "kghr"
    TONS = "tons"
    TONNES = "tonnes"
    MGD = "mgd"
    M3D = "m3d"


class WasteType(str, Enum):
    """Valid waste types for combustion"""
    SLUDGE = "sludge"
    FOOD = "food"
    FOG = "fog"
    GREEN = "green"
    MANURE = "manure"


class CombustionCalcResponse(BaseModel):
    """Response model for combustion calculation endpoint (/combustion/calc)"""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "mass": 100.0,
            "waste_type": "sludge",
            "electricity": 1677161.14,
            "emissions": 0.37,
            "percent": 0.0038,
        }
    })

    mass: float = Field(description="Mass in kg/hr")
    waste_type: str = Field(description="Type of waste used")
    electricity: float = Field(description="Annual electricity production in MWh")
    emissions: float = Field(description="Avoided emissions in million metric tonnes")
    percent: float = Field(description="Fraction of total NJ emissions avoided")


class CombustionCountyResponse(BaseModel):
    """Response model for combustion county endpoint (/combustion/county)"""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "county_name": "Essex",
            "waste_type": "sludge",
            "mass": 1234.56,
            "electricity": 1677161.14,
            "emissions": 0.37,
            "percent": 0.0038,
        }
    })

    county_name: str = Field(description="Name of the county")
    waste_type: str = Field(description="Type of waste used")
    mass: float = Field(description="Mass in kg/hr")
    electricity: float = Field(description="Annual electricity production in MWh")
    emissions: float = Field(description="Avoided emissions in million metric tonnes")
    percent: float = Field(description="Fraction of total NJ emissions avoided")


class CombustionErrorResponse(BaseModel):
    """Standard error response model for combustion endpoints"""
    model_config = ConfigDict(json_schema_extra={
        "example": {"error": "Invalid waste type. Must be one of ['sludge', 'food', 'fog', 'green', 'manure']"}
    })

    error: str = Field(description="Error message")
