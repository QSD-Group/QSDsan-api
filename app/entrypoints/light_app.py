"""
Lambda entrypoint: health + all three county-lookup endpoints.

No biosteam/exposan/biorefineries in this deployable's dependency set at
all — see Dockerfile.lambda.light.
"""

from app.app_factory import create_app
from app.routers import health, htl_lookup, combustion_lookup, fermentation_lookup

app = create_app()

app.include_router(htl_lookup.router, prefix="/api/v1", tags=["HTL"])
app.include_router(combustion_lookup.router, prefix="/api/v1", tags=["Combustion"])
app.include_router(fermentation_lookup.router, prefix="/api/v1", tags=["Fermentation"])
app.include_router(health.router, tags=["Health"])
