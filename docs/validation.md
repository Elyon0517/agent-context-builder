# Validation

## Version 0.1.1 checks

The vector input hardening was validated on October 9, 2026 in the same local environment as the initial release.

- 114 tests passed, including the three live MongoDB and Redis integration tests.
- Eleven additional regression cases cover mutable vector containers, mutable projection entries, invalid coordinates, identifiers, and memory versions.
- Ruff, strict mypy, all three service-free examples, and source/wheel builds passed.

Mutable inputs are rejected before projection replacement, so a rejected update preserves the current index. Empty projections and valid finite vectors remain supported.

## Initial release checks

The initial implementation was validated on October 9, 2026 with Python 3.12.13 on macOS, MongoDB 8.2.0, and Redis 8.2.1.

- 103 tests passed, including three live integration tests.
- Ruff lint and formatting checks passed.
- Strict mypy checks passed for the library.
- The three service-free examples completed successfully.
- A source distribution and wheel were built successfully.

MongoDB and Redis ran as temporary loopback-only processes on dynamically selected ports, using temporary data directories. They were stopped after the test run. No production service was used.

These checks establish the tested behaviors in this environment; they do not establish scalability, all Python-version compatibility, or quality of a language model's use of context. The default suite skips live integration tests unless local test endpoints are supplied.

## Reproducing the checks

See the README for installation and test commands. The live test database and Redis key use unique generated names and are removed by the tests. Point the integration environment variables at isolated test servers.
