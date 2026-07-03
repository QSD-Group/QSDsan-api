"""
Lambda entrypoint: fermentation calc only. Imports biosteam and the
cellulosic-ethanol biorefinery.
"""

from app.app_factory import create_app
from app.routers import fermentation_calc

app = create_app()

app.include_router(fermentation_calc.router, prefix="/api/v1", tags=["Fermentation"])
