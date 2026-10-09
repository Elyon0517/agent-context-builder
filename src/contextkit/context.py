"""Compile versioned application facts and active memories into bounded snapshots."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from contextkit.models import (
    ContextKitError,
    MemoryStatus,
    Scope,
    canonical_json,
    fingerprint,
    require_revision,
    require_text,
)
from contextkit.ports import SnapshotCache, SubjectStore


class SourceStatus(StrEnum):
    AVAILABLE = "available"
    ABSENT = "absent"
    FAILED = "failed"


@dataclass(frozen=True)
class Fact:
    key: str
    value: str
    evidence: tuple[str, ...]
    kind: str = "observation"

    def __post_init__(self) -> None:
        require_text(self.key, "fact key")
        require_text(self.value, "fact value")
        require_text(self.kind, "fact kind")
        if not isinstance(self.evidence, tuple) or not self.evidence:
            raise ValueError("fact requires a nonempty evidence tuple")
        for reference in self.evidence:
            require_text(reference, "evidence reference")


@dataclass(frozen=True)
class SourceResult:
    status: SourceStatus
    revision: str = ""
    facts: tuple[Fact, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.status, SourceStatus):
            raise ValueError("status must be a SourceStatus")
        if not isinstance(self.facts, tuple) or any(
            not isinstance(f, Fact) for f in self.facts
        ):
            raise ValueError("facts must be a tuple of Fact values")
        if self.status == SourceStatus.AVAILABLE:
            require_text(self.revision, "source revision")
        elif self.facts or self.revision:
            raise ValueError("absent and failed sources cannot supply facts or revisions")


@dataclass(frozen=True)
class ContextSource:
    name: str
    authority: int
    keys: tuple[str, ...]
    read: Callable[[Scope], SourceResult]
    required: bool = False

    def __post_init__(self) -> None:
        require_text(self.name, "source name")
        require_revision(self.authority, "authority")
        if not isinstance(self.keys, tuple) or not self.keys:
            raise ValueError("source must declare a nonempty tuple of fact keys")
        for key in self.keys:
            require_text(key, "source fact key")
        if len(set(self.keys)) != len(self.keys):
            raise ValueError("source fact keys must be unique")
        if not callable(self.read):
            raise ValueError("source reader must be callable")


class SourceUnavailable(ContextKitError):
    """A required context source could not be read."""


class ContextBudgetExceeded(ContextKitError):
    """The envelope cannot fit without truncating structured data."""


@dataclass(frozen=True)
class ContextSnapshot:
    id: str
    memory_revision: int
    payload: str

    def to_dict(self) -> dict[str, Any]:
        return dict(json.loads(self.payload))

    def render(self) -> str:
        return self.payload


def _render(value: object) -> str:
    return canonical_json(value).translate(
        {ord("<"): r"\u003c", ord(">"): r"\u003e", ord("&"): r"\u0026"}
    )


class ContextCompiler:
    def __init__(
        self,
        store: SubjectStore,
        *,
        sources: tuple[ContextSource, ...] = (),
        cache: SnapshotCache | None = None,
    ) -> None:
        if len({source.name for source in sources}) != len(sources):
            raise ValueError("source names must be unique")
        self.store = store
        self.sources = tuple(sorted(sources, key=lambda s: (-s.authority, s.name)))
        self.cache = cache

    def compile(
        self,
        scope: Scope,
        *,
        request: str = "",
        resource: str | None = None,
        max_chars: int = 8000,
        memory_ids: tuple[str, ...] | None = None,
    ) -> ContextSnapshot:
        require_revision(max_chars, "max_chars", 1)
        if not isinstance(request, str) or (
            resource is not None and not isinstance(resource, str)
        ):
            raise ValueError("request and resource must be text")
        if memory_ids is not None and (
            not isinstance(memory_ids, tuple)
            or any(not isinstance(value, str) or not value for value in memory_ids)
        ):
            raise ValueError("memory_ids must be a tuple of nonempty IDs")
        state = self.store.load(scope)
        results: list[tuple[ContextSource, SourceResult]] = []
        for source in self.sources:
            try:
                result = source.read(scope)
            except Exception:
                result = SourceResult(SourceStatus.FAILED)
            if not isinstance(result, SourceResult):
                raise ValueError(f"source {source.name} returned an invalid result")
            if source.required and result.status == SourceStatus.FAILED:
                raise SourceUnavailable(source.name)
            if any(fact.key not in source.keys for fact in result.facts):
                raise ValueError(f"source {source.name} returned an undeclared fact key")
            if len({fact.key for fact in result.facts}) != len(result.facts):
                raise ValueError(f"source {source.name} returned duplicate fact keys")
            results.append((source, result))

        blocked: dict[str, int] = {}
        for source, result in results:
            if result.status == SourceStatus.FAILED:
                for key in source.keys:
                    blocked[key] = max(blocked.get(key, -1), source.authority)

        winners: dict[str, dict[str, Any]] = {}
        conflicts: set[str] = set()
        for source, result in results:
            for fact in result.facts:
                if blocked.get(fact.key, -1) >= source.authority:
                    continue
                previous = winners.get(fact.key)
                if previous is not None:
                    if previous["value"] != fact.value:
                        conflicts.add(fact.key)
                    continue
                winners[fact.key] = {
                    "key": fact.key,
                    "value": fact.value,
                    "kind": fact.kind,
                    "source": source.name,
                    "authority": source.authority,
                    "evidence": list(fact.evidence),
                }

        facts = sorted(winners.values(), key=lambda f: (-f["authority"], f["key"]))
        memories = [
            {
                "id": memory.id,
                "version": memory.version,
                "content": memory.content,
                "kind": memory.kind,
                "evidence": list(memory.evidence),
                "confidence": memory.confidence,
                "user_override": memory.user_override,
            }
            for memory in sorted(
                state.memories.values(),
                key=lambda m: (not m.user_override, -m.confidence, m.id),
            )
            if memory.status == MemoryStatus.ACTIVE
            and (memory_ids is None or memory.id in memory_ids)
        ]
        envelope: dict[str, Any] = {
            "schema_version": 1,
            "data_role": "untrusted_context",
            "scope": {"tenant": scope.tenant, "subject": scope.subject},
            "memory_revision": state.revision,
            "current_request": request,
            "resource": resource,
            "sources": {
                source.name: {"status": result.status.value, "revision": result.revision}
                for source, result in results
            },
            "conflicts": sorted(conflicts),
            "blocked_keys": sorted(blocked),
            "facts": facts,
            "memories": memories,
            "omitted_facts": 0,
            "omitted_memories": 0,
        }
        payload = _render(envelope)
        while len(payload) > max_chars and (memories or facts):
            if memories:
                memories.pop()
                envelope["omitted_memories"] += 1
            else:
                facts.pop()
                envelope["omitted_facts"] += 1
            payload = _render(envelope)
        if len(payload) > max_chars:
            raise ContextBudgetExceeded("request and envelope exceed max_chars")
        snapshot_id = fingerprint(payload)
        if self.cache is not None:
            try:
                cached = self.cache.get(snapshot_id)
                if cached == payload:
                    payload = cached
                else:
                    self.cache.put(snapshot_id, payload)
            except Exception:
                pass
        return ContextSnapshot(snapshot_id, state.revision, payload)
