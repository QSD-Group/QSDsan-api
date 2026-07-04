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
- fermentation_calc: Fermentation calculation endpoints
- fermentation_lookup: Fermentation county lookup endpoints
- health: Health monitoring and metrics endpoints

Deliberately no eager `from . import ...` here: each of the four Lambda
entrypoints (app/entrypoints/*.py) imports only the specific router
module(s) it needs. Since `from app.routers import X` still runs this
__init__.py first regardless of what X is, an eager blanket import here
would force every entrypoint to import all six routers' underlying heavy
service modules (exposan/biosteam/biorefineries together), defeating the
whole point of splitting them into separately-deployable functions with
non-overlapping dependency footprints.
"""