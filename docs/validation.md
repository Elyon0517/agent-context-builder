# Validation

## 0.2.0 — October 9, 2026

- Python 3.12.13 on macOS: 123 passed, including three live MongoDB/Redis integration tests.
- Ruff lint and format checks, strict mypy, examples and source/wheel builds passed.
- Service-free examples use synthetic records, not production data.

Live services used temporary loopback-only MongoDB and Redis processes with temporary storage and dynamically selected ports. Both were stopped after testing. Default runs skip the three live tests unless isolated endpoints are configured. Tests cover summary overflow, token counter validation, tenant/session isolation and canonical revalidation of selected memory IDs.

Packages are distributed through pinned GitHub releases, not a PyPI publication. Passing these checks does not establish compatibility with every Python version, production scale or downstream model behavior.
