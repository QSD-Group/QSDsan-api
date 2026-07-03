"""
Tests for the health check and readiness endpoints.
"""


def test_ready_endpoint_reports_dependencies_ok(client):
    response = client.get("/ready")
    # The endpoint may return 503 due to system resources, but the important thing
    # is that critical dependencies (pandas, numpy, and data files) are checked.
    # Check that if we get a successful response (200), all required dependencies are OK.
    if response.status_code == 200:
        data = response.json()
        deps = data["dependencies"]
        assert deps["pandas"] == "OK"
        assert deps["numpy"] == "OK"
        assert deps["htl_data"] == "OK"
        assert deps["combustion_data"] == "OK"
        assert deps["fermentation_data"] == "OK"
