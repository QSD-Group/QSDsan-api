"""
Pydantic Models Package

This package contains all Pydantic models for request/response validation
in the FastAPI application.

Models provide:
- Automatic validation
- Type safety  
- Auto-generated documentation
- Serialization/deserialization
"""

from .htl import HTLCalcResponse, HTLCountyResponse, HTLUnit
from .combustion import CombustionCalcResponse, CombustionCountyResponse, CombustionUnit, WasteType
from .fermentation import FermentationCalcResponse, FermentationCountyResponse, FermentationUnit

__all__ = [
    "HTLCalcResponse",
    "HTLCountyResponse", 
    "HTLUnit",
    "CombustionCalcResponse",
    "CombustionCountyResponse",
    "CombustionUnit",
    "WasteType",
    "FermentationCalcResponse",
    "FermentationCountyResponse",
    "FermentationUnit"
]