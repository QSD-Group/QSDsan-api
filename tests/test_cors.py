"""CORS behavior: allow the group frontend origin, block everything else."""
from app.main import ALLOWED_ORIGINS

FRONTEND_ORIGIN = "https://nj-bioenergy.apps.qsdsan.com"
# qsdsan.app is the retired old frontend (now only 301-redirects to the new URL); it must
# NOT be an allowed origin anymore.
RETIRED_ORIGIN = "https://qsdsan.app"
UNKNOWN_ORIGIN = "https://evil.example.com"

# These tests assume the built-in default origin list. If a shell ALLOWED_ORIGINS
# override is present it would cause confusing per-test mismatches, so fail loudly here.
assert FRONTEND_ORIGIN in ALLOWED_ORIGINS, (
    "ALLOWED_ORIGINS was overridden by the environment; unset it to run the CORS "
    "tests against the built-in defaults."
)


def test_cors_allows_new_frontend_origin(client):
    r = client.get("/health", headers={"Origin": FRONTEND_ORIGIN})
    assert r.headers.get("access-control-allow-origin") == FRONTEND_ORIGIN
    # allow_credentials must stay on for allowed origins (the original risk vector).
    assert r.headers.get("access-control-allow-credentials") == "true"


def test_cors_blocks_retired_qsdsan_app_origin(client):
    r = client.get("/health", headers={"Origin": RETIRED_ORIGIN})
    assert "access-control-allow-origin" not in r.headers


def test_cors_blocks_unknown_origin(client):
    r = client.get("/health", headers={"Origin": UNKNOWN_ORIGIN})
    assert "access-control-allow-origin" not in r.headers
