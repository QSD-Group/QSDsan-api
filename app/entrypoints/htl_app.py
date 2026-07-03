"""
Lambda entrypoint: HTL calc only. Imports exposan.htl/chaospy.
"""

from app.app_factory import create_app
from app.routers import htl_calc

app = create_app()

app.include_router(htl_calc.router, prefix="/api/v1", tags=["HTL"])
