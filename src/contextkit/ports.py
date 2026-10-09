"""Storage and projection contracts; implementations must isolate scopes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from contextkit.models import Scope, SubjectState


class SubjectStore(Protocol):
    def load(self, scope: Scope) -> SubjectState: ...

    def compare_and_swap(
        self, scope: Scope, expected_revision: int, state: SubjectState
    ) -> bool:
        """Atomically commit the complete aggregate iff its revision still matches."""
        ...


class SnapshotCache(Protocol):
    def get(self, key: str) -> str | None: ...

    def put(self, key: str, value: str) -> None: ...


@dataclass(frozen=True)
class VectorEntry:
    memory_id: str
    memory_version: int
    vector: tuple[float, ...]


@dataclass(frozen=True)
class VectorHit:
    scope: Scope
    memory_id: str
    memory_version: int
    score: float


class VectorIndex(Protocol):
    def replace(self, scope: Scope, revision: int, entries: tuple[VectorEntry, ...]) -> bool:
        """Replace a scoped projection; reject an older revision atomically."""
        ...

    def search(self, scope: Scope, query: tuple[float, ...], limit: int) -> list[VectorHit]: ...


class Embedder(Protocol):
    def embed(self, text: str) -> tuple[float, ...]: ...
