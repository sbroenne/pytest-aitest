"""Tests for JSON schema validation and fixtures."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pytest_aitest.models import SuiteReport
from pytest_aitest.schema import (
    SCHEMA_VERSION,
    SchemaValidationError,
    get_schema_path,
    get_schema_version,
    load_schema,
    validate_report,
    validate_schema_version,
)


class TestSchemaModule:
    """Test schema loading and validation utilities."""

    def test_schema_version_constant(self) -> None:
        """Schema version should be 2.0."""
        assert SCHEMA_VERSION == "2.0"

    def test_get_schema_version(self) -> None:
        """get_schema_version should return current version."""
        assert get_schema_version() == "2.0"

    def test_get_schema_path_exists(self) -> None:
        """Schema file should exist at returned path."""
        path = get_schema_path()
        assert path.exists(), f"Schema not found at {path}"

    def test_load_schema_returns_dict(self) -> None:
        """load_schema should return valid dict."""
        schema = load_schema()
        assert isinstance(schema, dict)
        assert "$schema" in schema
        assert "properties" in schema

    def test_load_schema_has_required_properties(self) -> None:
        """Schema should define required fields."""
        schema = load_schema()
        required = schema.get("required", [])
        assert "schema_version" in required
        assert "name" in required
        assert "timestamp" in required
        assert "tests" in required
        assert "summary" in required


class TestValidateReport:
    """Test report validation against schema."""

    def test_valid_minimal_report(self) -> None:
        """Minimal valid report should pass validation."""
        data = {
            "schema_version": "2.0",
            "name": "test",
            "timestamp": "2026-01-01T00:00:00Z",
            "duration_ms": 1000.0,
            "tests": [],
            "summary": {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "pass_rate": 0.0,
            },
        }
        # Should not raise
        validate_report(data)

    def test_missing_required_field(self) -> None:
        """Missing required field should fail validation."""
        data = {
            "schema_version": "2.0",
            "name": "test",
            # Missing timestamp, duration_ms, tests, summary
        }
        with pytest.raises(SchemaValidationError):
            validate_report(data)

    def test_invalid_schema_version(self) -> None:
        """Invalid schema version should fail."""
        data = {
            "schema_version": "invalid",
            "name": "test",
            "timestamp": "2026-01-01T00:00:00Z",
            "duration_ms": 1000.0,
            "tests": [],
            "summary": {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "pass_rate": 0.0,
            },
        }
        with pytest.raises(SchemaValidationError):
            validate_report(data)

    def test_invalid_test_outcome(self) -> None:
        """Invalid test outcome should fail validation."""
        data = {
            "schema_version": "2.0",
            "name": "test",
            "timestamp": "2026-01-01T00:00:00Z",
            "duration_ms": 1000.0,
            "tests": [
                {
                    "name": "test_foo",
                    "outcome": "invalid_outcome",  # Should be passed/failed/skipped
                    "duration_ms": 100.0,
                }
            ],
            "summary": {
                "total": 1,
                "passed": 0,
                "failed": 1,
                "skipped": 0,
                "pass_rate": 0.0,
            },
        }
        with pytest.raises(SchemaValidationError):
            validate_report(data)


class TestValidateSchemaVersion:
    """Test schema version checking."""

    def test_valid_version(self) -> None:
        """Valid version should return the version."""
        data = {"schema_version": "2.0"}
        assert validate_schema_version(data) == "2.0"

    def test_missing_version(self) -> None:
        """Missing version should raise error."""
        data = {"name": "test"}
        with pytest.raises(SchemaValidationError, match="Missing schema_version"):
            validate_schema_version(data)

    def test_incompatible_version(self) -> None:
        """Incompatible version should raise error."""
        data = {"schema_version": "1.0"}
        with pytest.raises(SchemaValidationError, match="Incompatible schema version"):
            validate_schema_version(data)


class TestFixturesValidation:
    """Test that all committed fixtures are valid."""

    @pytest.fixture
    def fixtures_dir(self) -> Path:
        """Get path to fixtures directory."""
        return Path(__file__).parent.parent / "fixtures" / "reports"

    def test_fixtures_directory_exists(self, fixtures_dir: Path) -> None:
        """Fixtures directory should exist."""
        assert fixtures_dir.exists(), f"Fixtures dir not found: {fixtures_dir}"

    def test_fixtures_are_present(self, fixtures_dir: Path) -> None:
        """At least one fixture file should exist."""
        fixtures = list(fixtures_dir.glob("*.json"))
        assert len(fixtures) > 0, "No fixture files found"

    @pytest.mark.parametrize(
        "fixture_name",
        [
            "01_basic_usage.json",
            "02_model_comparison.json",
            "03_prompt_comparison.json",
            "04_matrix.json",
            "05_sessions.json",
        ],
    )
    def test_fixture_validates_against_schema(
        self, fixtures_dir: Path, fixture_name: str
    ) -> None:
        """Each fixture should validate against the schema."""
        fixture_path = fixtures_dir / fixture_name
        if not fixture_path.exists():
            pytest.skip(f"Fixture {fixture_name} not found")

        data = json.loads(fixture_path.read_text(encoding="utf-8"))
        validate_report(data)  # Should not raise

    @pytest.mark.parametrize(
        "fixture_name",
        [
            "01_basic_usage.json",
            "02_model_comparison.json",
            "03_prompt_comparison.json",
            "04_matrix.json",
            "05_sessions.json",
        ],
    )
    def test_fixture_has_correct_schema_version(
        self, fixtures_dir: Path, fixture_name: str
    ) -> None:
        """Each fixture should have schema version 2.0."""
        fixture_path = fixtures_dir / fixture_name
        if not fixture_path.exists():
            pytest.skip(f"Fixture {fixture_name} not found")

        data = json.loads(fixture_path.read_text(encoding="utf-8"))
        assert data.get("schema_version") == "2.0"

    @pytest.mark.parametrize(
        "fixture_name",
        [
            "01_basic_usage.json",
            "02_model_comparison.json",
            "03_prompt_comparison.json",
            "04_matrix.json",
            "05_sessions.json",
        ],
    )
    def test_fixture_loads_as_pydantic_model(
        self, fixtures_dir: Path, fixture_name: str
    ) -> None:
        """Each fixture should parse as Pydantic SuiteReport."""
        fixture_path = fixtures_dir / fixture_name
        if not fixture_path.exists():
            pytest.skip(f"Fixture {fixture_name} not found")

        data = json.loads(fixture_path.read_text(encoding="utf-8"))
        report = SuiteReport.model_validate(data)
        assert report.schema_version == "2.0"
        assert len(report.tests) > 0

    @pytest.mark.parametrize(
        "fixture_name",
        [
            "01_basic_usage.json",
            "02_model_comparison.json",
            "03_prompt_comparison.json",
            "04_matrix.json",
            "05_sessions.json",
        ],
    )
    def test_fixture_roundtrip_serialization(
        self, fixtures_dir: Path, fixture_name: str
    ) -> None:
        """Loading and re-serializing fixture should produce valid JSON."""
        fixture_path = fixtures_dir / fixture_name
        if not fixture_path.exists():
            pytest.skip(f"Fixture {fixture_name} not found")

        # Load as Pydantic
        data = json.loads(fixture_path.read_text(encoding="utf-8"))
        report = SuiteReport.model_validate(data)

        # Serialize back to JSON
        json_str = report.model_dump_json()
        reparsed = json.loads(json_str)

        # Should still be valid
        validate_report(reparsed)


class TestGeneratedModelsCheck:
    """Test that generated models are up-to-date."""

    def test_generated_models_exist(self) -> None:
        """Generated models file should exist."""
        from pytest_aitest.models import _generated

        assert _generated is not None

    def test_generated_models_match_schema_version(self) -> None:
        """Generated models should match schema version constant."""
        from pytest_aitest.models._generated import PytestAitestReport

        # The schema_version field should be a Literal["2.0"]
        model_schema = PytestAitestReport.model_json_schema()
        version_prop = model_schema["properties"]["schema_version"]
        assert version_prop.get("const") == "2.0"
