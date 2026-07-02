# Contributing to GuardLine

Thanks for your interest in making GuardLine better. Contributions of all kinds are welcome — new detection patterns, bug fixes, documentation improvements, and feature development.

## Quick Contributions

The easiest way to contribute is by adding new detection patterns. Each pattern is a YAML entry with a regex, severity level, and remediation text. See `docs/ADDING_RULES.md` for a step-by-step guide.

## Development Setup

```bash
# Clone the repo
git clone https://github.com/toutlawbradley/guardline.git
cd guardline

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run linter
ruff check src/
```

## Submitting Changes

1. Fork the repo and create a branch from `main`
2. Write tests for any new functionality
3. Ensure all tests pass and linting is clean
4. Submit a pull request with a clear description of the change

## Reporting Issues

If you find a false positive, a missed detection, or a bug, please open an issue with:

- What you expected to happen
- What actually happened
- A minimal example that reproduces the issue (sanitize any real credentials)

## Code of Conduct

Be respectful, be constructive, and remember that everyone is here to make software more secure.