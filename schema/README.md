# pytest-aitest Report Schema

This directory contains the JSON Schema that defines the report format for pytest-aitest.

## Schema-First Development

The schema is the **single source of truth**. Python models are generated from it.

### Workflow: Adding a New Field

1. **Edit the schema**: Update `report.schema.json` with the new field
2. **Regenerate models**: Run `python scripts/generate_models.py`
3. **Update engine**: Populate the new field in `execution/engine.py`
4. **Regenerate fixtures**: Run integration tests and update fixtures
5. **Commit all**: Schema + generated code + fixtures together

### Version Bumping Rules

| Change Type | Example | Version Bump |
|-------------|---------|--------------|
| Add optional field | `duration_ms` to `ToolCall` | Patch (2.0 → 2.1) |
| Add required field | New required property | Minor (2.0 → 3.0) |
| Remove/rename field | Rename `cost_usd` → `total_cost` | Major (2.x → 3.0) |
| Add new enum value | New `outcome` value | Patch |

### Current Version

**Schema Version: 2.0**

### Validation

The schema is validated by CI:
- Schema file is valid JSON Schema
- Generated models match schema
- All fixtures in `tests/fixtures/reports/` validate against schema
- Round-trip serialization works (model → JSON → model)

### Tools

```bash
# Generate Pydantic models from schema
python scripts/generate_models.py

# Check if generated code is up-to-date (CI mode)
python scripts/generate_models.py --check

# Validate a JSON file against the schema
python -c "
from pytest_aitest.schema import validate_report
import json
with open('report.json') as f:
    validate_report(json.load(f))
print('Valid!')
"
```
