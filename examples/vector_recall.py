"""A stale derived index cannot revive a forgotten canonical memory."""

import hashlib
import re

from contextkit import MemoryEngine, Observation, Scope
from contextkit.adapters import InMemoryStore, InMemoryVectorIndex


class DemoEmbedder:
    def embed(self, text: str) -> tuple[float, ...]:
        values = [0.0] * 32
        for word in re.findall(r"\w+", text.lower()):
            bucket = int.from_bytes(hashlib.sha256(word.encode()).digest()[:4], "big") % 32
            values[bucket] += 1.0
        return tuple(values)


def main() -> None:
    engine = MemoryEngine(InMemoryStore())
    index = InMemoryVectorIndex()
    embedder = DemoEmbedder()
    scope = Scope("helpdesk", "customer-42")
    memory = engine.observe(
        scope,
        Observation(
            "message:1",
            "response-preference",
            1,
            "Prefers detailed explanations",
            ("message:1",),
            kind="preference",
        ),
    ).memory
    engine.project(scope, index, embedder)
    found = engine.recall(scope, "detailed explanations", index=index, embedder=embedder)
    assert found == (memory,)
    print("Before forgetting:", [item.content for item in found])
    engine.forget(scope, memory.id, expected_version=1, operation_id="forget:2")
    assert index.search(scope, embedder.embed("detailed explanations"), 5)
    assert engine.recall(scope, "detailed explanations", index=index, embedder=embedder) == ()
    print("Stale index still has a candidate; canonical recall returns no memory.")
    engine.project(scope, index, embedder)
    assert index.search(scope, embedder.embed("detailed explanations"), 5) == []
    print("Projection rebuild removes the stale candidate.")


if __name__ == "__main__":
    main()
