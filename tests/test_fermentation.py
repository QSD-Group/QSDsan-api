"""
Tests for Fermentation service functions and FastAPI routes.

Service tests cover the lightweight conversion/validation functions directly.
Route tests mock the heavy biorefineries computation to keep tests fast.
"""
import pytest
from unittest.mock import patch


# Shared mock return values
# fermentation_calc returns (ethanol MM gal/yr, price $/gal, GWP lb CO2e/gal)
_CALC_RESULT = (0.65, 84.66, 13.63)
# fermentation_county returns (county_name, dry_tonnes, ethanol, price, gwp)
_COUNTY_RESULT = ("Atlantic", 50000, 1.2, 84.66, 13.63)


# ---------------------------------------------------------------------------
# Service unit tests (no mocking — fast, pure-Python functions)
# ---------------------------------------------------------------------------

class TestFermentationConversion:
    """Tests for fermentation_convert_feedstock_kg_hr."""

    @pytest.fixture(autouse=True)
    def setup(self):
        from app.services.fermentation_service import fermentation_convert_feedstock_kg_hr
        self.convert = fermentation_convert_feedstock_kg_hr

    def test_kghr_returns_same_value(self):
        assert self.convert(100.0, "kghr") == 100.0

    def test_tons_to_kghr(self):
        expected = 100.0 * 907.185 / 8760
        assert abs(self.convert(100.0, "tons") - expected) < 0.001

    def test_tonnes_to_kghr(self):
        expected = 100.0 * 1000 / 8760
        assert abs(self.convert(100.0, "tonnes") - expected) < 0.001

    def test_invalid_unit_raises_value_error(self):
        # mgd/m3d are not supported for fermentation (only kghr/tons/tonnes)
        with pytest.raises(ValueError):
            self.convert(100.0, "mgd")

    def test_non_numeric_feedstock_raises_type_error(self):
        with pytest.raises(TypeError):
            self.convert("100", "kghr")

    def test_non_string_unit_raises_type_error(self):
        with pytest.raises(TypeError):
            self.convert(100.0, 123)


# ---------------------------------------------------------------------------
# Route tests (mock the biorefineries CellulosicEthanol computation)
# ---------------------------------------------------------------------------

class TestFermentationCalcEndpoint:
    """Tests for GET /api/v1/fermentation/calc."""

    def test_valid_request_returns_200(self, client):
        with patch("app.routers.fermentation.fermentation_kg", return_value=100.0), \
             patch("app.routers.fermentation.fermentation_calc", return_value=_CALC_RESULT):
            response = client.get("/api/v1/fermentation/calc?mass=100&unit=kghr")
        assert response.status_code == 200

    def test_response_has_expected_fields(self, client):
        with patch("app.routers.fermentation.fermentation_kg", return_value=100.0), \
             patch("app.routers.fermentation.fermentation_calc", return_value=_CALC_RESULT):
            response = client.get("/api/v1/fermentation/calc?mass=100")
        data = response.json()
        assert "mass" in data
        assert "ethanol" in data
        assert "price" in data
        assert "gwp" in data

    def test_response_values_match_mocked_service(self, client):
        with patch("app.routers.fermentation.fermentation_kg", return_value=100.0), \
             patch("app.routers.fermentation.fermentation_calc", return_value=_CALC_RESULT):
            response = client.get("/api/v1/fermentation/calc?mass=100&unit=kghr")
        data = response.json()
        assert data["mass"] == 100.0
        assert data["ethanol"] == 0.65
        assert data["price"] == pytest.approx(84.66)
        assert data["gwp"] == pytest.approx(13.63)

    def test_mass_converted_before_passing_to_service(self, client):
        with patch("app.routers.fermentation.fermentation_kg", return_value=11.41) as mock_convert, \
             patch("app.routers.fermentation.fermentation_calc", return_value=_CALC_RESULT):
            client.get("/api/v1/fermentation/calc?mass=100&unit=tonnes")
        mock_convert.assert_called_once_with(100.0, "tonnes")

    def test_missing_mass_returns_422(self, client):
        response = client.get("/api/v1/fermentation/calc")
        assert response.status_code == 422

    def test_zero_mass_returns_422(self, client):
        response = client.get("/api/v1/fermentation/calc?mass=0")
        assert response.status_code == 422

    def test_negative_mass_returns_422(self, client):
        response = client.get("/api/v1/fermentation/calc?mass=-10")
        assert response.status_code == 422

    def test_invalid_unit_returns_422(self, client):
        # mgd is valid for HTL/combustion but not for fermentation
        response = client.get("/api/v1/fermentation/calc?mass=100&unit=mgd")
        assert response.status_code == 422

    def test_all_valid_units(self, client):
        for unit in ["kghr", "tons", "tonnes"]:
            with patch("app.routers.fermentation.fermentation_kg", return_value=100.0), \
                 patch("app.routers.fermentation.fermentation_calc", return_value=_CALC_RESULT):
                response = client.get(f"/api/v1/fermentation/calc?mass=100&unit={unit}")
            assert response.status_code == 200, f"Failed for unit={unit}"


class TestFermentationCountyEndpoint:
    """Tests for GET /api/v1/fermentation/county."""

    def test_valid_county_returns_200(self, client):
        with patch("app.routers.fermentation.fermentation_county", return_value=_COUNTY_RESULT):
            response = client.get("/api/v1/fermentation/county?county_name=Atlantic")
        assert response.status_code == 200

    def test_response_has_expected_fields(self, client):
        with patch("app.routers.fermentation.fermentation_county", return_value=_COUNTY_RESULT):
            response = client.get("/api/v1/fermentation/county?county_name=Atlantic")
        data = response.json()
        assert "county_name" in data
        assert "mass" in data
        assert "ethanol" in data
        assert "price" in data
        assert "gwp" in data

    def test_response_values_match_mocked_service(self, client):
        with patch("app.routers.fermentation.fermentation_county", return_value=_COUNTY_RESULT):
            response = client.get("/api/v1/fermentation/county?county_name=Atlantic")
        data = response.json()
        assert data["county_name"] == "Atlantic"
        assert data["mass"] == 50000
        assert data["ethanol"] == pytest.approx(1.2)

    def test_county_name_forwarded_to_service(self, client):
        with patch("app.routers.fermentation.fermentation_county", return_value=_COUNTY_RESULT) as mock_county:
            client.get("/api/v1/fermentation/county?county_name=Bergen")
        mock_county.assert_called_once_with("Bergen")

    def test_missing_county_name_returns_422(self, client):
        response = client.get("/api/v1/fermentation/county")
        assert response.status_code == 422

    def test_unknown_county_returns_404(self, client):
        with patch("app.routers.fermentation.fermentation_county", side_effect=ValueError("County not found")):
            response = client.get("/api/v1/fermentation/county?county_name=InvalidCounty")
        assert response.status_code == 404
