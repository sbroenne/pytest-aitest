# Contributing to pytest-aitest

## Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/sbroenne/pytest-aitest.git
   cd pytest-aitest
   ```

2. Install in editable mode with dev dependencies:
   ```bash
   uv sync --all-extras
   ```

   This installs the package from your local source code. Any changes you make to `src/pytest_aitest/` are immediately available — no reinstall needed.

3. Install pre-commit hooks:
   ```bash
   pre-commit install
   ```

### Editable Install Explained

Python has two install modes:

| Mode | Command | Use case |
|------|---------|----------|
| **Regular** | `uv add pytest-aitest` | End users, pulls from PyPI |
| **Editable** | `uv sync` (in project dir) | Developers, uses local source |

With editable mode, Python points to your source folder instead of copying files. Edit code → run tests → see changes instantly.

### Using in Other Projects

To test your local changes in another project while developing:

```bash
# In your other project directory
cd d:\source\my-mcp-server

# Add pytest-aitest as an editable dependency
uv add --editable d:\source\pytest-aitest
```

This adds a local reference to your `pyproject.toml`:
```toml
dependencies = [
    "pytest-aitest @ file:///d:/source/pytest-aitest",
]
```

Now your other project uses your local source. Changes to pytest-aitest are immediately available — no reinstall needed.

## Code Quality

This project uses automated tools to maintain code quality:

- **[Ruff](https://docs.astral.sh/ruff/)** — Linting and formatting
- **[Pyright](https://github.com/microsoft/pyright)** — Type checking
- **[pre-commit](https://pre-commit.com/)** — Git hooks for automated checks

### Running Checks Manually

```bash
# Run all pre-commit hooks
pre-commit run --all-files

# Or run individual tools
ruff check .                 # Linting
ruff format .                # Formatting
pyright                      # Type checking
```

### Pre-commit Hooks

Pre-commit hooks run automatically on `git commit`. If a hook fails, fix the issues and commit again.

The hooks will:
1. **ruff** — Auto-fix linting issues where possible
2. **ruff-format** — Format code consistently
3. **pyright** — Check types

## Running Tests

```bash
# Run unit tests (fast, no LLM calls)
pytest tests/unit/ -v

# Run integration tests (requires LLM credentials)
pytest tests/integration/ -v

# Run all tests
pytest -v
```

For detailed information about the test architecture, including the four-layer testing system and test fixtures, see **[Testing Architecture](docs/testing.md)**.

### Integration Tests

Integration tests require LLM provider credentials. Set up at least one:

```bash
# Azure OpenAI (uses Entra ID - no API key needed)
export AZURE_API_BASE=https://your-resource.cognitiveservices.azure.com
az login

# Google Vertex AI
export GOOGLE_CLOUD_PROJECT=your-project-id
gcloud auth application-default login
```

## Project Structure

```
pytest-aitest/
├── src/pytest_aitest/
│   ├── __init__.py      # Package exports
│   ├── config.py        # Configuration handling
│   ├── engine.py        # Test execution engine
│   ├── fixtures.py      # pytest fixtures
│   ├── plugin.py        # pytest plugin
│   ├── reporting.py     # Report generation
│   ├── result.py        # Test result types
│   └── servers.py       # MCP/CLI server handling
├── tests/
│   ├── unit/            # Unit tests (mocked LLM calls)
│   └── integration/     # Integration tests (real LLM calls)
├── examples/            # Example usage patterns
├── pyproject.toml       # Project configuration
└── .pre-commit-config.yaml
```

## Making Changes

1. Create a branch for your changes
2. Make your changes
3. Ensure all checks pass: `pre-commit run --all-files`
4. Run tests: `pytest tests/unit/ -v`
5. Submit a pull request

All PRs are **squash merged** to keep a clean commit history on main.

## Code Style

- Follow [PEP 8](https://peps.python.org/pep-0008/) (enforced by Ruff)
- Use type hints for all public APIs
- Keep functions focused and small
- Write docstrings for public classes and methods

## Releasing

1. Update version in `src/pytest_aitest/__init__.py` and `pyproject.toml`
2. Create a git tag: `git tag v0.x.x`
3. Push: `git push origin main --tags`
