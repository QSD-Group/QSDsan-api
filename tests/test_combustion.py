"""
Tests for Combustion service functions and FastAPI routes.

Service tests verify type/value validation and the dry_mass bug fix.
Route tests mock the heavy biosteam computation to keep tests fast.
"""
import pytest
from unittest.mock import patch


# Shared mock return values
_CALC_RESULT = ("sludge", 100.0, 1677161.41, 0.370, 0.00379)
_COUNTY_RESULT = ("Essex", "sludge", 1234.56, 1677161.41, 0.370, 0.00379)

# Recorded reference output for combustion_calc(1000.0, 'sludge') against a
# correctly-set combustion thermo (see TestCombustionThermoRegression below).
_REFERENCE_RESULT = (
    "sludge", 1000.0, 16771611.411033249, 3.7020225242133353, 0.037930558649726796,
)


# ---------------------------------------------------------------------------
# Regression test: combustion must re-assert its own thermo on every call
# ---------------------------------------------------------------------------

class TestCombustionThermoRegression:
    """Regression test for the shared-process thermo-clobbering bug.

    app.main registers HTL, combustion, and fermentation calc routers in one
    warm process. htl.calc._get_model() and fermentation.calc.
    _get_biorefinery() both replace biosteam's global bst.settings.thermo
    with their own chemical sets. combustion.calc used to only call
    bst.settings.set_thermo(...) the first time combustion_calc_raw ever ran
    (caching a "_chemicals_ready" flag) -- so if another service's thermo
    became active afterward, the next combustion call would build its
    bst.Stream against the wrong chemicals and crash (or, if the other
    thermo happened to share chemical names, silently produce wrong
    numbers). The fix re-asserts bst.settings.set_thermo(cached_chemicals)
    on every call to combustion_calc_raw, not just the first.

    This test simulates "something else changed the global thermo" directly
    (cheaper and more deterministic than actually running htl_calc/
    fermentation_calc) and confirms combustion_calc still succeeds and still
    matches the recorded reference output.
    """

    def test_combustion_survives_foreign_thermo_set_before_it(self):
        import biosteam as bst
        import thermosteam as tmo
        from app.services.combustion.calc import combustion_calc

        # Simulate a different service (HTL/fermentation) having replaced
        # the global thermo with an unrelated chemical set since combustion
        # last ran.
        foreign_chemicals = tmo.Chemicals(['Water', 'Ethanol'])
        bst.settings.set_thermo(foreign_chemicals)

        result = combustion_calc(1000.0, 'sludge')

        assert result[0] == _REFERENCE_RESULT[0]
        assert result[1] == pytest.approx(_REFERENCE_RESULT[1])
        assert result[2] == pytest.approx(_REFERENCE_RESULT[2])
        assert result[3] == pytest.approx(_REFERENCE_RESULT[3])
        assert result[4] == pytest.approx(_REFERENCE_RESULT[4])

    def test_combustion_survives_foreign_thermo_set_between_two_calls(self):
        import biosteam as bst
        import thermosteam as tmo
        from app.services.combustion.calc import combustion_calc

        first = combustion_calc(1000.0, 'sludge')

        foreign_chemicals = tmo.Chemicals(['Water', 'Ethanol'])
        bst.settings.set_thermo(foreign_chemicals)

        second = combustion_calc(1000.0, 'sludge')

        assert first == second


# ---------------------------------------------------------------------------
# Service unit tests
# ---------------------------------------------------------------------------

class TestCombustionCalcService:
    """Tests for combustion_calc service function."""

    def test_dry_mass_is_forwarded_to_raw(self):
        """Regression test: dry_mass must be passed through to combustion_calc_raw.

        Before the fix, food/fog waste types in county lookups would silently
        use the wrong moisture fraction because dry_mass was accepted by
        combustion_calc but never passed down to combustion_calc_raw.
        """
        from app.services.combustion.calc import combustion_calc
        with patch(
            "app.services.combustion.calc.combustion_calc_raw",
            return_value=(100.0, 0.5, 0.005),
        ) as mock_raw:
            combustion_calc(1000.0, "sludge", dry_mass=500.0)
        _, kwargs = mock_raw.call_args
        assert kwargs.get("dry_mass_in_kg_hr") == 500.0

    def test_invalid_waste_type_raises_value_error(self):
        from app.services.combustion.calc import combustion_calc
        with patch("app.services.combustion.calc.combustion_calc_raw", return_value=(100.0, 0.5, 0.005)):
            with pytest.raises(ValueError):
                combustion_calc(1000.0, "invalid_type")

    def test_non_string_waste_type_raises_type_error(self):
        from app.services.combustion.calc import combustion_calc
        with pytest.raises(TypeError):
            combustion_calc(1000.0, 123)

    def test_non_numeric_mass_raises_type_error(self):
        from app.services.combustion.calc import combustion_calc
        with pytest.raises(TypeError):
            combustion_calc("1000", "sludge")

    def test_zero_mass_raises_value_error(self):
        from app.services.combustion.calc import combustion_calc
        with pytest.raises(ValueError):
            combustion_calc(0.0, "sludge")

    def test_negative_mass_raises_value_error(self):
        from app.services.combustion.calc import combustion_calc
        with pytest.raises(ValueError):
            combustion_calc(-100.0, "sludge")


# ---------------------------------------------------------------------------
# Route tests (mock the biosteam computation)
# ---------------------------------------------------------------------------

class TestCombustionCalcEndpoint:
    """Tests for GET /api/v1/combustion/calc."""

    def test_valid_request_returns_200(self, client):
        with patch("app.routers.combustion_calc.combustion_calc", return_value=_CALC_RESULT):
            response = client.get("/api/v1/combustion/calc?mass=100&unit=kghr&waste_type=sludge")
        assert response.status_code == 200

    def test_response_has_expected_fields(self, client):
        with patch("app.routers.combustion_calc.combustion_calc", return_value=_CALC_RESULT):
            response = client.get("/api/v1/combustion/calc?mass=100")
        data = response.json()
        assert "mass" in data
        assert "waste_type" in data
        assert "electricity" in data
        assert "emissions" in data
        assert "percent" in data

    def test_response_values_match_mocked_service(self, client):
        with patch("app.routers.combustion_calc.combustion_calc", return_value=_CALC_RESULT):
            response = client.get("/api/v1/combustion/calc?mass=100&waste_type=sludge")
        data = response.json()
        assert data["waste_type"] == "sludge"
        assert data["mass"] == 100.0
        assert data["electricity"] == pytest.approx(1677161.41)

    def test_default_unit_is_kghr(self, client):
        with patch("app.routers.combustion_calc.combustion_calc", return_value=_CALC_RESULT):
            response = client.get("/api/v1/combustion/calc?mass=100")
        assert response.status_code == 200

    def test_default_waste_type_is_sludge(self, client):
        with patch("app.routers.combustion_calc.combustion_calc", return_value=_CALC_RESULT) as mock_calc:
            client.get("/api/v1/combustion/calc?mass=100")
        args, _ = mock_calc.call_args
        assert args[1] == "sludge"

    def test_missing_mass_returns_422(self, client):
        response = client.get("/api/v1/combustion/calc")
        assert response.status_code == 422

    def test_zero_mass_returns_422(self, client):
        response = client.get("/api/v1/combustion/calc?mass=0")
        assert response.status_code == 422

    def test_negative_mass_returns_422(self, client):
        response = client.get("/api/v1/combustion/calc?mass=-10")
        assert response.status_code == 422

    def test_invalid_unit_returns_422(self, client):
        response = client.get("/api/v1/combustion/calc?mass=100&unit=invalid")
        assert response.status_code == 422

    def test_invalid_waste_type_returns_422(self, client):
        response = client.get("/api/v1/combustion/calc?mass=100&waste_type=invalid")
        assert response.status_code == 422

    def test_all_valid_waste_types(self, client):
        for waste_type in ["sludge", "food", "fog", "green", "manure"]:
            mock_result = (waste_type, 100.0, 1677161.41, 0.37, 0.0038)
            with patch("app.routers.combustion_calc.combustion_calc", return_value=mock_result):
                response = client.get(f"/api/v1/combustion/calc?mass=100&waste_type={waste_type}")
            assert response.status_code == 200, f"Failed for waste_type={waste_type}"

    def test_all_valid_units(self, client):
        for unit in ["kghr", "tons", "tonnes", "mgd", "m3d"]:
            with patch("app.routers.combustion_calc.combustion_calc", return_value=_CALC_RESULT):
                response = client.get(f"/api/v1/combustion/calc?mass=100&unit={unit}")
            assert response.status_code == 200, f"Failed for unit={unit}"


class TestCombustionCountyEndpoint:
    """Tests for GET /api/v1/combustion/county."""

    def test_valid_county_returns_200(self, client):
        with patch("app.routers.combustion_lookup.combustion_county", return_value=_COUNTY_RESULT):
            response = client.get("/api/v1/combustion/county?county_name=Essex&waste_type=sludge")
        assert response.status_code == 200

    def test_response_has_expected_fields(self, client):
        with patch("app.routers.combustion_lookup.combustion_county", return_value=_COUNTY_RESULT):
            response = client.get("/api/v1/combustion/county?county_name=Essex")
        data = response.json()
        assert "county_name" in data
        assert "waste_type" in data
        assert "mass" in data
        assert "electricity" in data
        assert "emissions" in data
        assert "percent" in data

    def test_response_values_match_mocked_service(self, client):
        with patch("app.routers.combustion_lookup.combustion_county", return_value=_COUNTY_RESULT):
            response = client.get("/api/v1/combustion/county?county_name=Essex")
        data = response.json()
        assert data["county_name"] == "Essex"
        assert data["waste_type"] == "sludge"
        assert data["mass"] == 1234.56

    def test_missing_county_name_returns_422(self, client):
        response = client.get("/api/v1/combustion/county")
        assert response.status_code == 422

    def test_unknown_county_returns_404(self, client):
        with patch("app.routers.combustion_lookup.combustion_county", return_value=None):
            response = client.get("/api/v1/combustion/county?county_name=InvalidCounty")
        assert response.status_code == 404

    def test_invalid_waste_type_returns_422(self, client):
        response = client.get("/api/v1/combustion/county?county_name=Essex&waste_type=invalid")
        assert response.status_code == 422

    def test_county_and_waste_type_forwarded_to_service(self, client):
        with patch("app.routers.combustion_lookup.combustion_county", return_value=_COUNTY_RESULT) as mock_county:
            client.get("/api/v1/combustion/county?county_name=Essex&waste_type=food")
        args, _ = mock_county.call_args
        assert args[0] == "Essex"
        assert args[1] == "food"
