"""Schema validation utilities for pytest-aitest reports.

This module provides functions to validate report data against the JSON Schema.
"""

from __future__ import annotations

import json
from importlib.resources import files
from pathlib import Path
from typing import Any

from jsonschema import ValidationError, validate

# Schema version - must match the const in report.schema.json
SCHEMA_VERSION = "3.0"


class SchemaValidationError(Exception):
    """Raised when report data fails schema validation."""

    def __init__(self, message: str, errors: list[str] | None = None):
        super().__init__(message)
        self.errors = errors or []


def get_schema_path() -> Path:
    """Get the path to the JSON Schema file."""
    # Try relative path from this file first (development and installed)
    schema_path = Path(__file__).parent.parent.parent / "schema" / "report.schema.json"
    if schema_path.exists():
        return schema_path
    
    # Try package resources (installed package with bundled schema)
    try:
        from importlib.resources import files
        schema_file = files("pytest_aitest").joinpath("schema", "report.schema.json")
        if hasattr(schema_file, "read_text"):
            return Path(str(schema_file))
    except (TypeError, FileNotFoundError, ModuleNotFoundError):
        pass

    # Fall back to cwd-relative
    return Path("schema/report.schema.json")


def load_schema() -> dict[str, Any]:
    """Load the JSON Schema from package resources or file system."""
    schema_path = get_schema_path()
    return json.loads(schema_path.read_text(encoding="utf-8"))


def get_schema_version() -> str:
    """Get the current schema version."""
    return SCHEMA_VERSION


def validate_report(data: dict[str, Any]) -> None:
    """Validate report data against the JSON Schema.

    Args:
        data: Report data as a dictionary

    Raises:
        SchemaValidationError: If validation fails
    """
    try:
        schema = load_schema()
        validate(instance=data, schema=schema)
    except ValidationError as e:
        raise SchemaValidationError(
            f"Report validation failed: {e.message}",
            errors=[str(e)],
        ) from e


def validate_schema_version(data: dict[str, Any]) -> str:
    """Check that the schema version is compatible.

    Args:
        data: Report data with schema_version field

    Returns:
        The schema version found in the data

    Raises:
        SchemaValidationError: If version is missing or incompatible
    """
    version = data.get("schema_version")
    if not version:
        raise SchemaValidationError(
            "Missing schema_version field in report data"
        )

    if version != SCHEMA_VERSION:
        raise SchemaValidationError(
            f"Incompatible schema version: {version} (expected {SCHEMA_VERSION})"
        )

    return version
