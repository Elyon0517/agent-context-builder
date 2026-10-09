"""Optional cache for content-addressed snapshot payloads."""

from __future__ import annotations

from typing import Any

from contextkit.models import require_revision, require_text


class RedisCache:
    def __init__(self, client: Any, *, namespace: str = "contextkit", ttl: int = 300) -> None:
        require_text(namespace, "namespace")
        require_revision(ttl, "ttl", 1)
        self.client = client
        self.namespace = namespace
        self.ttl = ttl

    def get(self, key: str) -> str | None:
        value = self.client.get(f"{self.namespace}:snapshot:{key}")
        if value is None:
            return None
        return value.decode() if isinstance(value, bytes) else str(value)

    def put(self, key: str, value: str) -> None:
        self.client.set(f"{self.namespace}:snapshot:{key}", value, ex=self.ttl)
