"""
Lambda entrypoint: combustion calc only. Imports biosteam/thermosteam only
(no exposan, no biorefineries — see app/services/combustion/_chemicals.py).
"""

from app.app_factory import create_app
from app.routers import combustion_calc

app = create_app()

app.include_router(combustion_calc.router, prefix="/api/v1", tags=["Combustion"])
