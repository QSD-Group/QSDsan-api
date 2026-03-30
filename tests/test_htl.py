"""
Tests for HTL (Hydrothermal Liquefaction) service functions and FastAPI routes.

Service tests cover the lightweight conversion/validation functions directly.
Route tests mock the heavy exposan computation to keep tests fast.
"""
import pytest
from unittest.mock import patch


# ---------------------------------------------------------------------------
# Service unit tests (no mocking — these are fast, pure-Python functions)
# ---------------------------------------------------------------------------

class TestHTLConversion:
    """Tests for htl_convert_sludge_mass_kg_hr."""

    @pytest.fixture(autouse=True)
    def setup(self):
        from app.services.htl_service import htl_convert_sludge_mass_kg_hr
        self.convert = htl_convert_sludge_mass_kg_hr

    def test_kghr_returns_same_value(self):
        assert self.convert(150.0, "kghr") == 150.0

    def test_tons_to_kghr(self):
        expected = 150.0 * 907.185 / 8760
        assert abs(self.convert(150.0, "tons") - expected) < 0.001

    def test_tonnes_to_kghr(self):
        expected = 150.0 * 1000 / 8760
        assert abs(self.convert(150.0, "tonnes") - expected) < 0.001

    def test_mgd_to_kghr(self):
        expected = 1.0 * 3.78541e6 / 24
        assert abs(self.convert(1.0, "mgd") - expected) < 1.0

    def test_m3d_to_kghr(self):
        expected = 100.0 * 1000 / 24
        assert abs(self.convert(100.0, "m3d") - expected) < 0.001

    def test_unit_case_insensitive(self):
        assert self.convert(100.0, "KGHR") == self.convert(100.0, "kghr")

    def test_invalid_unit_raises_value_error(self):
        with pytest.raises(ValueError):
            self.convert(100.0, "xyz")

    def test_non_numeric_mass_raises_type_error(self):
        with pytest.raises(TypeError):
            self.convert("100", "kghr")

    def test_non_string_unit_raises_type_error(self):
        with pytest.raises(TypeError):
            self.convert(100.0, 123)


# ---------------------------------------------------------------------------
# Route tests (mock the exposan htl_calc to avoid slow computation)
# ---------------------------------------------------------------------------

class TestHTLCalcEndpoint:
    """Tests for GET /api/v1/htl/calc."""

    def test_valid_request_returns_200(self, client):
        with patch("app.routers.htl.htl_convert_kg", return_value=100.0), \
             patch("app.routers.htl.htl_calc", return_value=(2.5, 8.0)):
            response = client.get("/api/v1/htl/calc?sludge=100&unit=kghr")
        assert response.status_code == 200

    def test_response_has_expected_fields(self, client):
        with patch("app.routers.htl.htl_convert_kg", return_value=100.0), \
             patch("app.routers.htl.htl_calc", return_value=(2.5, 8.0)):
            response = client.get("/api/v1/htl/calc?sludge=100")
        data = response.json()
        assert "sludge" in data
        assert "price" in data
        assert "gwp" in data

    def test_response_values_match_mocked_service(self, client):
        with patch("app.routers.htl.htl_convert_kg", return_value=100.0), \
             patch("app.routers.htl.htl_calc", return_value=(2.5, 8.0)):
            response = client.get("/api/v1/htl/calc?sludge=100&unit=kghr")
        data = response.json()
        assert data["sludge"] == 100.0
        assert data["price"] == 2.5
        assert data["gwp"] == 8.0

    def test_default_unit_is_kghr(self, client):
        with patch("app.routers.htl.htl_convert_kg", return_value=100.0) as mock_convert, \
             patch("app.routers.htl.htl_calc", return_value=(2.5, 8.0)):
            client.get("/api/v1/htl/calc?sludge=100")
        mock_convert.assert_called_once_with(100.0, "kghr")

    def test_missing_sludge_returns_422(self, client):
        response = client.get("/api/v1/htl/calc")
        assert response.status_code == 422

    def test_zero_sludge_returns_422(self, client):
        response = client.get("/api/v1/htl/calc?sludge=0")
        assert response.status_code == 422

    def test_negative_sludge_returns_422(self, client):
        response = client.get("/api/v1/htl/calc?sludge=-10")
        assert response.status_code == 422

    def test_invalid_unit_returns_422(self, client):
        response = client.get("/api/v1/htl/calc?sludge=100&unit=invalid")
        assert response.status_code == 422

    def test_all_valid_units(self, client):
        for unit in ["kghr", "tons", "tonnes", "mgd", "m3d"]:
            with patch("app.routers.htl.htl_convert_kg", return_value=100.0), \
                 patch("app.routers.htl.htl_calc", return_value=(2.5, 8.0)):
                response = client.get(f"/api/v1/htl/calc?sludge=100&unit={unit}")
            assert response.status_code == 200, f"Failed for unit={unit}"


class TestHTLCountyEndpoint:
    """Tests for GET /api/v1/htl/county."""

    def test_valid_county_returns_200(self, client):
        with patch("app.routers.htl.htl_county", return_value=("Atlantic", 8991.7, 162.6, 176.1)):
            response = client.get("/api/v1/htl/county?county_name=Atlantic")
        assert response.status_code == 200

    def test_response_has_expected_fields(self, client):
        with patch("app.routers.htl.htl_county", return_value=("Atlantic", 8991.7, 162.6, 176.1)):
            response = client.get("/api/v1/htl/county?county_name=Atlantic")
        data = response.json()
        assert "county_name" in data
        assert "sludge" in data
        assert "price" in data
        assert "gwp" in data

    def test_response_values_match_mocked_service(self, client):
        with patch("app.routers.htl.htl_county", return_value=("Atlantic", 8991.7, 162.6, 176.1)):
            response = client.get("/api/v1/htl/county?county_name=Atlantic")
        data = response.json()
        assert data["county_name"] == "Atlantic"
        assert data["sludge"] == 8991.7
        assert data["price"] == 162.6
        assert data["gwp"] == 176.1

    def test_county_name_forwarded_to_service(self, client):
        with patch("app.routers.htl.htl_county", return_value=("Essex", 5000.0, 150.0, 160.0)) as mock_county:
            client.get("/api/v1/htl/county?county_name=Essex")
        mock_county.assert_called_once_with("Essex")

    def test_missing_county_name_returns_422(self, client):
        response = client.get("/api/v1/htl/county")
        assert response.status_code == 422

    def test_unknown_county_returns_404(self, client):
        with patch("app.routers.htl.htl_county", side_effect=ValueError("County not found")):
            response = client.get("/api/v1/htl/county?county_name=InvalidCounty")
        assert response.status_code == 404
