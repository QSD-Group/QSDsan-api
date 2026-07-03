"""
FastAPI Routers Package

This package contains all FastAPI routers for the application endpoints.
Routers replace Flask blueprints and provide better organization and
automatic documentation generation.

Available routers:
- htl_calc: HTL (Hydrothermal Liquefaction) calculation endpoints
- htl_lookup: HTL county lookup endpoints
- combustion_calc: Combustion calculation endpoints
- combustion_lookup: Combustion county lookup endpoints
- fermentation: Fermentation processing endpoints
- health: Health monitoring and metrics endpoints
"""

# Import routers for easy access
from . import htl_calc, htl_lookup, combustion_calc, combustion_lookup, fermentation, health

__all__ = ["htl_calc", "htl_lookup", "combustion_calc", "combustion_lookup", "fermentation", "health"]