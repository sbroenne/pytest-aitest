from pytest_aitest.core.serialization import DictWithAttrAccess, to_dict_with_attr
import json
from pathlib import Path

# Load JSON fixture
data = json.loads(Path("tests/fixtures/reports/01_single_agent.json").read_text())
print(f"Type of loaded data: {type(data)}")
print(f"Type of data['summary']: {type(data['summary'])}")

# Wrap it
wrapped = to_dict_with_attr(data)
print(f"Type of wrapped: {type(wrapped)}")
print(f"Type of wrapped['summary']: {type(wrapped['summary'])}")
print(f"Has summary attr: {hasattr(wrapped, 'summary')}")
if hasattr(wrapped, 'summary'):
    print(f"wrapped.summary type: {type(wrapped.summary)}")
    print(f"wrapped.summary has failed: {hasattr(wrapped.summary, 'failed')}")
    print(f"wrapped.summary['failed']: {wrapped.summary['failed']}")
    print(f"wrapped.summary.failed: {wrapped.summary.failed}")
