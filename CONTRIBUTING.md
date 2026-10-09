# Contributing

Create a virtual environment and install `.[dev,mongo,redis]`. Before submitting a change, run:

```bash
python -m pytest
python -m ruff check .
python -m ruff format --check .
python -m mypy
```

Add behavior tests for state transitions or adapter contract changes. A useful failure report includes the scope shape with synthetic identifiers, ordered events, expected outcome, actual outcome, and storage implementation. Never include production records, secrets, or private conversation content.

Keep the core independent of a model provider or runtime. New adapters should document their atomicity boundary, failure behavior, scope isolation, and retention behavior. Changes to replay, correction, forgetting, or source authority must update the contracts document.

Optional integration tests run only against explicitly configured test services. Repository changes do not need to add hosted automation.
