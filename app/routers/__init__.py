"""
FastAPI Routers Package

This package contains all FastAPI routers for the application endpoints.
Routers replace Flask blueprints and provide better organization and 
automatic documentation generation.

Available routers:
- htl: HTL (Hydrothermal Liquefaction) processing endpoints
- combustion: Combustion processing endpoints  
- fermentation: Fermentation processing endpoints
- health: Health monitoring and metrics endpoints
"""

# Import routers for easy access
from . import htl, combustion, fermentation, health, v2_example

__all__ = ["htl", "combustion", "fermentation", "health", "v2_example"]